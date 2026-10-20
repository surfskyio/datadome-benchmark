import os
import asyncio, csv, json, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright

API_KEY = os.environ["BROWSERBASE_API_KEY"]
PROJECT_ID = os.environ["BROWSERBASE_PROJECT_ID"]

SESSION_EXTRA = {
    "proxies": [{"type": "browserbase", "geolocation": {"country": "US"}}],
}

MARKERS = ["geo.captcha-delivery.com", "var dd=", "DataDome"]
SEARCH = "https://www.etsy.com/search?q=leather+wallet"
HOME = "https://www.etsy.com"

MODE = sys.argv[1] if len(sys.argv) > 1 else "warm"
RUNS = int(sys.argv[2]) if len(sys.argv) > 2 else 5
CSV_PATH = Path(f"results_browserbase_dev_{MODE}.csv")
SHOTS = Path("screenshots/browserbase-dev")
SHOTS.mkdir(parents=True, exist_ok=True)

COLS = ["run_id","timestamp_utc","backend","plan","mode","http_status",
        "challenge_markers","listing_count","page_size","total_ms","outcome",
        "failure_type","exit_ip","exit_country","exit_org","session_id",
        "screenshot_path"]

def create_session(retries=4):
    body = dict({"projectId": PROJECT_ID}, **SESSION_EXTRA)
    last = None
    for i in range(retries):
        req = urllib.request.Request(
            "https://api.browserbase.com/v1/sessions",
            data=json.dumps(body).encode(),
            headers={"X-BB-API-Key": API_KEY, "Content-Type": "application/json"},
            method="POST")
        try:
            return json.loads(urllib.request.urlopen(req, timeout=60).read())
        except urllib.error.HTTPError:
            raise
        except urllib.error.URLError as e:
            last = e
            print("    DNS/connection blip, retrying in", 3 * (i + 1), "s")
            time.sleep(3 * (i + 1))
    raise last

async def one_run(pw, n):
    rid = f"bbdev_{MODE}_{datetime.now().strftime('%Y%m%d')}_{n:03d}"
    row = dict.fromkeys(COLS, "")
    row.update(run_id=rid, backend="browserbase", plan="developer", mode=MODE,
               timestamp_utc=datetime.now(timezone.utc).isoformat())
    t0 = time.time()
    browser = None
    try:
        sess = create_session()
        row["session_id"] = sess.get("id", "")
        browser = await pw.chromium.connect_over_cdp(sess["connectUrl"], timeout=90000)
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        page.set_default_timeout(60000)

        if MODE == "warm":
            await page.goto(HOME, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)

        resp = await page.goto(SEARCH, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(6)

        html = await page.content()
        found = [m for m in MARKERS if m in html]
        listings = html.count("data-listing-id")
        status = resp.status if resp else 0
        shot = SHOTS / f"{rid}.png"
        await page.screenshot(path=str(shot))

        row.update(http_status=status,
                   challenge_markers="|".join(found) if found else "none",
                   listing_count=listings, page_size=len(html),
                   total_ms=int((time.time()-t0)*1000),
                   screenshot_path=str(shot))

        if status == 200 and not found and listings > 0:
            row.update(outcome="pass", failure_type="none")
        elif status == 403:
            row.update(outcome="fail", failure_type="block_403")
        elif found:
            row.update(outcome="fail", failure_type="challenge_200")
        else:
            row.update(outcome="fail", failure_type="empty_dom")

        try:
            await page.goto("https://ipinfo.io/json",
                            wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            info = json.loads(await page.inner_text("body"))
            row["exit_ip"] = info.get("ip", "")
            row["exit_country"] = info.get("country", "")
            row["exit_org"] = info.get("org", "")
        except Exception:
            pass
    except Exception as e:
        row.update(outcome="fail", failure_type="connection_error",
                   total_ms=int((time.time()-t0)*1000),
                   challenge_markers=type(e).__name__)
    finally:
        if browser:
            try: await browser.close()
            except Exception: pass
    return row

async def main():
    print("session config:", json.dumps(SESSION_EXTRA))
    new = not CSV_PATH.exists()
    with CSV_PATH.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        if new: w.writeheader()
        async with async_playwright() as pw:
            for n in range(1, RUNS+1):
                row = await one_run(pw, n)
                w.writerow(row); f.flush()
                print(f"[{n}/{RUNS}] {row['run_id']}: {row['outcome']} "
                      f"status={row['http_status']} listings={row['listing_count']} "
                      f"{row['exit_country']} {row['exit_org'][:28]}")
                if n < RUNS:
                    await asyncio.sleep(45)

asyncio.run(main())
