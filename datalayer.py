import json
import re
import requests
from time import sleep
from os import makedirs, scandir

from shared import slugify, fix_case
from cards import ERRATA

API_DELAY = 0.5
COMMENT_REGEX = re.compile(r"# (?P<comment>.*)$")
CARD_REGEX = re.compile(r"(?P<quantity>[0-9]+) (?P<card>.*)$")
CARDS_FOLDER = "./data/index/"

class ForceReDL(Exception):
    pass

class EventNotFound(Exception):
    pass

class NoDeck(Exception):
    pass

def get_deck(p_id, evt_id, public_on_omni):
    try:
        with open(f"data/event_{evt_id}/deck_{p_id}.json") as f:
            dl = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        try:
            dl = sideload_deck(p_id, evt_id)
        except (FileNotFoundError):
            if not public_on_omni:
                raise NoDeck()
            print(f"Downloading #{p_id}'s decklist...")
            dl_raw = requests.get(f"https://omni.gatcg.com/api/events/decklist?id={evt_id}&player={p_id}")
            print("...done.")
            dl = dl_raw.json()
            if dl_raw.status_code != 200 or dl.get("error"):
                raise NoDeck(f"Status code {dl_raw.status_code} fetching evt {evt_id} deck for player #{p_id}")
            # cache deck to reduce HTTP requests to omni
            with open(f"data/event_{evt_id}/deck_{p_id}.json", "w") as f:
                json.dump(dl, f)
            sleep(API_DELAY)
    return dl

def sideload_deck(p_id, evt_id):
    with open(f"data/event_{evt_id}/sideload/deck_{p_id}.txt") as f:
        dl_txt = f.read()
    
    deck = {"material": [], "main": [], "sideboard": []}
    active_deck = None
    for line in dl_txt.split("\n"):
        cm = COMMENT_REGEX.match(line)
        if cm:
            comment = cm.group("comment").lower().strip()
            if comment in ("material deck", "material", "mats"):
                active_deck = deck["material"]
            elif comment in ("main deck", "maindeck", "main"):
                active_deck = deck["main"]
            elif comment in ("sideboard", "side"):
                active_deck = deck["sideboard"]
            else:
                print("Warning: comment other than mat/main/side indicator")
        elif line.strip():
            m = CARD_REGEX.match(line)
            if not m:
                raise ValueError("Unknown line in decklist:", line)
            if active_deck is None:
                raise ValueError("Card in unknown section of deck", line)
            active_deck.append({
                "quantity": int(m.group("quantity")),
                "card": m.group("card"),
                "rawInput": line
            })
    #print("Sideloaded deck:", json.dumps(deck, indent=2))
    return deck
            

try:
    carddata = {}
    for entry in scandir(CARDS_FOLDER):
        if entry.is_file() and entry.name[-5:] == ".json":
            with open(entry) as f:
                setlist = json.load(f)
            for card in setlist:
                cardname = fix_case(card["name"])
                if cardname not in carddata.keys():
                    carddata[cardname] = card
                else:
                    carddata[cardname]["result_editions"] += card["result_editions"]
                    
    # with open(f"data/cards.json") as f:
    #     carddata = json.load(f)
except FileNotFoundError:
    print("Didn't find cached card data")
    carddata = {}

for cardname, card in carddata.items():
    # possibly change card image for a lower rarity one?
    lowest_rarity = 99
    for ced in carddata[cardname]["result_editions"]:
        if ced["set"]["name"][:14] == "Supporter Pack":
            # Skip supporter pack editions since they're always reprints
            continue
        if ced["rarity"] < lowest_rarity:
            lowest_rarity = ced["rarity"]
            lowest_ced = ced
    if lowest_rarity == 99:
        exit(f"Error finding lowest rarity for {cardname}.")
    ed_slug = lowest_ced["slug"]
    card["img"] = f"https://ga-index-public.s3.us-west-2.amazonaws.com/cards/{ed_slug}.jpg"

def get_card_img(cardname, at=0):
    # Special case for errata'd Proxia's Vault cards like Stonescale Band
    if cardname in ERRATA.keys():
        errata = ERRATA[cardname]
        if errata.get("before") > at:
            return errata["img"]

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
    # print("Saving card data to cache...")
    # makedirs("data/", exist_ok=True)
    # carddata[cardname] = {
    #     "img": card_img
    # }
    # with open(f"data/cards.json", "w") as f:
    #     json.dump(carddata, f)
    return card_img

FM_EFFECT = '<span class=\"effect__label\">Floating Memory</span>'
CB_FM = '<span class=\"effect__bubble\">Class Bonus</span><span class=\"effect__label\">Floating Memory'
def card_is_floating(card, champs=[]):
    """
    Given a card data object and a list of champion card names, return True if the card
    (a) is unconditional floating memory, or
    (b) is floating memory for any class any of the champs have
    """
    card_effect = card["effect"] or ""
    if FM_EFFECT in card_effect:
        if CB_FM in card_effect:
            for champ in champs:
                champcard = carddata[champ]
                for champclass in champcard["classes"]:
                    if champclass in card["classes"]:
                        return True
            return False
        else:
            return True
    return False

def get_event(evt_id, force_redownload=False, save=True):
    try:
        if force_redownload:
            raise ForceReDL
        with open(f"data/event_{evt_id}/event.json") as f:
            evt = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, ForceReDL):
        print(f"Downloading event #{evt_id} JSON...")
        evt_raw = requests.get(f"https://omni.gatcg.com/api/events/event?id={evt_id}")
        #print("...done.")
        if evt_raw.status_code == 404:
            raise EventNotFound
        evt = evt_raw.json()
        if save:
            save_event_json(evt)
        sleep(API_DELAY)
    return evt

def save_event_json(evt):
    makedirs(f"data/event_{evt['id']}/", exist_ok=True)
    with open(f"data/event_{evt['id']}/event.json", "w") as f:
        json.dump(evt, f)
