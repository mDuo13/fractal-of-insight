import json
import re
import requests
from logging import warning
from requests.adapters import HTTPAdapter, Retry
from time import sleep, time
from os import makedirs, scandir, path

from .shared import slugify, fix_case, lineage
from .cards import ERRATA, REMOVED_FROM_PRXY
from .carddb import CardDB
from .decksim import DeckSim
from .prices import PriceDB

API_DELAY = 0.5
COMMENT_REGEX = re.compile(r"# (?P<comment>.*)$")
CARD_REGEX = re.compile(r"(?P<quantity>[0-9]+) (?P<card>.*)$")
CARDS_FOLDER = "./data/index/"
PRICES_FOLDER = "./data/prices/"
DECK_SIMILARITY_FILE = "./data/decksim.json"

class ForceReDL(Exception):
    pass

class EventNotFound(Exception):
    pass

class NoDeck(Exception):
    pass

MAX_RETRIES = 3
TIMEOUT_SECONDS = 10
def fetch(url):
    """
    Get with timeouts, automatic backoff, etc.
    """
    s = requests.Session()
    retries = Retry(total=MAX_RETRIES, backoff_factor=1, status_forcelist=[ 502, 503, 504 ])
    s.mount('https://', HTTPAdapter(max_retries=retries))
    return s.get(url, timeout=TIMEOUT_SECONDS)


def get_deck(p_id, evt_id, public_on_omni):
    try:
        dl = sideload_deck(p_id, evt_id)
    except (FileNotFoundError):
        try:
            with open(f"data/event_{evt_id}/deck_{p_id}.json") as f:
                dl = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            if not public_on_omni or int(evt_id) == 384: #Special case for Ascent Ontario which was before Omni supported decklists
                raise NoDeck()
            print(f"Downloading #{p_id}'s decklist...")
            dl_raw = fetch(f"https://omni.gatcg.com/api/events/decklist?id={evt_id}&player={p_id}")
            print("...done.")
            dl = dl_raw.json()
            if dl_raw.status_code != 200 or dl.get("error"):
                raise NoDeck(f"Status code {dl_raw.status_code} fetching evt {evt_id} deck for player #{p_id}")
            # cache deck to reduce HTTP requests to omni
            with open(f"data/event_{evt_id}/deck_{p_id}.json", "w") as f:
                json.dump(dl, f)
            sleep(API_DELAY)
    return dl

def get_topcut_deck(p_id, evt_id):
    # Maybe someday there will be an API way to get top cut decks.
    try:
        dl = sideload_deck(p_id, evt_id, fname=f"data/event_{evt_id}/sideload/deck_{p_id}_topcut.txt")
        return dl
    except (FileNotFoundError):
        raise NoDeck()

def sideload_deck(p_id, evt_id, fname=None):
    if not fname:
        fname = f"data/event_{evt_id}/sideload/deck_{p_id}.txt"
    with open(fname) as f:
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
                warning("Decklist comment other than mat/main/side indicator")
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

carddata = CardDB()

def get_card_img(cardname, at=0, from_set_group=None):
    """
    Get an appropriate image URL for the card, looking it up on Index if necessary.

    Params:
    at - the time of the event where the card appears, in case of cards that
         have different versions because of errata
    from_set_group - if provided, should be the name of an Index-defined set
                     group, such as 'Mercurial Heart' (which includes ReCo
                     decks & MRC Alter). Will return the image URL for the
                     corresponding edition if possible.
    """
    # Special case for errata'd Proxia's Vault cards like Stonescale Band
    if at == 0:
        at = time()*1000
    if cardname in ERRATA.keys():
        errata = ERRATA[cardname]
        if errata.get("before") > at:
            return errata["img"]

    card_info = carddata.get(cardname)
    if card_info and from_set_group and from_set_group != "Other":
        set_group = carddata.get_set_groups()[from_set_group]
        set_prefixes = [s["prefix"] for s in set_group["sets"]]
        for ed in card_info["editions"]:
            if ed["set"]["prefix"] in set_prefixes:
                return f"https://api.gatcg.com{ed['image']}"
    elif card_info and card_info.get("img"):
        return card_info["img"]

    print("looking up img for",cardname)
    index_lookup = fetch(f"https://api.gatcg.com/cards/{slugify(cardname)}")
    sleep(API_DELAY)
    try:
        index_json = index_lookup.json()
    except json.JSONDecodeError:
        print("Invalid/unexpected Index response:", index_lookup)
        exit()
    ed_img = index_json["result_editions"][0]["image"]
    card_img = f"https://api.gatcg.com{ed_img}"
    return card_img

