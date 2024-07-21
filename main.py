#!/usr/bin/env python

import argparse
import jinja2
from os import makedirs
import os.path

import config
from shared import slugify
from omnievent import OmniEvent
from season import Season

def main(args):
    if args.event_id:
        e = OmniEvent(args.event_id)
        write_event(e)
    else:
        build_index(args.all)

def write_event(e):
    with open("event.html.jinja2", "r") as f:
        ts = f.read()
    t = jinja2.Template(ts)
    evt_html = t.render(evt=e, slugify=slugify)

    chartpath = os.path.join(config.OUTDIR, e.season)
    makedirs(chartpath, exist_ok=True)
    chartfile = os.path.join(chartpath, str(e.id)+".html")
    print("Writing to", chartfile)

    with open(chartfile, "w") as f:
        f.write(evt_html)

def sum_season(season):
    season.analyze_decks()
    season.calc_headtohead()
    
    with open("season.html.jinja2", "r") as f:
        ts = f.read()
    t = jinja2.Template(ts)
    szn_html = t.render(szn=season)
    chartpath = os.path.join(config.OUTDIR, season.code)
    makedirs(chartpath, exist_ok=True)
    chartfile = os.path.join(chartpath, "index.html")
    print("Writing to", chartfile)

    with open(chartfile, "w") as f:
        f.write(szn_html)

def build_index(rebuild_all):
    seasons = {}
    for entry in os.scandir("./data"):
        if entry.is_dir() and entry.name[:6] == "event_":
            e = OmniEvent(entry.name[6:])
            if not seasons.get(e.season):
                seasons[e.season] = Season(e.season)
            seasons[e.season].events.append(e)
            
            if rebuild_all:
                write_event(e)
    
    if rebuild_all:
        for szn in seasons.values():
            sum_season(szn)

    with open("index.html.jinja2", "r") as f:
        ts = f.read()
    t = jinja2.Template(ts)
    s = t.render(seasons=seasons)

    chartpath = os.path.join(config.OUTDIR)
    indexfile = os.path.join(chartpath, "index.html")
    with open(indexfile, "w") as f:
        f.write(s)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize an Omnidex event (requires all decklists to be public)")
    parser.add_argument("event_id", type=int, help="Omnidex event ID to look up", nargs="?", default=None)
    parser.add_argument("-a", "--all", action="store_true", help="Rebuild all cached events")
    args = parser.parse_args()
    main(args)
