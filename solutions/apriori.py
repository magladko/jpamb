#!/usr/bin/env python3
"""Another cheating solution.

This solution uses apriori knowledge about the distribution of the test-cases
to gain an advantage.
"""

import sys
import csv
import jpamb

if sys.argv[1] == "info":
    jpamb.printinfo(
        "apriori",
        "1.0",
        "The Rice Theorem Cookers",
        ["cheat", "python", "stats"],
        for_science=True,
    )


with open("stats/distribution.csv") as f:
    distribution = list(csv.DictReader(f))[-1]

print(f"Got {sys.argv[1:]}", file=sys.stderr)

for k, v in distribution.items():
    if k == "method":
        continue
    print(f"{k};{v}")
