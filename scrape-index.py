#!/usr/bin/env python
import json
import os, os.path

import yaml
import requests

CARDS_FOLDER = "./data/index/"

print("Fetching list of sets...")
r = requests.get("https://api.gatcg.com/option/search")
j = r.json()
all_sets = j["set"]

for cardset in all_sets:
    setlist = []
    prefix = cardset["value"]
    page = 0
    total_pages = 1

    print(f"Fetching {prefix}")
    while page < total_pages:
        page += 1
        print(f"... downloading page {page}")
        r = requests.get(f"https://api.gatcg.com/cards/search?prefix={prefix}&page={page}")
        j = r.json()
        total_pages = j["total_pages"]
        setlist += j["data"]

    os.makedirs(CARDS_FOLDER, exist_ok=True)        
    fname = os.path.join(CARDS_FOLDER, f"{prefix}.json")
    with open(fname, "w") as f:
        json.dump(setlist, f)