FM_EFFECT = '**Floating Memory**'
CB_FM = '[Class Bonus] **Floating Memory**'
OTHER_FM = ' Bonus] **Floating Memory**'
def card_is_floating(card, champs=[]):
    """
    Given a card data object and a list of champion card names, return True if the card
    (a) is unconditional floating memory, or
    (b) is floating memory for any class any of the champs have
    """
    card_effect = card.get("effect", "") or ""
    if FM_EFFECT in card_effect:
        if CB_FM in card_effect:
            for champ in champs:
                champcard = carddata[champ]
                for champclass in champcard["classes"]:
                    if champclass in card["classes"]:
                        return True
            return False
        elif OTHER_FM in card_effect:
            for champ in champs:
                champname = lineage(champ)
                champbonus_text = f'[{champname} Bonus] **Floating Memory**'
                if champbonus_text in card_effect:
                    return True
            return False
        else:
            return True
    return False

def get_event(evt_id, force_redownload=False, save=True, dl_decklists=False):
    try:
        if force_redownload:
            raise ForceReDL
        with open(f"data/event_{evt_id}/event.json") as f:
            evt = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, ForceReDL):
        print(f"Downloading event #{evt_id} JSON...")
        evt_raw = fetch(f"https://omni.gatcg.com/api/events/event?id={evt_id}")
        #print("...done.")
        if evt_raw.status_code == 404:
            raise EventNotFound
        evt = evt_raw.json()
        if save:
            save_event_json(evt)
        sleep(API_DELAY)
    if dl_decklists:
        for pdata in evt["players"]:
            is_public = pdata.get("isDecklistPublic")
            try:
                get_deck(pdata["id"], evt["id"], is_public)
            except NoDeck:
                pass
    return evt

def get_event_videos(evt_id):
    try:
        with open(f"vods/{evt_id}.json") as f:
            vids = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        vids = {"videos": []}
    return vids.get("videos", [])

def get_event_refracted_achievements(evt_id):
    try:
        with open(f"data/refracted/{evt_id}.json") as f:
            evt_refracteds = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        evt_refracteds = {
            "event_id": int(evt_id),
            "achievements":[],
            "is_refracted": False
        }
    if str(evt_refracteds["event_id"]) != str(evt_id):
        print(f"Refracted event ID mismatch: {evt_id} vs {evt_refracteds['evt_id']}")
        return []
    for ra in evt_refracteds["achievements"]:
        # required keys
        for key,kt in (("player",int), ("round",int), ("achievement",str)):
            if key not in ra.keys() or type(ra[key]) != kt:
                print(f"Evt#{evt_id}: Invalid refracted achievement data:",ra)
                return []
        # optional keys
        for key, kt in (("stage",int),):
            if key in ra.keys() and type(ra[key]) != kt:
                print(f"Evt#{evt_id}: Invalid refracted achievement data:",ra)
                return []
    return evt_refracteds["achievements"], evt_refracteds.get("is_refracted", False)

def save_event_json(evt):
    makedirs(f"data/event_{evt['id']}/", exist_ok=True)
    with open(f"data/event_{evt['id']}/event.json", "w") as f:
        json.dump(evt, f)

def get_card_references(cardname):
    """
    Return a list of card (names) summoned/generated by the card.
    """
    refs = carddata[cardname].get("references", [])
    reflist = []
    for r in refs:
        if r.get("direction") == "TO" and r.get("kind") in ("SUMMON", "MASTERY", "GENERATE"):
            if r["name"] == "Shifting Currents" and cardname != "Kongming, Wayward Maven":
                # Special case so that random cards with a shifting currents bonus, like Strategem of Myriad ice, don't show Shifting Currents as a token
                continue
            reflist.append(carddata[r.get("name")])
    return reflist

def is_material(cardname):
    """
    Returns True if the card is a material deck card.
    Returns False otherwise.
    """
    card = carddata[cardname]
    if "CHAMPION" in card["types"] or "REGALIA" in card["types"]:
        return True
    return False

pricedb = PriceDB(PRICES_FOLDER, carddata)

decksim = DeckSim()
def get_cached_similarity(hash1, hash2):
    return decksim.get(hash1, hash2)
def store_similarity(hash1, hash2, sim):
    return decksim.store(hash1, hash2, sim)
def write_similarity_cache():
    decksim.write()
