# DataDome benchmark: Playwright vs Browserbase vs Surfsky

Raw data and code behind the article "How to Bypass DataDome with Playwright: Local vs Browserbase vs Surfsky".

Target: `https://www.etsy.com/search?q=leather+wallet`

## What was tested

Each backend ran two arms of 20:

- **cold** — navigate straight to the search URL
- **warm** — load the Etsy homepage, wait 5 seconds, then navigate to the same search URL

Everything else is identical between the arms. The homepage visit is the only
difference. A run passes only if it returns HTTP 200, the response HTML
contains no DataDome challenge markers, and listing content is present.

## Results

| File | Backend | Config | Date |
|---|---|---|---|
| `results/local_cold.csv` | Local Chromium | US residential proxy | Sep 30 (11 runs), Oct 19 (9 runs) |
| `results/local_warm.csv` | Local Chromium | US residential proxy | Sep 30 |
| `results/browserbase_free_cold.csv` | Browserbase | Free plan, no proxies | Sep 29 |
| `results/browserbase_free_warm.csv` | Browserbase | Free plan, no proxies | Sep 29 |
| `results/browserbase_dev_cold.csv` | Browserbase | Developer plan, US residential | Oct 19 |
| `results/browserbase_dev_warm.csv` | Browserbase | Developer plan, US residential | Oct 19 |
| `results/surfsky_cold.csv` | Surfsky | Trial, US residential | Sep 29-30 |
| `results/surfsky_warm.csv` | Surfsky | Trial, US residential | Sep 29-30 |
| `results/browserbase_captcha_control.csv` | Browserbase | solveCaptchas false control | Sep 29 |

The Browserbase Developer runs are three weeks after the other backends.
DataDome retrains per site, so pass rates from different dates are not
strictly comparable. Exact dates are in the timestamp_utc column of every file.

## Running it

    python -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    playwright install chromium
    cp .env.example .env

Then, per backend and arm:

    python scripts/run_local.py cold 20
    python scripts/run_local.py warm 20
    python scripts/run_browserbase_dev.py cold 20
    python scripts/run_browserbase_dev.py warm 20
    python scripts/run_surfsky.py cold 20
    python scripts/run_surfsky.py warm 20

Runs are spaced 45 seconds apart. Firing them back to back is its own
detection signal.

## Environment

- Python 3.12 (the Surfsky SDK requires 3.12 or newer)
- Playwright with bundled Chromium
- macOS, run from a residential connection

## Expect drift

DataDome updates its models. These numbers describe Etsy on the dates above
and nothing more. If you re-run this and get different results, that is the
expected outcome, not a bug.
