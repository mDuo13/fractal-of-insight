#!/usr/bin/env python

import argparse
import jinja2
from os import makedirs
import os.path

import config
from shared import slugify, OVERALL
from omnievent import OmniEvent, Team3v3Event, IsTeamEvent
from season import Season, SEASONS, Format, FORMATS
from competition import EVENT_TYPES, TEAM_STANDARD
from player import Player
from archetypes import ARCHETYPES

class PageBuilder:
    def __init__(self):
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(config.TEMPLATE_DIR)
        )
        self.env.globals["slugify"] = slugify
        self.env.globals["config"] = config
        self.env.globals["EVENT_TYPES"] = EVENT_TYPES
        self.env.globals["TEAM_STANDARD"] = TEAM_STANDARD
        self.env.globals["OVERALL"] = OVERALL
        self.env.filters["slugify"] = slugify
    
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
        if e.format == TEAM_STANDARD:
            template = "teamevent.html.jinja2"
        else:
            template = "event.html.jinja2"
        self.render(template, e_path, evt=e)
    
    def write_season(self, season):
        """
        Write a season summary page.
        """
        season.analyze()
        szn_path = f"{season.code}/index.html"
        self.render("season.html.jinja2", szn_path, szn=season)

    def write_formats(self, formats):
        """
        Write a summary of different formats (by card legality)
        """
        for fmt in formats:
            fmt.analyze()
        fmt_path = "formats/index.html"
        self.render("formats.html.jinja2", fmt_path, formats=formats)

    def write_player(self, player, events, known_players):
        player.analyze()
        plr_path = f"player/{player.id}.html"
        self.render("player.html.jinja2", plr_path, player=player, events=events, players=known_players)

    def write_player_index(self, players=[], events={}):
        self.render("players.html.jinja2", "player/index.html", players=players, events=events)

    def write_archetype(self, archetype, players=[], events=[], seasons=[], wins=0):
        archetype.analyze()
        slug = slugify(archetype.name)
        arche_path = f"deck/{slug}.html"
        self.render("archetype.html.jinja2", arche_path, arche=archetype, players=players, events=events, seasons=seasons, wins=wins)

    def write_archetype_index(self, archetypes, aew):
        self.render("archetypes.html.jinja2", "deck/index.html", archetypes=archetypes, aew=aew)
    
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
                except IsTeamEvent:
                    e = Team3v3Event(entry.name[6:])
                    all_events[e.id] = e
                    #print(f"Skipping team standard event (#{entry.name[6:]})")
                    #continue
                if not seasons.get(e.season):
                    seasons[e.season] = Season(e.season)
                seasons[e.season].add_event(e)

                for fmt in FORMATS.values():
                    if fmt.should_include(e):
                        fmt.add_event(e)
                        break

                for entrant in e.players:
                    if entrant.id in known_players.keys():
                        known_players[entrant.id].add_entry(entrant)
                    else:
                        known_players[entrant.id] = Player(entrant)
                    known_players[entrant.id].track_rivals_for_event(e)
                
                self.write_event(e)
        
        seasons_sorted = {k:seasons[v] for k,v in SEASONS.items() if v in seasons.keys()}

        for szn in seasons.values():
            self.write_season(szn)

        formats_desc = list(reversed(FORMATS.values()))
        self.write_formats(formats_desc)
        
        known_pids_sorted = [pid for pid, pl in known_players.items()]
        known_pids_sorted.sort(key=lambda x: known_players[x].sortkey())
        for pid in known_pids_sorted:
            self.write_player(known_players[pid], all_events, known_players)
        self.write_player_index(players=[known_players[pid] for pid in known_pids_sorted], events=all_events)

        aew = {} #archetype event wins
        for szn in seasons.values():
            for arche,wins in szn.arche_wins.items():
                if arche in aew.keys():
                    aew[arche] += wins
                else:
                    aew[arche] = wins

        for a in ARCHETYPES.values():
            if a.name not in aew.keys():
                aew[a.name] = []
            self.write_archetype(a, known_players, all_events, seasons_sorted, aew[a.name])

        arches_sorted = [a for a in ARCHETYPES.values()]
        arches_sorted.sort(key=lambda x: len(x.matched_decks), reverse=True)
        self.write_archetype_index(arches_sorted, aew)

        self.render("index.html.jinja2", "index.html", seasons=seasons_sorted)

def main(args):
    builder = PageBuilder()
    for i in args.event_id:
        try:
            e = OmniEvent(i, force_redownload=args.update)
        except IsTeamEvent:
            e = Team3v3Event(i, force_redownload=args.update)
        #builder.write_event(e)
    builder.write_all()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize an Omnidex event (works better if decklists are public)")
    parser.add_argument("event_id", type=int, help="Omnidex event ID to look up", nargs="*", default=None)
    parser.add_argument("-a", "--all", action="store_true", help="Rebuild all cached events")
    parser.add_argument("-u", "--update", action="store_true", help="Redownload the specified omnidex event")
    args = parser.parse_args()
    main(args)
