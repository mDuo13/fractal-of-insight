#!/usr/bin/env python

import argparse
import json
import jinja2
from logging import warning
from os import makedirs
import os.path
from math import ceil
from collections import defaultdict

import fractal.config as config
from fractal.datalayer import carddata, get_event, get_card_img, pricedb, write_similarity_cache, is_material
from fractal.shared import slugify, rank_card, OVERALL, REGIONS, ms_to_date, EVENT_TYPES, TEAM_STANDARD
from fractal.omnievent import OmniEvent, Team3v3Event, IsTeamEvent, NotStarted
from fractal.season import Season, SEASONS, FORMATS
from fractal.player import Player
from fractal.archetypes import ARCHETYPES, NO_ARCHETYPE, MAT_DIFF_CARD_LIMIT, MAIN_DIFF_CARD_LIMIT, SIDE_DIFF_CARD_LIMIT, RISING_CARD_LIMIT
from fractal.cards import ERRATA, BANLIST
from fractal.cardstats import ALL_CARD_STATS, PAD_UNTIL
from fractal.achievements import ACHIEVEMENTS, GAS, REFRACTED_ACHIEVEMENTS, REFRACTED_ARTISTS
from fractal.champs import CHAMP_DATA
from fractal.hipster import HipsterDB

FAST_CUTOFF = 5 # process a minimal number of events for "fast" mode (testing purposes)

