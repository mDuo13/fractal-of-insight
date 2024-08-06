#!/usr/bin/env python

import argparse
import json
import requests
from time import sleep

import config
from datalayer import get_event, save_event_json, EventNotFound

try:
    with open(config.CRAWLER_FILE) as f:
        crawldata = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    print("Couldn't read cached event data")
    crawldata = {
        "max_crawled": 0,
        "events": {}
    }

# Event Summary format:
# events[id as string] = {
#     "status": "rsvp" | "canceled" | "started" | "complete" | "404",
#     "interesting": True | False,
# }

def save_crawldata():
    with open(config.CRAWLER_FILE, "w") as f:
        json.dump(crawldata, f)

def crawl_event(i): # TODO: implement a force_redownload
    evt_data = crawldata["events"].get(str(i))

    if not evt_data or evt_data.get("status") in ("rsvp", "started"):
        try:
            evt_full = get_event(i, save=False)
            if i > crawldata["max_crawled"]:
                crawldata["max_crawled"] = i
        except EventNotFound:
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
        
        evt_data = {
            "status": evt_full["status"],
            "interesting": interesting
        }
        crawldata["events"][str(i)] = evt_data

    return evt_data


def is_interesting(evt):
    if evt.get("status") in ("rsvp", "canceled", "started"):
        print("Status:",evt.get("status"))
        return False
    if evt["status"] != "complete":
        print(f"Unknown status: {evt['status']}")
        return False
    if not evt.get('ranked'):
        print("Unranked")
        return False
    
    players = evt.get("players", [])
    if len(players) < config.INTERESTING_PLAYER_COUNT:
        print(f"Only {len(players)} players")
        return False
    
    if evt.get("category") == "regular" and not evt.get("decklists"):
        print(f"Big locals? #{evt['id']} ({len(players)} players): {evt['name']}")
        if len(players) > config.REALLY_INTERESTING_PLAYER_COUNT:
            return True
        return False
    
    return True
    

def main(args):
    interesting_events = {}
    start = args.event_id
    if start < 0:
        start = crawldata["max_crawled"] + 1
    
    unsaved_data = 0
    try:
        for i in range(start, 99999999):
            evt_data = crawl_event(i)
            if evt_data.get("interesting"):
                interesting_events[i] = evt_data
            unsaved_data += 1
            if unsaved_data >= config.CRAWL_SAVE_INTERVAL:
                save_crawldata()
                unsaved_data = 0
            
    except KeyboardInterrupt:
        save_crawldata()
        print(f"\n{len(interesting_events)} interesting events:")
        print(", ".join([str(k) for k in interesting_events.keys()]))



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Iterate over Omnidex events to look for interesting ones")
    parser.add_argument("event_id", type=int, help="Omnidex event ID to start at", nargs="?", default=-1)
    #parser.add_argument("--reverse", "-r", help="Count down instead of up")
    args = parser.parse_args()
    main(args)
