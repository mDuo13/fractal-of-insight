#!/usr/bin/env python
#Get TCGPlayer.com pricing information from TCGCSV.com
import json
import os
import requests
from datetime import date

PRICES_FOLDER = "./data/prices/"
os.makedirs(PRICES_FOLDER, exist_ok=True)

category = '74' # Grand Archive
r = requests.get(f"https://tcgcsv.com/tcgplayer/{category}/groups")
all_groups = r.json()['results']
if not r.json()["success"]:
    exit("Fetching tcgcsv groups failed")
# fname = os.path.join(PRICES_FOLDER, "groups.json")
# with open(fname, "w") as f:
#     json.dump(all_groups, f)

prefixes = []
for group in all_groups:
    group_id = group['groupId']
    prefix = group['abbreviation']
    prefixes.append(prefix)
    print(f"Getting product listing for {group['name']}")
    r = requests.get(f"https://tcgcsv.com/tcgplayer/{category}/{group_id}/products")
    products = {p['productId']: p for p in r.json()['results']}

    print(f"Getting prices for {group['name']}")
    r = requests.get(f"https://tcgcsv.com/tcgplayer/{category}/{group_id}/prices")
    prices = r.json()['results']

    for price in prices:
        if 'prices' in products[price['productId']].keys():
            products[price['productId']]['prices'].append(price)
        else:
            products[price['productId']]['prices'] = [price]
    for p in products.values():
        if 'prices' not in p.keys():
            # print(f"No price info for {p['name']}")
            # This occurs when a thing is sold out
            p['prices'] = []

    fname = os.path.join(PRICES_FOLDER, f"{prefix}.json")
    with open(fname, "w") as f:
        json.dump(products, f)

meta = {
    "updated": date.today().isoformat(),
    "prefixes": prefixes
}
fname = os.path.join(PRICES_FOLDER, "price-meta.json")
with open(fname, "w") as f:
    json.dump(meta, f)
