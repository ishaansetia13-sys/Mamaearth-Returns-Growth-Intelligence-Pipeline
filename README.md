# Mamaearth Returns & Growth Intelligence Pipeline

This project uses the supplied customer, product and order CSVs to study revenue and product returns. It has three independent stages: SQL reporting on the original data, pandas cleaning and analysis, and an SCR business narrative. All money values are in INR.

## 1. SQL: schema, data and reports

Use Python 3 and SQLite. From the project folder, run:

```bash
python -c "import sqlite3; from pathlib import Path; db=sqlite3.connect('mamaearth.db'); [db.executescript(Path(f).read_text()) for f in ['sql/schema.sql','sql/seed_data.sql']]; db.close()"

```

For labeled SQL results, install the SQLite CLI and run `sqlite3 -header -column mamaearth.db < sql/reports.sql`. Run the schema and seed steps only on a fresh database (delete `mamaearth.db` before starting again). `reports.sql` adds the loyalty column, so run the report file once per fresh database. Original expected counts: 45 customers, 16 products and 180 orders. The SQL revenue includes the five deliberately duplicated orders.

## 2. Pandas analysis and charts

Install dependencies: `python -m pip install -r requirements.txt`.

From the project folder run, in this order:

```bash
python analysis/clean_and_eda.py
python analysis/visualize.py
```

The first script independently reads the original CSVs, standardises payment methods, removes the five duplicated transactions, fills missing values and prints the requested EDA checks. It exports `narrator/findings.json` from its calculated results. The second script reuses the same cleaning function and saves both charts in `visualizations/`. Neither script edits the original CSVs.

## 3. Insight narrator

Offline mode requires no key or internet access:

```bash
python narrator/generate_narrative.py
```

For the optional Gemini version, obtain a free-tier API key from Google AI Studio. Set it in your terminal before running the same command:

```bash
# macOS / Linux
export GEMINI_API_KEY="your_key_here"
# Windows PowerShell
$env:GEMINI_API_KEY="your_key_here"
```

The script uses `google-genai`, a separate system instruction, temperature 0 and a 30-second request timeout. If the API fails, or the response misses a required figure, it uses a deterministic offline SCR narrative instead. The five-number checker prints PASS/FAIL for each figure and saves the verified output to `narrator/sample_output.txt`. Never commit your actual API key.

## Notes on interpretation

The SQL stage reports original transactions; the pandas stage removes five duplicate submissions, reducing revenue by INR 2,501.90. The two unusually large January orders remain in the cleaned dataset but are excluded from the outlier-corrected monthly comparison. COD has the highest observed return rate, especially in Tier-2 cities; this association does not establish causation.
