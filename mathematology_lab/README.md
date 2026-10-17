# Mathematology Lab v0.1 — Data Foundation

An intentionally small, single-user starting point for the Mathematology Lab research system. The existing agentic platform on `main` is untouched.

## Start locally or in a Replit Python environment

From the repository root:

```bash
pip install -r mathematology_lab/requirements.txt
streamlit run mathematology_lab/app.py --server.address 0.0.0.0
```

Open the Streamlit web preview. No Redis, PostgreSQL, Docker, or OpenAI API key is needed for this milestone.

## Input

CSV columns: `draw_date,winning_numbers,bonus`. Dates must use ISO `YYYY-MM-DD`; six numbers are space-separated. Bonus is optional, and if supplied must be in 1–59 and distinct from the six main numbers.

The loader retains original number order for flattened Markov and mutation research, stores draws chronologically, validates uniqueness, and creates a content-addressed immutable snapshot. The app does not fetch external data or alter the three original Replit applications.

## Tests

```bash
python -m unittest discover -s mathematology_lab/tests -v
```

## Next milestones

1. Historical source adapters and import/export compatibility.
2. Versioned engine adapters and full per-number model score records.
3. Leakage-free walk-forward backtesting.
4. Optional OpenAI API reasoning assistant and experiment dashboard.

**Security:** This prototype has no built-in authentication. Do not publish it as an openly accessible public deployment with private data. Use a private development environment or put access control in front of it. Keep API keys in platform secrets.
