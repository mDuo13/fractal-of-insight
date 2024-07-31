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

class PageBuilder:
    def __init__(self):
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(config.TEMPLATE_DIR)
        )
        self.env.globals["slugify"] = slugify
        self.env.globals["config"] = config
    
    def render(self, template, write_to, **kwargs):
        """
        Load the template with the given name, and write the HTML file in the 
        configured output directory, passing kwargs as context to the template.
        """
        t = self.env.get_template(template)
        html = t.render(**kwargs)

        out_dir, out_file = os.path.split(write_to)
        whole_out_dir = os.path.join(config.OUTDIR, out_dir)
        makedirs(whole_out_dir, exist_ok=True)
        whole_out_file = os.path.join(whole_out_dir, out_file)
        print("Writing to", whole_out_file)
        with open(whole_out_file, "w") as f:
            f.write(html)
    
    def write_event(self, e):
        """
        Write an Omnidex event page.
        """
        e_path = f"{e.season}/{e.id}.html"
        self.render("event.html.jinja2", e_path, evt=e)
    
    def write_season(self, season):
        """
        Write a season summary page.
        """
        season.analyze()
        szn_path = f"{season.code}/index.html"
        self.render("season.html.jinja2", szn_path, szn=season)
    
    def write_index(self, rebuild_all=False):
        """
        Write the homepage and possibly all known event pages.
        """
        seasons = {}
        for entry in os.scandir("./data"):
            if entry.is_dir() and entry.name[:6] == "event_":
                e = OmniEvent(entry.name[6:])
                if not seasons.get(e.season):
                    seasons[e.season] = Season(e.season)
                seasons[e.season].add_event(e)
                
                if rebuild_all:
                    self.write_event(e)
        
        if rebuild_all:
            for szn in seasons.values():
                self.write_season(szn)
        seasons_sorted = {k:seasons[v] for k,v in SEASONS.items() if v in seasons.keys()}
        self.render("index.html.jinja2", "index.html", seasons=seasons_sorted)

def main(args):
    builder = PageBuilder()
    for i in args.event_id:
        e = OmniEvent(i, force_redownload=args.update)
        builder.write_event(e)
    builder.write_index(args.all)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize an Omnidex event (works better if decklists are public)")
    parser.add_argument("event_id", type=int, help="Omnidex event ID to look up", nargs="*", default=None)
    parser.add_argument("-a", "--all", action="store_true", help="Rebuild all cached events")
    parser.add_argument("-u", "--update", action="store_true", help="Redownload the specified omnidex event")
    args = parser.parse_args()
    main(args)
