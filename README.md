# TrendPilot_

Judge copy of the local research app. The model key stays in `.env` and is not committed. The original app on port 8787 is unchanged.

Open `http://127.0.0.1:8788` after `uv run trendpilot serve`.


TrendPilot is a local research agent for one company at a time. It searches public web pages, opens them, and returns evidence-backed bets for the company.

The agent uses the xAI login already stored by Pi on this PC (`grok-4.7` plus live web search). It does not email or message anyone.

## Run one company

```bash
uv run trendpilot run examples/company.json
uv run trendpilot run examples/company.json --question "One local bet only."
```

Trace lines go to stderr. Findings JSON goes to stdout. On Windows, pass `--out findings.json` if the console still mangles Cyrillic.

`examples/last-run.json` is one real captured run, not a template.

```bash
uv run trendpilot profiles
uv run trendpilot serve
```

On Windows, double-click `Start TrendPilot.bat` to open the UI. It starts the local server in the background only when needed, so there is no server window to keep open. The server listens only on this PC at `127.0.0.1`.

`serve` runs the local HTTP service at `http://127.0.0.1:8787` and accepts `POST /research`.

- `GET /health`
- `POST /research` with `{"company": {...}, "question": "optional"}`
- Response is newline-delimited JSON events. The last event has `"kind": "done"` and `payload.findings`.

If Pi is not logged in to xAI, set `XAI_API_KEY`. Optional model override: `TRENDPILOT_MODEL`.

## Company and findings contract

The bundled UI runs locally at `http://127.0.0.1:8787`. Other clients can call `trendpilot.run` or `POST /research` directly.

Company fields: `name`, `industry`, `size` (`micro|small|mid|large`), `city`, `offer`, `customer`, `channel`, `constraint`, `competitors`, `language` (`Russian|Kazakh|English`).

Findings:

```json
{
  "headline": "",
  "market_read": "",
  "bets": [
    {
      "title": "",
      "status": "act | watch | not_local | unknown | do_nothing",
      "claim": "",
      "evidence": [{ "url": "", "what_it_shows": "" }],
      "relevance": "",
      "cost": "",
      "benefit": "",
      "test": "",
      "kill_line": ""
    }
  ]
}
```

Event kinds while it works: `status`, `search`, `fetch`, `findings`, `note`, `error`, `done`.

Demo profiles are fictional. They are not clients.
