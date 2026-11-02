# HUMAN RHYTHMS — v0.2

**Personal Human Rhythm Observatory**  
A longitudinal observation system for biological timing, human functioning, time use and performance.

## What changed in v0.2

- The **Rhythm Map** is now the home screen: nine synchronized domain time series on one shared timeline.
- Temporal windows: today, 9 days, 1 week, 1 month, 3 months, 6 months, 1 year, 2 years, lifetime and custom.
- A timestamped observation form records ratings and raw measurements across all nine domains.
- A life-history section records retrospective life periods and major events, with recall confidence.
- Analytics include domain coverage, indicator summaries and raw indicator trends.
- SQLite remains available for local single-user use.
- Supabase/PostgreSQL connection support and an initial SQL migration with Row Level Security policies are included.
- Excel export remains available.

## Important measurement rules

1. **The app is not a live sensor.** "Current state" means the latest information you recorded. It updates after new observations are entered.
2. **The 0–100 chart is only a display transform** for selected 1–5 self-ratings. It is not a validated health, wellbeing, productivity or performance score.
3. Higher stress, noise burden, social demand and workload are reverse-transformed for visual orientation. Raw values remain stored.
4. Sleep duration, daylight minutes and movement minutes retain their original units. They are not forced onto the same 0–100 scale.
5. Missing data are unknown, not zero. No historical daily values are fabricated.
6. Retrospective life periods and events are explicitly labeled as recalled history, with a confidence rating. They are not equivalent to prospective daily observations.
7. The nine app domains are an operational taxonomy, not validated psychological or physiological constructs.
8. A line that looks wave-like is not, by itself, evidence of a circadian rhythm. Circadian analysis requires appropriate repeated timing measurements.

## Run locally (Windows PowerShell)

Use Python 3.11 or 3.12.

```powershell
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m streamlit run app.py
```

Open `http://localhost:8501`.

## Local database

Without Supabase credentials, the app uses SQLite at:

`data/human_rhythms.sqlite3`

The database is excluded from Git. Use the Excel export as a portable snapshot, not as a second live database.

## Connect Supabase

1. Create a Supabase project: https://supabase.com/
2. Open **SQL Editor**.
3. Run `supabase/migrations/001_initial_schema.sql`.
4. Add your project URL and publishable/anon key to `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_ANON_KEY = "YOUR_PUBLISHABLE_OR_ANON_KEY"
```

5. Restart Streamlit.

Alternatively, set environment variables named `SUPABASE_URL` and `SUPABASE_ANON_KEY`.

**Security limitation in this prototype:** the included Streamlit Supabase adapter is a single-user development bridge, not a completed multi-user authentication implementation. The SQL policies require `auth.uid()` to match the profile UUID. Before using Supabase mode, add Supabase Auth sign-in and derive the profile ID from the authenticated session. Do not use a service-role key in Streamlit client code or commit credentials. Do not deploy private personal data until authentication and row isolation have been tested.

## Data model

- `profiles`: user identity and birth date
- `observations`: timestamped domain-indicator values, unit, source, confidence and notes
- `life_periods`: retrospective life stages / phases
- `life_events`: dated transitions and contextual events
- `activities`: time-use records (schema included; richer entry UI is a future iteration)

The app keeps raw values. Normalized chart values are calculated at display time.

## GitHub

```bash
git init
git add .
git commit -m "Human Rhythms v0.2 — synchronized rhythm map and Supabase schema"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/human-rhythms.git
git push -u origin main
```

## Streamlit Community Cloud

You can deploy a public demo, but do not collect private data until authentication and durable storage are fully implemented and tested. Configure secrets in the Streamlit app settings rather than committing `secrets.toml`.

## Project structure

```text
human-rhythms/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   └── config.toml
├── data/
│   └── .gitkeep
├── docs/
│   ├── DATA_DICTIONARY.md
│   ├── RESEARCH_ALIGNMENT.md
│   └── V0.2_PRODUCT_SPEC.md
└── supabase/
    └── migrations/
        └── 001_initial_schema.sql
```

## Next technical milestone

- Add authenticated Supabase Auth flow and enforce UUID identity end-to-end.
- Add proper event-level / intraday observation entry and wearable imports.
- Add activity/time-use entry and aggregation.
- Add a dedicated retrospective domain assessment with interval-based domain history and uncertainty visualization.
- Add instrument-specific validated questionnaires only after reviewing evidence, language validation and scoring rules.
