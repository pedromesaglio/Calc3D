# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Calc3D** — Web calculator for 3D printing production costs. Built with FastAPI + Jinja2 + Chart.js.

## Setup & Run

```bash
# Activate the existing virtualenv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run dev server
uvicorn main:app --reload
```

App is served at `http://localhost:8000`.

## Architecture

- `main.py` — FastAPI app. All routes and business logic live here. History is stored in-process (a module-level list); no database.
- `templates/index.html` — Single Jinja2 template. Renders form, results, chart, and history table. Chart.js and Tailwind CSS are loaded from CDN.

### Cost calculation flow

```
POST /calculate
  → parse form inputs
  → filament_cost  = (weight_g / 1000) * price_per_kg
  → electricity_cost = (watts / 1000) * hours * rate_per_kwh
  → base_cost_per_unit = filament + electricity + other_costs
  → selling_price_per_unit = base_cost_per_unit * multiplier
  → append result dict to history[]
  → render index.html with last_result + chart_data (JSON)
```

Chart data (`build_chart_data`) generates cost series for multipliers ×1–×5 across quantities 1–20, serialized as JSON and passed directly to the template for Chart.js consumption.

### Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Render calculator (empty state) |
| POST | `/calculate` | Compute costs, add to history, re-render |
| POST | `/clear-history` | Empty the history list, redirect to `/` |
