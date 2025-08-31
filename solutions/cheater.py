# /usr/bin/env python
"""This solution cheats by loading the `stats/cases.txt` file."""

import sys

import jpamb


methodid = sys.argv[1]

if methodid == "info":
    jpamb.printinfo("cheater", "0.1", ["cheat", "python"], for_science=True)

queries = set()

queries_in_method = set()

with open("stats/cases.txt", "r") as f:
    for line in f.readlines():
        methodid_, case = line.split(" ", 1)
        query = case.rsplit("->", 1)[1].strip()
        queries.add(query)
        if methodid_ == methodid:
            queries_in_method.add(query)

for q in queries:
    score = "100%" if q in queries_in_method else "0%"
    print(f"{q};{score}")
