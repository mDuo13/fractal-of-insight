#!/usr/bin/env python

import argparse
import json
import logging
import requests
from time import sleep, time

from fractal import config
from fractal.shared import ms_from_dt
from fractal.datalayer import get_event, get_deck, save_event_json, EventNotFound, NoDeck

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())
logger.propagate = False

crawldata = {
    "max_crawled": 0,
    "events": {}
}

def load_crawldata():
    global crawldata
    logger.info(f"Loading crawler data from file '{config.CRAWLER_FILE}'")
    try:
        with open(config.CRAWLER_FILE) as f:
            crawldata = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.error("Couldn't read cached event data")

class Consecutive404Streak(Exception):
    pass

# Event Summary format:
# events[id as string] = {
#     "status": "rsvp" | "canceled" | "started" | "complete" | "404" | "deleted" | "stale",
#     "interesting": 1 | 0, # more compact than true/false
#     "startAt": scheduled start, in ms since unix epoch (same as Omnidex format), only added if status == "rsvp"
# }

def save_crawldata():
    logger.debug(f"Writing crawler data to '{config.CRAWLER_FILE}'")
    with open(config.CRAWLER_FILE, "w") as f:
        json.dump(crawldata, f)

def due_for_update(evt_data, refresh_all_stale=False):
    if not evt_data:
        return True
    if refresh_all_stale and evt_data.get("status") == "stale":
        return True
    if evt_data.get("status") in ("complete", "stale", "canceled", "deleted", "canceled-suspended", "canceled-reset"):
        logger.info(f"Not due for update: status is {evt_data['status']}")
        return False

    ## Old logic: didn't update in-progress events, sometimes fooled by
    ## events that were initially scheduled in the far future.
    # if evt_data.get("status") in ("started", "completable", "404"):
    #     return True

    if evt_data.get("status") == "rsvp":
        if type(evt_data.get("startAt")) == str:
            start_time = ms_from_dt(evt_data["startAt"]) / 1000
            logger.debug(f"Converted start time from {evt_data['startAt']} to {start_time}")
        else:
            start_time = evt_data.get("startAt", 0) / 1000
        if start_time > time() + 86400:
            logger.debug("Scheduled for more than 1 day in future, don't bother updating yet")
            return False
    return True

def crawl_event(i, force_redownload=False, refresh_all_stale=False):
    logger.debug(f"Crawling #{i}")
    evt_data = crawldata["events"].get(str(i))
    updated = False

    if force_redownload or due_for_update(evt_data, refresh_all_stale):
        try:
            evt_full = get_event(i, force_redownload=True, save=False, short_circuit_fn=worth_investigating)
            logger.debug(f"Re-fetched event #{i}:")
            logger.debug(json.dumps(evt_full, indent=2))
            if i > crawldata["max_crawled"]:
                crawldata["max_crawled"] = i
            updated = True
        except EventNotFound:
            logger.info(f"Got EventNotFound while redownloading event #{i}.")
            if crawldata["max_crawled"] > i:
                evt_full = {"status": "deleted"}
                updated = True
            else:
                evt_full = {"status": "404"}

        interesting = is_interesting(evt_full)
        if interesting:
            print(f"""
--------------
Omni ID: {i}
{evt_full['name']}
{len(evt_full.get('players'))} players
Category: {evt_full.get('category')}
Decklists? {"Yes" if evt_full.get("decklists") else "No"}
""")
            save_event_json(evt_full)
            get_decks_from_event(evt_full)

        evt_data = {
            "status": evt_full["status"],
            "interesting": interesting
        }
        if evt_data["status"] == "rsvp":
            evt_data["startAt"] = evt_full.get("startAt", 0)
        crawldata["events"][str(i)] = evt_data

    return evt_data, updated

def get_decks_from_event(evt):
    for p in evt["players"]:
        is_public = p.get("isDecklistPublic")
        if is_public:
            try:
                get_deck(p["id"], evt["id"], is_public)
            except (NoDeck):
                logger.warning(f"Decklist public but not? Evt #{evt['id']} {p['username']}#{p['id']}")

