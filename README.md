# SemanticBench

**Ask business questions about real company data in plain English, and measure how much a
semantic layer improves AI accuracy.**

![tests](https://github.com/VijayKrishna810680/semanticbench/actions/workflows/ci.yml/badge.svg)

**Live demo: [semanticbench-vijay.streamlit.app](https://semanticbench-vijay.streamlit.app)** (paste a free Groq key in the sidebar to ask questions)

Built on **real data**: ~100,000 orders from [Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce),
a Brazilian online marketplace (Sep 2016 to Oct 2018), with customers, sellers, products, payments,
deliveries and reviews.

## What it does

1. **Ask your data (live app).** Type a question like *"Top 10 categories by revenue in 2018"*. The AI
   reads the semantic layer, writes SQL, checks that it's safe, runs it read-only on the real
   database, and shows the answer, a chart and the SQL.
2. **Compare mode.** See the same question answered **with** and **without** the semantic layer side by side.
3. **Accuracy benchmark.** 25 real business questions with verified correct answers. The AI is scored in three modes:

   | Mode | What the AI sees |
   |---|---|
   | raw | Only table and column names |
   | auto | A semantic model the AI wrote itself from a profile of the data |
   | semantic | A semantic model written by a data engineer ([semantic/olist.yaml](semantic/olist.yaml)) |

4. **Failure analysis.** Explains *why* the AI was wrong. For example, it counted order IDs instead of real
   customers, forgot to exclude cancelled orders, or included freight in revenue.
5. **Query log.** Monitors every live question: success rate, speed, and thumbs up/down feedback.

## Why the semantic layer matters on this data

Real data has traps that an AI can't see from column names alone:

| Trap | Without a semantic layer | Business definition |
|---|---|---|
| `customer_id` is per **order**, not per person | 99,441 "customers" | 96,096 real customers (`customer_unique_id`) |
| Cancelled and unavailable orders | counted as sales | revenue counts **delivered** orders only |
| Payments include freight | revenue too high | revenue = item `price` only |
| Category names are in Portuguese | `beleza_saude` | `health_beauty` via translation table |
| "Late delivery" | many possible definitions | delivered date > estimated date (by day) |

## Production features

- **Read-only safety**, in 3 layers:
  - The SQL parser allows only a single `SELECT` on known tables.
  - The database is opened read-only.
  - Access to external files and URLs is disabled.
- **Query timeout** (20s) and row limit (1,000) on live queries.
- **Self-correction.** If the SQL fails, the AI sees the error and fixes it (one retry).
- **API keys** come from environment variables, `.env` or Streamlit secrets. Keys typed into the app are used for that browser session only and never logged.
- **Rate-limit handling** with automatic retry, for free tiers.
- **Logging and feedback** in SQLite (`logs/query_log.sqlite`).
- **Tests and CI.** 23 pytest tests run on every push with GitHub Actions: safety guard, answer checker and real-data checks.
- **Docker** image and **Streamlit Community Cloud** deployment ready.

## Quick start (free, no money needed)

```bash
git clone https://github.com/VijayKrishna810680/semanticbench.git
cd semanticbench
pip install -r requirements.txt
python setup_data.py          # downloads the real Olist data (~65 MB) and builds data/olist.duckdb
pytest -q                     # 23 tests should pass
```

Get a **free** AI key. Groq is easiest: [console.groq.com](https://console.groq.com), no credit card.
Put it in a `.env` file (copy `.env.example`), or set it in your terminal:

```bash
export GROQ_API_KEY=your_key            # Mac/Linux
set GROQ_API_KEY=your_key               # Windows cmd
$env:GROQ_API_KEY="your_key"            # Windows PowerShell
```

Then:

```bash
streamlit run app.py                                   # the live app
python generate_semantic.py --provider groq            # AI writes semantic/olist_auto.yaml
python run_benchmark.py --provider groq --sleep 2      # benchmark: raw, auto, semantic
python analyze.py                                      # why answers were wrong
```

Other free options: `--provider gemini` (key from [aistudio.google.com](https://aistudio.google.com/apikey), no GCP billing)
and `--provider ollama` (runs offline on your laptop). Paid options: `openai`, `anthropic`.

## Deploy free on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. Click **Create app**, choose this repo, and set the main file to `app.py`.
3. In **Advanced settings → Secrets**, paste `GROQ_API_KEY = "your-key"`.
4. Click Deploy. The first start downloads the data automatically (~30 seconds).

Or with Docker: `docker build -t semanticbench . && docker run -p 8501:8501 -e GROQ_API_KEY=... semanticbench`

## Project structure

| Path | Purpose |
|---|---|
| `app.py`, `views/` | Streamlit app: Ask, Benchmark, Semantic model, Query log |
| `core/agent.py` | Question → SQL → safety check → run → self-fix → plain-English answer |
| `core/guard.py` | SQL safety rules (SELECT-only, known tables, blocked file functions) |
| `core/db.py` | Read-only DuckDB connection with timeout |
| `core/llm.py` | One interface for Groq, Gemini, Ollama, OpenAI and Anthropic |
| `core/semantic.py` | Builds the context for each mode, and the prompts |
| `core/checker.py` | Compares AI results with the correct results |
| `core/logs.py` | Query log and feedback (SQLite) |
| `semantic/olist.yaml` | Curated semantic model |
| `benchmark/questions.json` | 25 questions with verified correct SQL |
| `setup_data.py` | Downloads the real data and builds the database |
| `run_benchmark.py`, `generate_semantic.py`, `analyze.py` | Benchmark tools |
| `tests/` | pytest suite |

## Results

Run `python run_benchmark.py --provider groq` and add your numbers here:

| Model | Raw | Auto semantic | Curated semantic |
|---|---|---|---|
| _your model_ | _%_ | _%_ | _%_ |

## Using your own data

1. Load your tables into a DuckDB file and set `SB_DB_PATH=path/to/your.duckdb`.
2. Write a semantic model for it, or start with `python generate_semantic.py` and review the result.
3. Add your own questions and correct SQL to `benchmark/questions.json` to measure accuracy.

## Data license

The Olist dataset is published by Olist under
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) (non-commercial use).
It is downloaded at setup time and not stored in this repository. The code is MIT licensed.
