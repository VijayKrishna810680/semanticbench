"""
One function to call different AI providers.

FREE options (no money needed):
  groq    - free API key at console.groq.com (no credit card).    GROQ_API_KEY
  gemini  - free API key at aistudio.google.com (no GCP billing). GEMINI_API_KEY
  ollama  - runs on your own laptop, fully offline.               (no key)
Paid options: openai (OPENAI_API_KEY), anthropic (ANTHROPIC_API_KEY)
"""
import os
import re
import time

# provider -> (base_url, api-key env var, default model)
OPENAI_COMPATIBLE = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "openai/gpt-oss-120b"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY", "gemini-flash-latest"),
    "ollama": (os.getenv("OLLAMA_URL", "http://localhost:11434/v1"), None, "qwen2.5-coder:7b"),
    "openai": (None, "OPENAI_API_KEY", "gpt-4o-mini"),
}
PROVIDERS = list(OPENAI_COMPATIBLE) + ["anthropic"]
DEFAULT_MODELS = {p: v[2] for p, v in OPENAI_COMPATIBLE.items()} | {"anthropic": "claude-haiku-4-5"}
KEY_ENV = {p: v[1] for p, v in OPENAI_COMPATIBLE.items()} | {"anthropic": "ANTHROPIC_API_KEY"}


class MissingKeyError(RuntimeError):
    pass


def has_key(provider: str, api_key: str = "") -> bool:
    env = KEY_ENV.get(provider)
    return env is None or bool(api_key) or bool(os.getenv(env))


def _call(provider, model, messages, max_tokens, api_key=""):
    if provider == "anthropic":
        import anthropic
        msg = anthropic.Anthropic(api_key=api_key or None).messages.create(
            model=model, max_tokens=max_tokens, temperature=0, messages=messages)
        return msg.content[0].text

    if provider in OPENAI_COMPATIBLE:
        from openai import OpenAI
        base_url, key_env, _ = OPENAI_COMPATIBLE[provider]
        api_key = "ollama" if key_env is None else (api_key or os.getenv(key_env))
        if not api_key:
            raise MissingKeyError(f"Set {key_env} first (free key - see README).")
        client = OpenAI(base_url=base_url, api_key=api_key, max_retries=0, timeout=90)
        extra = {}
        if "gpt-oss" in model or model.startswith("gemini"):
            extra["reasoning_effort"] = "low"  # "thinking" models: think briefly, answer fast
        resp = client.chat.completions.create(
            model=model, temperature=0, max_tokens=max_tokens, messages=messages, **extra)
        return resp.choices[0].message.content or ""

    raise ValueError(f"Unknown provider: {provider}")


def ask_llm(provider, model, prompt=None, messages=None, max_tokens=2000, retries=5, api_key=""):
    """Send a prompt (or a chat history) to the AI. Waits and retries on free-tier rate limits."""
    model = model or DEFAULT_MODELS[provider]
    messages = messages or [{"role": "user", "content": prompt}]
    for attempt in range(retries + 1):
        try:
            return _call(provider, model, messages, max_tokens, api_key)
        except MissingKeyError:
            raise
        except Exception as e:
            text = str(e).lower()
            limited = "429" in text or "rate" in text or "quota" in text or "overloaded" in text
            if not limited or attempt == retries:
                raise
            wait = min(10 * (attempt + 1), 60)
            print(f"    (rate limit, waiting {wait}s...)", flush=True)
            time.sleep(wait)


def extract_block(text: str, lang: str = "sql") -> str:
    """Pull the content out of a ```lang ... ``` block (or return the text as-is)."""
    m = re.search(rf"```(?:{lang})?\s*(.*?)```", text, re.S | re.I)
    return (m.group(1) if m else text).strip()
