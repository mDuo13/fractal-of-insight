#!/usr/bin/env python
import json
import os.path

import yaml
import requests

CARDS_FOLDER = "./data/index/"

r = requests.get("https://api.gatcg.com/option/search")
j = r.json()
all_sets = j["set"]

all_cards = {}

for cardset in all_sets:
    setlist = []
    prefix = cardset["value"]
    all_cards[prefix] = []
    page = 0
    total_pages = 1

    while page < total_pages:
        page += 1 
        r = requests.get(f"https://api.gatcg.com/cards/search?prefix={prefix}&page={page}")
        j = r.json()
        total_pages = j["total_pages"]
        setlist += j["data"]
        
    fname = os.path.join(CARDS_FOLDER, f"{prefix}.json")
    with open(fname, "w") as f:
        json.dump(setlist, f)
