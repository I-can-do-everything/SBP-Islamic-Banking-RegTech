# Assets

Images used by the social media drafts. Every image is rendered from source in `src/` (HTML and CSS) with Playwright at 2x scale, so it can be regenerated and edited.

To re-render (from this folder):

```bash
NODE_PATH=$(npm root -g) node src/render.js architecture-overview audit-by-numbers
```

| File | Used by | Shows | Sensitive information check |
|---|---|---|---|
| `architecture-overview.png` | LI-01, LI-04, Blog-01 | System architecture: web app, API, PostgreSQL, workers with DuckDB, object storage, rulebook, AI gateway | Diagram only. No data, hostnames, keys or real bank names. Carries the "Portfolio project. Synthetic data. Not an SBP certified system." footer |
| `audit-by-numbers.png` | LI-02, Blog-01 | Bug counts by severity from the prototype audit, and the sign convention example (11.5% vs -11.5%) | Counts and an illustrative calculation only. No data from any bank |

Screenshots of the running app will be added from milestone M7 onward, captured from the demo bank (EXIB, synthetic data) by the Playwright end to end tests.
