import json
import re
import requests
from logging import warning
from requests.adapters import HTTPAdapter, Retry
from time import sleep, time
from os import makedirs, scandir, path

from .shared import slugify, fix_case, lineage, ms_from_dt
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
            if dl and dl.get('visible') == False:
                raise NoDeck()
        except (FileNotFoundError, json.JSONDecodeError):
            if not public_on_omni or int(evt_id) == 384: #Special case for Ascent Ontario which was before Omni supported decklists
                raise NoDeck()
            print(f"Downloading #{p_id}'s decklist...")
            ## Old (Omnidex API v1) way to get one dl:
            # dl_raw = fetch(f"https://omni.gatcg.com/api/events/decklist?id={evt_id}&player={p_id}")
            ## New way gets all decklists for event using official API
            dl_raw = fetch(f"https://api.gatcg.com/omnidex/events/{evt_id}/decklists")
            print("...done.")
            all_dls = dl_raw.json()
            if dl_raw.status_code != 200 or (type(all_dls)==dict and all_dls.get("error")):
                raise NoDeck(f"Status code {dl_raw.status_code} fetching evt {evt_id} decklists")

            # Save *all* the decklists to disk, then return the requested one
            dl = None # The decklist we're actually looking for
            for dlw in all_dls:
                assert type(dlw['player']) == int
                with open(f"data/event_{evt_id}/deck_{dlw['player']}.json", "w") as f:
                    json.dump(dlw['decklist'], f)
                if p_id == dlw['player']:
                    dl = dlw['decklist']
            if not dl:
                raise NoDeck(f"Decklist for player #{p_id} not found in event #{evt_id}")
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

def get_event(evt_id, force_redownload=False, save=True, dl_decklists=False, short_circuit_fn=None):
    try:
        if force_redownload:
            raise ForceReDL
        with open(f"data/event_{evt_id}/event.json") as f:
            evt = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, ForceReDL):
        evt = collate_event_from_apis(evt_id, short_circuit_fn=short_circuit_fn)
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
    if "api_version" not in evt.keys():
        if "matchConfigSwiss" in evt.keys():
            evt["api_version"] = "internal_v1"
        elif "swissMatchConfig" in evt.keys():
            evt["api_version"] = "hybrid_v1"
        else:
            print(f"Unknown API version for event #{evt['id']}")
            exit(1)
    return evt

def fetch_json(url):
    r = fetch(url)
    if r.status_code == 404:
        raise EventNotFound
    return r.json()

def collate_event_from_apis(evt_id, short_circuit_fn=None):
    """
    Download an event from multiple APIs (mostly the official Omnidex API where
    possible) and combining the result into one JSON file sorta resembling
    the old Omnidex API format for convenience. Throw EventNotFound if any of
    the API requests fails.
    """
    print(f"Downloading event #{evt_id} base JSON...")
    evt = fetch_json(f"https://api.gatcg.com/omnidex/events/{evt_id}")
    evt["api_version"] = "hybrid_v1"

    if short_circuit_fn: # If a function that returns 0 for uninteresting evts
        if not short_circuit_fn(evt):
            return evt

    print(f"Downloading player data for event #{evt_id}")
    evt["players"] = fetch_json(f"https://api.gatcg.com/omnidex/events/{evt_id}/players")
    
    # Short-circuit for events that haven't at least started
    if evt["status"] not in ("completable","complete","started"):
        return evt
    # Also short-cut freeplay events
    if evt["format"] == "free-play":
        return evt

    print(f"Downloading internal API player data for event #{evt_id}...")
    iplayers = fetch_json(f"https://omni.gatcg.com/api/v2/events/users?id={evt_id}")
    for ipl in iplayers:
        ipl_id = int(ipl['id'])
        for pl in evt["players"]:
            if ipl_id == pl['id']:
                pl['scoreElo'] = ipl['scores']['player']['elo']['value']
                pl['rankElo'] = ipl['scores']['player']['elo']['rank']
                pl['scoreVP'] = ipl['scores']['player']['vp']['value']
                if ipl.get('suspended'):
                    pl['suspendedUntil'] = ms_from_dt(ipl['suspended']['expires'])
                break
    
    if evt.get("judges", []):
        print(f"Downloading judge information for event #{evt_id}...")
        evt["judges"] = fetch_json(f"https://api.gatcg.com/omnidex/events/{evt_id}/judges")
        for ipl in iplayers:
            # add scoreVP and suspendedUntil data, if available, for judges too
            ipl_id = int(ipl['id'])
            for jd in evt["judges"]:
                if ipl_id == jd['id']:
                    jd['scoreVP'] = ipl['scores']['player']['vp']['value']
                if ipl.get('suspended'):
                    jd['suspendedUntil'] = ms_from_dt(ipl['suspended']['expires'])
                break

    if evt.get("teams"):
        print(f"Downloading team information for event #{evt_id}...")
        teams = fetch_json(f"https://api.gatcg.com/omnidex/events/{evt_id}/teams")
        for tm in teams:
            for seat in tm["players"]:
                # Find matching player and add their team info for backwards compat
                for pl in evt["players"]:
                    if pl["id"] == seat["id"]:
                        pl["team"] = tm["name"]
                        pl["teamSlot"] = int(seat["slot"]) # Hopefully this doesn't break in the future
                        break
        
        print(f"Downloading team standings for event #{evt_id}")
        standings = fetch_json(f"https://api.gatcg.com/omnidex/events/{evt_id}/standings")
        for st in standings["standings"]:
            for tm in evt["teams"]:
                if tm["name"] == st["name"]:
                    # Add standings info to team dict
                    tm.update(st)
                    break
            else:
                print(f"Standings not found for team: {st['name']}")
    
    else:
        print(f"Downloading player standings for event #{evt_id}")
        standings = fetch_json(f"https://api.gatcg.com/omnidex/events/{evt_id}/standings")
        for st in standings["standings"]:
            for pl in evt["players"]:
                if pl["id"] == st["id"]:
                    # Add standings information to player dict
                    pl.update(st)
                    break
            else:
                print(f"Standings not found for player #{pl['id']}?")

    
    for stage in evt["stages"]:
        stage["rounds"] = []
        roundn = 1
        while True:
            print(f"Downloading pairings for stage {stage['id']} ({stage['type']}) round {roundn}")
            pairings_r = fetch(f"https://api.gatcg.com/omnidex/events/{evt_id}/pairings?stage={stage['id']}&round={roundn}")
            if pairings_r.status_code == 404:
                print(f"Couldn't find pairings for stage {stage['id']} round {roundn}. Maybe it's ongoing?")
                break
            prdata = pairings_r.json()
            thisround = {
                "id": prdata["round"]["id"],
                "pairings": {},
                "matches": prdata["pairings"],
                "status": prdata["round"]["status"]
            }
            # Re-create the simple 'ID':ID pairings mapping from the old API
            for m in prdata["pairings"]:
                if len(m["pairing"]) > 1: #Not a bye
                    p1id = m["pairing"][0]["id"]
                    p2id = m["pairing"][1]["id"]
                    thisround["pairings"][str(p1id)] = p2id
                    thisround["pairings"][str(p2id)] = p1id
            stage["rounds"].append(thisround)
            roundn += 1
            if roundn > prdata["round"]["total"]:
                break
    
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