class PageBuilder:
    def __init__(self, force_evts=[]):
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(config.TEMPLATE_DIR)
        )
        self.env.globals["slugify"] = slugify
        self.env.globals["config"] = config
        self.env.globals["EVENT_TYPES"] = EVENT_TYPES
        self.env.globals["REGIONS"] = REGIONS
        self.env.globals["TEAM_STANDARD"] = TEAM_STANDARD
        self.env.globals["OVERALL"] = OVERALL
        self.env.globals["ACHIEVEMENTS"] = ACHIEVEMENTS
        self.env.globals["REFRACTED_ARTISTS"] = REFRACTED_ARTISTS
        self.env.filters["slugify"] = slugify
        self.env.filters["ms_to_date"] = ms_to_date
        self.env.trim_blocks = True
        self.env.lstrip_blocks = True
        self.env.autoescape = True

        self.seasons = {}
        self.players = {}
        self.events = {}
        self.cards = ALL_CARD_STATS
        self.index = carddata
        self.known_judges = defaultdict(list)
        self.hipster_floor = 99999 # minimum Hipster rating of any deck

        self.load_all(force_evts=force_evts)

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
        # skip overwriting matching files,
        # which should hopefully save bandwidth on transferring
        # identical files each time
        try:
            with open(whole_out_file, "r") as f:
                if html == f.read():
                    #print("Skipping unchanged file", whole_out_file)
                    return
        except FileNotFoundError:
            pass
        print("Writing to", whole_out_file)
        with open(whole_out_file, "w") as f:
            f.write(html)

    def format_sightings_json(self, sightings):
        """
        Turns a list of Deck entries into JSON data that can be inlined into
        a page for dynamically loading sightings of a given archetype/card/etc.
        """
        sj = []
        for deck in sightings:
            entrant = deck.entrant
            event = self.events[entrant.evt_id]
            if entrant.dq:
                placement = "DQ"
            elif event.format == TEAM_STANDARD:
                t = event.teams[entrant.team.lower()]
                placement = f"{t.placement}/{len(event.teams)} teams"
            else:
                placement = f"{entrant.placement}/{len(event.players)}"
            de = {
                "date": deck.date,
                "p_id": entrant.id,
                "p_name": entrant.username,
                "evt_id": int(entrant.evt_id),
                "evt_name": event.name,
                "evt_cat": event.category['shortname'],
                "szn": event.season,
                "d_name": str(deck),
                "place": placement,
                "record": entrant.record,
                "els": deck.els,
                "arches": deck.archetypes,
                "lineages": deck.lineages,
                "subtypes": deck.subtypes,
            }
            if event.format != "standard":
                de["evt_fmt"] = event.format
            if event.winner and (event.winner.deck == deck or event.winner.topcut_deck == deck):
                de["winner"] = 1
            if deck.is_topcut_deck:
                de["topcut"] = 1
            if deck.entrant.score > event.fiftypct_points:
                de["high"] = 1
            sj.append(de)
        return json.dumps(sj)

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
        szn_path = f"{season.code}/index.html"
        self.render("season.html.jinja2", szn_path, szn=season)

    def write_subseasons(self, parent_szn):
        """
        Write a summary of different formats (by card legality)
        """
        fmt_path = f"{parent_szn.code}/subformats.html"
        self.render("formats.html.jinja2", fmt_path, formats=parent_szn.subformats, szn=parent_szn)

    def write_player(self, player):
        plr_path = f"player/{player.id}.html"
        self.render("player.html.jinja2", plr_path, player=player, events=self.events, players=self.players)

    def write_player_index(self, players=[], events={}):
        players_sorted = [p for p in self.players.values()]
        players_sorted.sort(key=lambda x: x.sortkey())

        pj =[p.json_summary() for p in players_sorted]
        pjs = json.dumps(pj)

        self.render("players.html.jinja2", "player/index.html", players=players_sorted, events=self.events, players_json=pjs)

    def write_archetype(self, archetype):
        slug = slugify(archetype.name)
        arche_path = f"deck/{slug}.html"
        sightings_json = self.format_sightings_json(archetype.matched_decks[:config.MAX_SIGHTINGS])

        # New JS-powered sightings section
        self.render("archetype.html.jinja2", arche_path, arche=archetype,
                    players=self.players, seasons=self.seasons,
                    wins=self.aew[archetype.name], sightings_json=sightings_json
        )

    def write_archetype_index(self):
        archetypes = [a for a in ARCHETYPES.values()]
        archetypes.sort(key=lambda x: len(x.matched_decks), reverse=True)
        archetypes.append(NO_ARCHETYPE)
        self.render("archetypes.html.jinja2", "deck/index.html", archetypes=archetypes, aew=self.aew, seasons=self.seasons)

    def write_card_index(self):
        card_stats_by_set = ALL_CARD_STATS.split_by_set()
        self.render("cards.html.jinja2", "card/index.html", cardstats=ALL_CARD_STATS, carddata=carddata, set_groups=carddata.get_set_groups(), get_card_img=get_card_img, card_stats_by_set=card_stats_by_set, card_prices=pricedb, PAD_UNTIL=PAD_UNTIL)

    def write_champ(self, champstats):
        write_to = f"champion/{slugify(champstats.name)}.html"
        wins = self.cew.get(champstats.name,[])
        self.render("champion.html.jinja2", write_to, champion=champstats.name,
            stats=champstats, champlineage=champstats.cards, wins=wins)

    def write_champ_index(self):
        champs_sorted = [(k,v) for k,v in CHAMP_DATA.items()]
        champs_sorted.sort(key=lambda x:len(x[1].matched_decks), reverse=True)
        champions = {k:v for k,v in champs_sorted}
        write_to = "champion/index.html"
        self.render("champions.html.jinja2", write_to, champions=champions,
            seasons=self.seasons, cew=self.cew)

    def write_card_data(self):
        """
        Write a JSON file with card data for non-static parts of the site
        """
        mcardstats = { # 'Minified' card stats file
            c: {
                "a": cstat.num_appearances,
                "wr": cstat.winrate,
                "a60": cstat.hot_appearances,
                "wr60": (cstat.hot_rating if cstat.hot_appearances else -1),
                "price": pricedb.get_formatted_price(c),
                "mat": (1 if is_material(c) else 0),
                "rank": rank_card(carddata[c]),
                "img": carddata[c]["img"],
                "hipster": cstat.hipster
            }
            for c, cstat in ALL_CARD_STATS
        }
        self.render_json(mcardstats, "card/carddata.json")

    def write_card_page(self, cardname, cardstat, price="", events=[]):
        price = pricedb.get_formatted_price(cardname)
        sightings_json = self.format_sightings_json([p.deck for p in cardstat.appearances[:config.MAX_SIGHTINGS]])
        self.render("card.html.jinja2", f"card/{slugify(cardname)}.html", card=carddata[cardname], cardstat=cardstat, events=events, ERRATA=ERRATA, BANLIST=BANLIST, card_price=price, sightings_json=sightings_json)

    def write_decklist_tts(self, deck):
        if deck.is_topcut_deck:
            write_to = f"tts/event_{deck.entrant.evt_id}/{deck.entrant.id}_topcut.json"
        else:
            write_to = f"tts/event_{deck.entrant.evt_id}/{deck.entrant.id}.json"
        self.render_json(deck.tts_json(), write_to)

    def render_json(self, json_obj, write_to):
        """
        Write a JSON file to the output folder. Like render() but for JSON.
        Check if the file has same contents and don't overwrite if identical.
        """
        out_dir, out_file = os.path.split(write_to)
        whole_out_dir = os.path.join(config.OUTDIR, out_dir)
        makedirs(whole_out_dir, exist_ok=True)
        whole_out_file = os.path.join(whole_out_dir, out_file)

        # skip overwriting matching files
        try:
            json_string = json.dumps(json_obj)
            with open(whole_out_file, "r") as f:
                if json_string == f.read():
                    #print("Skipping unchanged file", whole_out_file)
                    return
        except FileNotFoundError:
            pass
        print("Writing to", whole_out_file)
        with open(whole_out_file, "w") as f:
            json.dump(json_obj, f)

    def write_achievement(self, achievement):
        write_to = f"achievement/{slugify(achievement.name)}.html"
        self.render("achievement.html.jinja2", write_to, achievement=achievement, astats=GAS[achievement.name])

    def write_achievements_index(self):
        self.render("achievements.html.jinja2", "achievement/index.html", GAS=GAS)

    def write_refracted_form(self):
        self.render("refracted-submissions.html.jinja2",
            "achievement/refracted-submissions.html",
            REFRACTED_ACHIEVEMENTS=REFRACTED_ACHIEVEMENTS
        )

    def write_refracted_about(self):
        self.render("refracted-about.html.jinja2",
            "achievement/refracted-about.html",
            REFRACTED_ACHIEVEMENTS=REFRACTED_ACHIEVEMENTS
        )

    def write_delta(self):
        self.render("delta.html.jinja2", "delta.html")

    def write_index(self):
        majors = [e for e in self.events.values()
                         if e.category['name'] in (
                            "Ascent",
                            "Nationals",
                            "Worlds",
                         )]
        majors.sort(key=lambda x:x.date, reverse=True)
        self.render("index.html.jinja2", "index.html", seasons=self.seasons, majors=majors)

    def write_decklist_jsons(self):
        """
        Write decklists in JSON format which are used not only for TTS export
        but also for dynamic loading in sightings on the site.
        """
        for e in self.events.values():
            for entrant in e.players:
                if entrant.deck:
                    self.write_decklist_tts(entrant.deck)
                if entrant.topcut_deck:
                    self.write_decklist_tts(entrant.topcut_deck)

    def read_event(self, id_s):
        """
        Instantiate a single event from an ID (int string) and add it to the
        relevant lists of events overall, by season, by format, and by player.
        """
        try:
            e = OmniEvent(id_s)
            self.events[e.id] = e
        except IsTeamEvent:
            e = Team3v3Event(id_s)
            self.events[e.id] = e
        if not self.seasons.get(e.season):
            self.seasons[e.season] = Season(e.season)
        self.seasons[e.season].add_event(e)

        for fmt in FORMATS:
            if fmt.should_include(e):
                fmt.add_event(e)
                break

        for entrant in e.players:
            if entrant.id in self.players.keys():
                self.players[entrant.id].add_entry(entrant)
            else:
                self.players[entrant.id] = Player(entrant)
        for judge in e.judges:
            self.known_judges[judge.id].append(judge)

    def read_events(self, force_evts=[]):
        """
        Read all events from disk and instantiate OmniEvents for each
        """
        evts_read = 0
        for entry in os.scandir("./data"):
            if config.SharedConfig.go_fast and evts_read >= FAST_CUTOFF:
                print("Skipping remaining events (fast mode)")
                if force_evts:
                    print("...but first, adding forced events")
                    for id_s in force_evts:
                        if id_s not in self.events.keys():
                            self.read_event(id_s)
                break
            if entry.is_dir() and entry.name[:6] == "event_":
                print("Reading event#",entry.name[6:])
                try:
                    self.read_event(entry.name[6:])
                except NotStarted:
                    print(f"Event #{entry.name[6:]} not started.")
                    continue
                evts_read += 1

    def consolidate_judges(self):
        """
        Add judges to player profiles where they exist
        """
        for jid, events_judged in self.known_judges.items():
            if jid in self.players.keys():
                events_judged.sort(key=lambda x:x.event.date)
                self.players[jid].events_judged = events_judged
            else:
                self.players[jid] = Player(events_judged[0])
                self.players[jid].events_judged = events_judged

    def analyze_hipsters(self):
        """
        Calculate hipster rating for each decklist and the hipster floor.
        """
        hdb = HipsterDB()
        lastdate = None
        evts_sorted = list(self.events.values())
        evts_sorted.sort(key=lambda e:e.start_time)
        for e in evts_sorted:
            if e.date != lastdate:
                cohort_floor = hdb.update_scores()
                if cohort_floor < self.hipster_floor:
                    self.hipster_floor = cohort_floor
                lastdate = e.date
            for p in e.players:
                if p.deck:
                    hdb.add_deck(p.deck)
                if p.topcut_deck:
                    hdb.add_deck(p.topcut_deck)
        cohort_floor = hdb.update_scores()
        if cohort_floor < self.hipster_floor:
            self.hipster_floor = cohort_floor
        ALL_CARD_STATS.update_hipster(hdb)
        self.hdb = hdb

    def organize_seasons(self):
        """
        Put seasons in the correct order and analyze them.
        """
        seasons_sorted = {k:self.seasons[v] for k,v in SEASONS.items() if v in self.seasons.keys()}
        unknown_seasons = [s.code for s in self.seasons.values() if s.code not in SEASONS.values()]
        if unknown_seasons:
            warning(f"Warning: unknown seasons: {unknown_seasons}")

        self.aew = {a:[] for a in ARCHETYPES.keys()} # archetype event wins
        self.aew[NO_ARCHETYPE.name] = []
        self.cew = {} # champ event wins
        self.seasons = seasons_sorted

        for season in self.seasons.values():
            season.analyze()
            subformats = [fmt for fmt in FORMATS if fmt.parent_season == season.code]
            for fmt in subformats:
                fmt.analyze()
            season.subformats = subformats

            # Analyze archetype & champ wins for this season
            for arche,wins in season.arche_wins.items():
                self.aew[arche] += wins
            for champ,wins in season.champ_wins.items():
                if champ in self.cew.keys():
                    self.cew[champ] += wins
                else:
                    self.cew[champ] = [w for w in wins]

    def analyze_players(self):
        for p in self.players.values():
            p.analyze_hipster(self.hipster_floor)
            p.analyze()
        GAS.total_players = len(self.players)

    def analyze_archetypes(self):
        for a in ARCHETYPES.values():
            if not a.matched_decks:
                continue
            a.analyze()
            a.load_videos()
        NO_ARCHETYPE.analyze()

    def analyze_champs(self):
        for champname, champstats in CHAMP_DATA.items():
            champstats.analyze()

    def load_all(self, force_evts=[]):
        """
        Read all input data and analyze it, making necessary connections between
        sub-systems.
        """
        self.read_events(force_evts=force_evts)
        self.consolidate_judges()
        self.organize_seasons()
        # Card stats has to come before player stuff for "first play" to work.
        ALL_CARD_STATS.analyze()
        self.analyze_hipsters()
        self.analyze_players()
        self.analyze_archetypes()
        self.analyze_champs()

    def write_all(self):
        """
        Write all parts of the site, including known event pages, homepage, season landings, player profiles, and the rest.
        """
        self.write_decklist_jsons()

        for season in self.seasons.values():
            self.write_season(season)
            self.write_subseasons(season)

        for p in self.players.values():
            self.write_player(p)
        self.write_player_index()

        for cardname, cardstat in ALL_CARD_STATS:
            self.write_card_page(cardname, cardstat, events=self.events)

        for a in ARCHETYPES.values():
            if not a.matched_decks:
                continue
            self.write_archetype(a)
        self.write_archetype(NO_ARCHETYPE)
        self.write_archetype_index()

        for e in self.events.values():
            self.write_event(e)

        self.write_card_index()
        self.write_card_data()

        for achievement in ACHIEVEMENTS.values():
            self.write_achievement(achievement)
        self.write_achievements_index()
        self.write_refracted_form()
        self.write_refracted_about()

        self.write_delta()

        for champname, champstats in CHAMP_DATA.items():
            if champstats.matched_decks:
                # skip champs with no appearances yet
                self.write_champ(champstats)
        self.write_champ_index()

        self.write_index()

def main(args):
    if args.fast:
        config.SharedConfig.go_fast = True
    force_evts = []
    for i in args.event_id:
        i_s = str(i)
        force_evts.append(i_s)
        get_event(i, force_redownload=args.update, save=True, dl_decklists=True)
    builder = PageBuilder(force_evts=force_evts)
    builder.write_all()
    if config.SharedConfig.go_fast != True:
        write_similarity_cache()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize an Omnidex event (works better if decklists are public)")
    parser.add_argument("event_id", type=int, help="Omnidex event ID to look up", nargs="*", default=None)
    parser.add_argument("-a", "--all", action="store_true", help="Rebuild all cached events")
    parser.add_argument("-u", "--update", action="store_true", help="Redownload the specified omnidex event")
    parser.add_argument("-f", "--fast", action="store_true", help="Skip deck similarity checks for a faster build")
    args = parser.parse_args()
    main(args)
