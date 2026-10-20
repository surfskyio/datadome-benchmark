import os
import asyncio, csv, sys, time
from datetime import datetime, timezone
from pathlib import Path
from surfsky import AsyncSurfsky, BrowserSettings, Fingerprint, PremiumProxy

MARKERS = ["geo.captcha-delivery.com", "var dd=", "DataDome"]
SEARCH = "https://www.etsy.com/search?q=leather+wallet"
HOME = "https://www.etsy.com"

MODE = sys.argv[1] if len(sys.argv) > 1 else "warm"
RUNS = int(sys.argv[2]) if len(sys.argv) > 2 else 5
CSV_PATH = Path(f"results_surfsky_{MODE}.csv")
SHOTS = Path(f"screenshots/surfsky-{MODE}")

COLS = ["run_id","timestamp_utc","backend","mode","http_status","challenge_markers",
        "listing_count","page_size","total_ms","outcome","failure_type","exit_ip",
        "exit_country","screenshot_path"]

async def one_run(client, n):
    rid = f"surfsky_{MODE}_{datetime.now().strftime('%Y%m%d')}_{n:03d}"
    row = dict.fromkeys(COLS, "")
    row.update(run_id=rid, backend="surfsky", mode=MODE,
               timestamp_utc=datetime.now(timezone.utc).isoformat())
    t0 = time.time()
    try:
        async with client.browser(
            fingerprint=Fingerprint(os="mac"),
            proxy=PremiumProxy(country="us"),
            browser_settings=BrowserSettings(inactive_kill_timeout=60),
        ) as page:
            if MODE == "warm":
                await page.goto(HOME, wait_until="domcontentloaded")
                await asyncio.sleep(5)

            await page.goto(SEARCH, wait_until="domcontentloaded")
            await asyncio.sleep(6)

            html = await page.content()
            found = [m for m in MARKERS if m in html]
            listings = html.count("data-listing-id")
            shot = SHOTS / f"{rid}.png"
            shot.write_bytes(await page.screenshot())

            row.update(http_status=page.status,
                       challenge_markers="|".join(found) if found else "none",
                       listing_count=listings, page_size=len(html),
                       total_ms=int((time.time()-t0)*1000),
                       screenshot_path=str(shot))

            if page.status == 200 and not found and listings > 0:
                row.update(outcome="pass", failure_type="none")
            elif page.status == 403:
                row.update(outcome="fail", failure_type="block_403")
            elif found:
                row.update(outcome="fail", failure_type="challenge_200")
            else:
                row.update(outcome="fail", failure_type="empty_dom")

            try:
                await page.goto("https://ipinfo.io/json", wait_until="domcontentloaded")
                await asyncio.sleep(2)
                raw = await page.content()
                for part in raw.split(","):
                    if '"ip"' in part:
                        row["exit_ip"] = part.split('"')[-2]
                    if '"country"' in part:
                        row["exit_country"] = part.split('"')[-2]
            except Exception:
                pass
    except Exception as e:
        row.update(outcome="fail", failure_type="connection_error",
                   total_ms=int((time.time()-t0)*1000),
                   challenge_markers=type(e).__name__)
    return row

async def main():
    new = not CSV_PATH.exists()
    with CSV_PATH.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        if new: w.writeheader()
        async with AsyncSurfsky(api_token=os.environ["SURFSKY_API_KEY"],
                                base_url="https://api-public.surfsky.io") as client:
            for n in range(1, RUNS+1):
                row = await one_run(client, n)
                w.writerow(row); f.flush()
                print(f"[{n}/{RUNS}] {row['run_id']}: {row['outcome']} "
                      f"status={row['http_status']} listings={row['listing_count']} "
                      f"ip={row['exit_country']}")
                if n < RUNS:
                    await asyncio.sleep(45)

asyncio.run(main())
