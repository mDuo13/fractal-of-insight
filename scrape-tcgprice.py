#!/usr/bin/env python
# Get TCGPlayer.com pricing information from TCGCSV.com
import json
import os
import requests
from requests.adapters import HTTPAdapter, Retry
from datetime import date
from time import sleep

PRICES_FOLDER = "./data/prices/"
os.makedirs(PRICES_FOLDER, exist_ok=True)
META_FILE = os.path.join(PRICES_FOLDER, "price-meta.json")

# Technically, we could use https://tcgcsv.com/last-updated.txt but instead
# we just save when we last updated and only update once per day.
try:
    with open(META_FILE) as f:
        old_meta = json.load(f)
        last_up = old_meta["updated"]
        if last_up == date.today().isoformat():
            print("Last update was today; no need to update again")
            exit(0)
except Exception as e:
    print("Error checking last update:",e)
    

sess = requests.Session()
API_DELAY = 0.1 #100ms
MAX_RETRIES = 3
TIMEOUT_SECONDS = 10
retries = Retry(total=MAX_RETRIES, backoff_factor=1, status_forcelist=[ 502, 503, 504 ])
sess.mount('https://', HTTPAdapter(max_retries=retries))
sess.headers.update({"User-Agent": "fractal-of-insight-crawler/0.2"})
def get_json_politely(url):
    sleep(API_DELAY)
    r = sess.get(url, timeout=TIMEOUT_SECONDS)
    return r.json()

category = '74' # Grand Archive
all_groups = get_json_politely(f"https://tcgcsv.com/tcgplayer/{category}/groups")["results"]

prefixes = []
for group in all_groups:
    group_id = group['groupId']
    prefix = group['abbreviation']
    prefixes.append(prefix)
    print(f"Getting product listing for {group['name']}")
    j = get_json_politely(f"https://tcgcsv.com/tcgplayer/{category}/{group_id}/products")
    products = {p['productId']: p for p in j['results']}

    print(f"Getting prices for {group['name']}")
    prices = get_json_politely(f"https://tcgcsv.com/tcgplayer/{category}/{group_id}/prices")["results"]

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
