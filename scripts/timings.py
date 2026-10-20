import os
import csv, glob, statistics
from collections import defaultdict

buckets = defaultdict(list)

for path in sorted(glob.glob("results_*.csv")):
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("failure_type") == "connection_error":
                continue
            ms = row.get("total_ms", "").strip()
            if not ms:
                continue
            buckets[(row["backend"], row["mode"])].append(int(ms))

order = {"local_chromium": 0, "browserbase": 1, "surfsky": 2}
rows = sorted(buckets.items(), key=lambda kv: (order.get(kv[0][0], 9), kv[0][1]))

print(f"{'Backend':<18}{'Arm':<8}{'Mean':>10}{'Median':>10}{'Fastest':>10}{'Slowest':>10}")
print("-" * 66)
for (backend, mode), vals in rows:
    print(f"{backend:<18}{mode:<8}"
          f"{statistics.mean(vals):>9.0f}m"
          f"{statistics.median(vals):>9.0f}m"
          f"{min(vals):>9d}m"
          f"{max(vals):>9d}m")
