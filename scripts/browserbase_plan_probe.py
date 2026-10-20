import os
import json, urllib.request

API_KEY = os.environ["BROWSERBASE_API_KEY"]
PROJECT_ID = os.environ["BROWSERBASE_PROJECT_ID"]

CANDIDATES = [
    ("proxies US + advancedStealth", {
        "proxies": [{"type": "browserbase", "geolocation": {"country": "US"}}],
        "browserSettings": {"advancedStealth": True}}),
    ("proxies US only", {
        "proxies": [{"type": "browserbase", "geolocation": {"country": "US"}}]}),
    ("proxies true + advancedStealth", {
        "proxies": True, "browserSettings": {"advancedStealth": True}}),
    ("proxies true only", {"proxies": True}),
    ("no proxies, advancedStealth", {
        "browserSettings": {"advancedStealth": True}}),
]

for label, extra in CANDIDATES:
    body = dict({"projectId": PROJECT_ID}, **extra)
    req = urllib.request.Request(
        "https://api.browserbase.com/v1/sessions",
        data=json.dumps(body).encode(),
        headers={"X-BB-API-Key": API_KEY, "Content-Type": "application/json"},
        method="POST")
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=60).read())
        print(f"OK      {label}")
        print(f"        session {r.get('id')}")
    except urllib.error.HTTPError as e:
        print(f"REJECT  {label}")
        print(f"        {e.code} {e.read().decode()[:160]}")
    print()
