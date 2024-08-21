#!/usr/bin/env python

import argparse
import jinja2
from os import makedirs
import os.path

import config
from shared import slugify
from omnievent import OmniEvent
from season import Season
from competition import SEASONS, EVENT_TYPES
from player import Player

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
        self.render("season.html.jinja2", szn_path, szn=season, EVENT_TYPES=EVENT_TYPES)

    def write_player(self, player, events):
        player.analyze()
        plr_path = f"player/{player.id}.html"
        self.render("player.html.jinja2", plr_path, player=player, events=events)

    def write_player_index(self, players=[], events={}):
        self.render("players.html.jinja2", "player/index.html", players=players, events=events)
    
    def write_all(self):
        """
        Write all known event pages as well as homepage, season landings, and player profiles.
        """
        seasons = {}
        known_players = {}
        all_events = {}
        for entry in os.scandir("./data"):
            if entry.is_dir() and entry.name[:6] == "event_":
                try:
                    e = OmniEvent(entry.name[6:])
                    all_events[e.id] = e
                except NotImplementedError:
                    print(f"Skipping team standard event (#{entry.name[6:]})")
                    continue
                if not seasons.get(e.season):
                    seasons[e.season] = Season(e.season)
                seasons[e.season].add_event(e)
                for entrant in e.players:
                    if entrant.id in known_players.keys():
                        known_players[entrant.id].add_entry(entrant)
                    else:
                        known_players[entrant.id] = Player(entrant)
                
                self.write_event(e)
        
        seasons_sorted = {k:seasons[v] for k,v in SEASONS.items() if v in seasons.keys()}

        for szn in seasons.values():
            self.write_season(szn)
        
        known_pids_sorted = [pid for pid, pl in known_players.items()]
        known_pids_sorted.sort(key=lambda x: known_players[x].sortkey())
        for pid in known_pids_sorted:
            self.write_player(known_players[pid], events=all_events)
        self.write_player_index(players=[known_players[pid] for pid in known_pids_sorted], events=all_events)

        self.render("index.html.jinja2", "index.html", seasons=seasons_sorted, EVENT_TYPES=EVENT_TYPES)

def main(args):
    builder = PageBuilder()
    for i in args.event_id:
        e = OmniEvent(i, force_redownload=args.update)
        builder.write_event(e)
    builder.write_all()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize an Omnidex event (works better if decklists are public)")
    parser.add_argument("event_id", type=int, help="Omnidex event ID to look up", nargs="*", default=None)
    parser.add_argument("-a", "--all", action="store_true", help="Rebuild all cached events")
    parser.add_argument("-u", "--update", action="store_true", help="Redownload the specified omnidex event")
    args = parser.parse_args()
    main(args)
