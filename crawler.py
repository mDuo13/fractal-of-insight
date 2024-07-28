#!/usr/bin/env python

import argparse
import json
import requests
from time import sleep

INTERESTING_PLAYER_COUNT = 20

def main(args):
    interesting_events = []
    try:
        for i in range(args.event_id, 99999999):
            sleep(0.5)
            print(f"Downloading event {i} JSON...")
            evt_raw = requests.get(f"https://omni.gatcg.com/api/events/event?id={i}")
            if evt_raw.status_code != 200:
                print(f"Failed. Omni API response: {evt_raw.status_code}")
                continue
            
            try:
                evt = evt_raw.json()
            except json.JSONDecodeError:
                print("Failed to parse Omnidex response")
                continue
            
            #print("...done.")

            if not evt.get("status"):
                print("No event status?")
                continue

            if evt["status"] == "rsvp":
                print("Event hasn't started yet")
                continue

            if evt["status"] == "canceled":
                print("Event was canceled")
                continue

            if evt["status"] == "started":
                print("Event hasn't finished")
                continue
            
            if evt["status"] != "complete":
                print(f"Unknown status: {evt['status']}")
                continue

            players = evt.get("players", [])
            if len(players) < INTERESTING_PLAYER_COUNT:
                print(f"Only {len(players)} players")
                continue
            
            if not evt.get('ranked'):
                print("Unranked")
                continue

            if evt.get("category") == "regular" and not evt.get("decklists"):
                print(f"Big locals? #{i} ({len(players)} players): {evt['name']}")
                continue

            interesting_events.append(f"""
--------------
Omni ID: {i}
{evt['name']}
{len(players)} players
Category: {evt.get('category')}
Decklists? {"Yes" if evt.get("decklists") else "No"}
""")
            print(interesting_events[-1])
    except KeyboardInterrupt:
        print("\n\nInteresting events:")
        [print(e) for e in interesting_events]

        

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Iterate over Omnidex events to look for interesting ones")
    parser.add_argument("event_id", type=int, help="Omnidex event ID to start at", nargs="?", default=1)
    #parser.add_argument("--reverse", "-r", help="Count down instead of up")
    args = parser.parse_args()
    main(args)