def is_interesting(evt):
    if evt.get("status") in ("404", "deleted"):
        logger.debug(f"Uninteresting: {evt['status']}")
        return 0
    if evt.get('format') == "free-play":
        logger.info("Uninteresting: Event is free-play format")
        return 0

    if evt["api_version"] == "hybrid_v1":
        start_s = ms_from_dt(evt["date"]) / 1000
    elif evt["api_version"] == "internal_v1":
        start_s = evt["startAt"]/1000
    else:
        logger.warning(f"Unknown API version used for event: {evt['api_version']}")
    
    if evt.get("status") == "rsvp":
        if time() - start_s > config.STALE_GRACE_PERIOD:
            logger.info("Uninteresting: Event is scheduled in the past; marking stale.")
            evt["status"] = "stale"
            return 0
    if evt.get("status") in ("started", "completable"):
        if time() - start_s > config.EVT_MAX_LENGTH:
            logger.info("Uninteresting: Event has been ongoing too long; marking stale.")
            evt["status"] = "stale"
            return 0
    if evt.get("status") in ("stale", "deleted", "canceled"):
        logger.info(f"Uninteresting: event status is {evt['status']}")
        return 0
    if evt.get("status") in ("rsvp", "started", "completable"):
        if evt.get("category") in ("ascent", "nationals", "worlds"):
            logger.info(f"Ongoing, but interesting (category {evt['category']}")
            return 1
        logger.info(f"Incomplete event ({evt['status']}) not interesting yet.")
        return 0
    if evt["status"] != "complete":
        logger.info(f"Uninteresting: Unknown status: {evt['status']}")
        return 0
    if not evt.get('ranked'):
        logger.info(f"Uninteresting: Unranked")
        return 0

    players = evt.get("players", [])
    logger.debug(f"Player count is {len(players)}")
    # if len(players) < config.INTERESTING_PLAYER_COUNT:
    #     print(f"Only {len(players)} players")
    #     return 0

    if evt.get("category") == "regular" and not evt.get("decklists"):
        if len(players) >= config.INTERESTING_PLAYER_COUNT:
            logger.info(f"Uninteresting (no decklists, mid-sized player count) #{evt['id']} ({len(players)} players): {evt['name']}")
        if len(players) >= config.REALLY_INTERESTING_PLAYER_COUNT:
            logger.info("Interesting: no decklists, but really big player count")
            return 1
        logger.info(f"Uninteresting: only {len(players)} players & no decklists")
        return 0

    total_public_dls = sum([1 for p in evt["players"] if p.get("isDecklistPublic", False)])
    if total_public_dls < 1 and evt.get("category") == "regular":
        logger.info(f"Private decklists only. Mid-size online event?")
        return 0

    return 1


def worth_investigating(evt):
    """
    Simplified logic "is_interesting" logic to be passed to get_event(...) so 
    it can skip fetching the rest of the event details if it's obviously a 
    plain locals. Returns 1 if the event might be worth further investigation or
    0 if fetching the rest of the event can be short-circuited.
    """
    if evt['format'] == "free-play" or evt['status'] in (
        "rsvp","canceled","canceled-reset","canceled-suspended"):
        return 0
    if evt.get("category") == "regular" and not evt.get("decklists"):
        if len(evt["players"]) < config.REALLY_INTERESTING_PLAYER_COUNT:
            return 0
    return 1

def main(args):
    interesting_events = {}
    start = args.event_id
    logger.info(f"Starting at event #{start}")
    # if start < 0:
    #     start = crawldata["max_crawled"] + 1

    unsaved_data = 0
    consecutive404s = 0
    try:
        for i in range(start, 99999999):
            evt_data, updated = crawl_event(i, force_redownload=args.update, refresh_all_stale=args.stale)
            if updated:
                unsaved_data += 1
            if evt_data.get("interesting") and updated:
                interesting_events[i] = evt_data
            if unsaved_data >= config.CRAWL_SAVE_INTERVAL:
                save_crawldata()
                unsaved_data = 0
            if evt_data["status"] == "404":
                consecutive404s += 1
                # Usually, 5 consecutive 404's in a row is a sign that we're caught
                # up, but there is at least one notable gap at 60730-60758 inclusive
                if consecutive404s >= config.MAX_404_STREAK and i > crawldata["max_crawled"]:
                    raise Consecutive404Streak

    except (KeyboardInterrupt, Consecutive404Streak):
        save_crawldata()
        print(f"\n{len(interesting_events)} new interesting events:")
        print(", ".join([str(k) for k in interesting_events.keys()]))

def check_event(event_id):
    """
    Check a single event and explain if/why it's interesting or not.
    """
    logger.setLevel(logging.DEBUG)
    evt_data, updated = crawl_event(event_id)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Iterate over Omnidex events to look for interesting ones")
    parser.add_argument("event_id", type=int, help="Omnidex event ID to start at", nargs="?", default=1)
    parser.add_argument("-u", "--update", action="store_true", help="Redownload events regardless of cached status")
    parser.add_argument("-s", "--stale",  action="store_true", help="Redownload all stale events (in case they were updated)")
    parser.add_argument("-c", "--check", nargs="?", type=int, help="Check a specific event ID and explain if/why it's interesting or not.")
    args = parser.parse_args()
    load_crawldata()
    if args.check:
        check_event(args.check)
    else:
        main(args)
