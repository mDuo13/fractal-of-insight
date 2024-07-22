import json
import requests
from time import sleep
from os import makedirs

from shared import slugify

API_DELAY = 0.5

class ForceReDL(Exception):
    pass

def get_deck(p_id, evt_id):
    try:
        with open(f"data/event_{evt_id}/deck_{p_id}.json") as f:
            dl = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Downloading #{p_id}'s decklist...")
        dl_raw = requests.get(f"https://omni.gatcg.com/api/events/decklist?id={evt_id}&player={p_id}")
        print("...done.")
        dl = dl_raw.json()
        # cache deck to reduce HTTP requests to omni
        with open(f"data/event_{evt_id}/deck_{p_id}.json", "w") as f:
            json.dump(dl, f)
        sleep(API_DELAY)
    return dl

try:
    with open(f"data/cards.json") as f:
        carddata = json.load(f)
except FileNotFoundError:
    print("Didn't find cached card data")
    carddata = {}

def get_card_img(cardname):
    card_info = carddata.get(cardname)
    if card_info and card_info.get("img"):
        return card_info["img"]

    print("looking up img for",cardname)
    index_lookup = requests.get(f"https://api.gatcg.com/cards/{slugify(cardname)}")
    sleep(API_DELAY)
    try:
        index_json = index_lookup.json()
    except json.JSONDecodeError:
        print("Invalid/unexpected Index response:", index_lookup)
        exit()
    ed_slug = index_json["result_editions"][0]["slug"]
    card_img = f"https://ga-index-public.s3.us-west-2.amazonaws.com/cards/{ed_slug}.jpg"
    print("Saving card data to cache...")
    makedirs("data/", exist_ok=True)
    carddata[cardname] = {
        "img": card_img
    }
    with open(f"data/cards.json", "w") as f:
        json.dump(carddata, f)
    return card_img

def get_event(evt_id, force_redownload=False):
    makedirs(f"data/event_{evt_id}/", exist_ok=True)
    try:
        if force_redownload:
            raise ForceReDL
        with open(f"data/event_{evt_id}/event.json") as f:
            evt = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, ForceReDL):
        print("Downloading event JSON...")
        evt_raw = requests.get(f"https://omni.gatcg.com/api/events/event?id={evt_id}")
        print("...done.")
        evt = evt_raw.json()
        with open(f"data/event_{evt_id}/event.json", "w") as f:
            json.dump(evt, f)
        sleep(API_DELAY)
    return evt
