# Assay — Metals & Macro Intelligence Desk

A live-simulated metals and macro intelligence terminal: spot prices, central bank gold
reserves, a global intel map of mines and shipping chokepoints, and a rolling news feed.

All data (prices, reserves, feed headlines, risk scores) is **fabricated for
demonstration** — there are no live market or news feeds wired in.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Structure

- `dashboard.html` — the actual dashboard: self-contained HTML/CSS/JS (canvas world map,
  live-jittering ticker, expandable reserves ledger, auto-appending intel feed).
- `app.py` — a thin Streamlit wrapper that embeds `dashboard.html` via
  `streamlit.components.v1.html`, so it can be deployed on Streamlit Community Cloud.

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub (public, for the free tier).
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub.
3. Click **New app**, pick this repo/branch, set the main file to `app.py`, and deploy.
