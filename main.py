#!/usr/bin/env python

import argparse
import jinja2
from os import makedirs
import os.path

import config
from shared import slugify
from omnievent import OmniEvent
from season import Season
from competition import SEASONS

def main(args):
    if args.event_id:
        e = OmniEvent(args.event_id)
        write_event(e)
    else:
        build_index(args.all)

def render(template, write_to, **kwargs):
    # TODO: setup a jinja env
    with open(template, "r") as f:
        ts = f.read()
    t = jinja2.Template(ts)
    html = t.render(**kwargs, config=config, slugify=slugify)

    out_dir, out_file = os.path.split(write_to)
    whole_out_dir = os.path.join(config.OUTDIR, out_dir)
    makedirs(whole_out_dir, exist_ok=True)
    whole_out_file = os.path.join(whole_out_dir, out_file)
    print("Writing to", whole_out_file)
    with open(whole_out_file, "w") as f:
        f.write(html)

def write_event(e):
    e_path = f"{e.season}/{e.id}.html"
    render("event.html.jinja2", e_path, evt=e)

def sum_season(season):
    season.analyze()
    szn_path = f"{season.code}/index.html"
    render("season.html.jinja2", szn_path, szn=season)
    
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
    seasons_sorted = {k:seasons[v] for k,v in SEASONS.items() if v in seasons.keys()}
    render("index.html.jinja2", "index.html", seasons=seasons_sorted)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize an Omnidex event (requires all decklists to be public)")
    parser.add_argument("event_id", type=int, help="Omnidex event ID to look up", nargs="?", default=None)
    parser.add_argument("-a", "--all", action="store_true", help="Rebuild all cached events")
    args = parser.parse_args()
    main(args)
