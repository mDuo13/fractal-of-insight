import json
import re
import requests
from requests.adapters import HTTPAdapter, Retry
from time import sleep
from os import makedirs, scandir, path

from shared import slugify, fix_case
from cards import ERRATA, PRIZE_EQUIVALENTS, REMOVED_FROM_PRXY
from carddb import CardDB
from decksim import DeckSim
from tcgplayer import TCG_ABBR, TCGP_CARDNAMES

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
            if not public_on_omni:
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

def get_spoiler(szn):
    try:
        with open(f"data/spoilers/{szn}/event.json") as f:
            evt = json.load(f)
    except (FileNotFoundError):
        print("Couldn't get event.json for spoiler season", szn)
        evt = {}
    return evt

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

carddata = CardDB()

try:
    with open("data/card_spoilers.json") as f:
        spoilerdata = json.load(f)
except FileNotFoundError:
    print("No spoiler data to load")
    spoilerdata = {}

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
    # ed_slug = index_json["result_editions"][0]["slug"]
    #card_img = f"https://ga-index-public.s3.us-west-2.amazonaws.com/cards/{ed_slug}.jpg"
    # card_img = f"https://api.gatcg.com/cards/images/{ed_slug}.jpg"
    # print("Saving card data to cache...")
    # makedirs("data/", exist_ok=True)
    # carddata[cardname] = {
    #     "img": card_img
    # }
    # with open(f"data/cards.json", "w") as f:
    #     json.dump(carddata, f)
    return card_img

FM_EFFECT = '**Floating Memory**'
CB_FM = '[Class Bonus] **Floating Memory**'
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
            "achievements":[]
        }
    if str(evt_refracteds["event_id"]) != str(evt_id):
        print(f"Refracted event ID mismatch: {evt_id} vs {evt_refracteds['evt_id']}")
        return []
    for ra in evt_refracteds["achievements"]:
        for key,kt in (("player",int), ("round",int), ("achievement",str)):
            if key not in ra.keys() or type(ra[key]) != kt:
                print(f"Evt#{evt_id}: Invalid refracted achievement data:",ra)
                return []
    return evt_refracteds.get("achievements", [])

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

def is_valid_in_decklists(cardname):
    """
    Returns true if the card should appear in decklists.
    Returns false if the card should not, such as tokens or masteries.
    """
    card = carddata[cardname]
    if "TOKEN" in card["types"]:
        return False
    if "MASTERY" in card["types"]:
        return False
    return True

# Load tcgcsv price data
try:
    pricedata = {}
    for entry in scandir(PRICES_FOLDER):
        if entry.is_file() and entry.name[-5:] == ".json" and entry.name != "price-meta.json":
            with open(entry) as f:
                pricelist = json.load(f)
            pricedata[entry.name[:-5]] = pricelist

except FileNotFoundError:
    print("Didn't find cached price data")
    pricedata = {}

try:
    with open(path.join(PRICES_FOLDER, "price-meta.json")) as f:
        PRICE_META = json.load(f)
except FileNotFoundError:
    print("Didn't find price metadata")
    PRICE_META = {"Updated": "Never", "prefixes": []}

def format_price(price):
    """
    Convert a price to a string in the format of "$NN.NN",
    or "Unavailable" if it's None
    """
    if price == 0.001:
        return f"N/A (Proxia's Vault)"
    elif price:
        return f"${price:.2f}"
    return "Unavailable"

def get_card_price(cardname, sub_prizes=False):
    """
    Return the price for the cheapest version of the given cardname,
    """
    if sub_prizes and cardname in PRIZE_EQUIVALENTS.keys():
        # Get the price of regular Spirit of Wind, for example, instead of Kaze
        cardname = PRIZE_EQUIVALENTS[cardname]
    card = carddata[cardname]
    fullname = fix_case(card["fullname"]) # For double-faced cards for example
    if fullname in TCGP_CARDNAMES.keys():
        fullname = TCGP_CARDNAMES[fullname]
    prices = []
    for ed in card["editions"]:
        prefix = ed["set"]["prefix"]
        if prefix == "PRXY":
            # Proxia's Vault cards are, by definition, free to proxy.
            # But let's return a nonzero price so it doesn't get
            # treated the same as None.
            return 0.001
        ed_price = low_price_by_edition(fullname, prefix)
        if ed_price:
            prices.append(ed_price)
    if prices:
        price = min(prices)
        return price

    #print(f"Couldn't get a price for {fullname}.")
    return None

def low_price_by_edition(fullname, prefix):
    low_price = None
    if prefix in TCG_ABBR.keys():
        for abbr in TCG_ABBR[prefix]:
            for item in pricedata[abbr].values():
                if item.get("name") == fullname:
                    new_price = low_price_for_product(item)
                    if not new_price: # could be None for no listings
                        continue
                    if not low_price or new_price < low_price:
                        low_price = new_price
    elif prefix not in pricedata.keys():
        print(f"No tcgp data for set '{prefix}'")
    else: # Prefix should match
        for item in pricedata[prefix].values():
            trimmed_name = re.sub(r"\(\w+\)", "", item.get("name","")).strip()
            if trimmed_name == fullname:
                new_price = low_price_for_product(item)
                if not new_price: # could be None for no listings
                    continue
                if not low_price or new_price < low_price:
                    low_price = new_price
    return low_price

def low_price_for_product(item):
    # May have multiple price listings, like foil vs nonfoil
    all_prices = [p["lowPrice"] for p in item["prices"] if p.get("lowPrice")]
    if not all_prices:
        # No price data, maybe no listings
        return None
    return min(all_prices)

decksim = DeckSim()
def get_cached_similarity(hash1, hash2):
    return decksim.get(hash1, hash2)
def store_similarity(hash1, hash2, sim):
    return decksim.store(hash1, hash2, sim)
def write_similarity_cache():
    decksim.write()
