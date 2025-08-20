#!/usr/bin/env python

import argparse
import json
import jinja2
from os import makedirs
import os.path
from math import ceil
from collections import defaultdict

import config
from datalayer import carddata, get_event, set_groups, get_card_img, get_card_price, format_price, write_similarity_cache
from shared import slugify, OVERALL, REGIONS
from omnievent import OmniEvent, Team3v3Event, IsTeamEvent, NotStarted
from season import Season, SEASONS, Format, FORMATS
from competition import EVENT_TYPES, TEAM_STANDARD
from player import Player
from archetypes import ARCHETYPES, NO_ARCHETYPE
from spoiler import SpoilerEvent, SPOILER_SEASONS
from cards import ERRATA, BANLIST
from cardstats import ALL_CARD_STATS, PAD_UNTIL
from achievements import ACHIEVEMENTS, GAS

SIGHTINGS_PER_PAGE = 200
CARD_SIGHTINGS_PER_PAGE = 100

class PageBuilder:
    def __init__(self):
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

    def write_archetype(self, archetype, players=[], events=[], seasons={}, wins=0):
        slug = slugify(archetype.name)
        arche_path = f"deck/{slug}.html"
        # The "Sightings" table is too much, so paginate it.
        max_page = ceil(len(archetype.matched_decks) / SIGHTINGS_PER_PAGE)
        self.render("archetype.html.jinja2", arche_path, arche=archetype, players=players, events=events, seasons=seasons, wins=wins,
                    page_number=1, page_start=0, page_end=SIGHTINGS_PER_PAGE, max_page=max_page)
        if max_page > 1:
            for i in range(1, max_page):
                page_number = i+1
                self.render("archetype-sightings-page.html.jinja2", f"deck/{slug}-{page_number}.html",
                            arche=archetype, players=players, events=events, seasons=seasons, wins=wins,
                            page_number=page_number, max_page=max_page, page_start=(i*SIGHTINGS_PER_PAGE), page_end=((i+1)*SIGHTINGS_PER_PAGE))

    def write_archetype_index(self, archetypes, aew, cswr):
        self.render("archetypes.html.jinja2", "deck/index.html", archetypes=archetypes, aew=aew, cswr=cswr)

    def write_card_index(self, card_stats_by_set):
        self.render("cards.html.jinja2", "card/index.html", cardstats=ALL_CARD_STATS, carddata=carddata, set_groups=set_groups, get_card_img=get_card_img, card_stats_by_set=card_stats_by_set, PAD_UNTIL=PAD_UNTIL)

    def write_card_page(self, cardname, cardstat, events=[]):
        max_page = ceil(len(cardstat.appearances) / CARD_SIGHTINGS_PER_PAGE)
        card_price = format_price(get_card_price(cardname))

        self.render("card.html.jinja2", f"card/{slugify(cardname)}.html", card=carddata[cardname], cardstat=cardstat, events=events, ERRATA=ERRATA, BANLIST=BANLIST, card_price=card_price, page_number=1, page_start=0, page_end=CARD_SIGHTINGS_PER_PAGE, max_page=max_page)

        # Actually printing all these sightings is like 4.5 gigs of data oops
        # if max_page > 1:
        #     for i in range(1, max_page):
        #         page_number = i+1
        #         self.render("card-sightings-page.html.jinja2", f"card/{slugify(cardname)}-{page_number}.html", card=carddata[cardname], cardstat=cardstat, events=events, page_number=page_number, page_start=(i*CARD_SIGHTINGS_PER_PAGE), page_end=((i+1)*CARD_SIGHTINGS_PER_PAGE), max_page=max_page)

    def write_decklist_tts(self, deck):
        if deck.is_topcut_deck:
            write_to = f"tts/event_{deck.entrant.evt_id}/{deck.entrant.id}_topcut.json"
        else:
            write_to = f"tts/event_{deck.entrant.evt_id}/{deck.entrant.id}.json"
        out_dir, out_file = os.path.split(write_to)
        whole_out_dir = os.path.join(config.OUTDIR, out_dir)
        makedirs(whole_out_dir, exist_ok=True)
        whole_out_file = os.path.join(whole_out_dir, out_file)

        # skip overwriting matching files
        try:
            json_string = json.dumps(deck.tts_json())
            with open(whole_out_file, "r") as f:
                if json_string == f.read():
                    #print("Skipping unchanged file", whole_out_file)
                    return
        except FileNotFoundError:
            pass
        print("Writing to", whole_out_file)
        with open(whole_out_file, "w") as f:
            json.dump(deck.tts_json(), f)

    def write_achievement(self, achievement):
        write_to = f"achievement/{slugify(achievement.name)}.html"
        self.render("achievement.html.jinja2", write_to, achievement=achievement, astats=GAS[achievement.name])

    def write_achievements_index(self):
        self.render("achievements.html.jinja2", "achievement/index.html", GAS=GAS)

    def write_spoilers(self, spoilers):
        self.render("spoilers.html.jinja2", "spoilers/index.html", spoilers=spoilers)

    def write_all(self):
        """
        Write all known event pages as well as homepage, season landings, and player profiles.
        """
        seasons = {}
        known_players = {}
        all_events = {}
        known_judges = defaultdict(list)
        for entry in os.scandir("./data"):
            if entry.is_dir() and entry.name[:6] == "event_":
                print("Reading event#",entry.name[6:])
                try:
                    e = OmniEvent(entry.name[6:])
                    all_events[e.id] = e
                except IsTeamEvent:
                    e = Team3v3Event(entry.name[6:])
                    all_events[e.id] = e
                except NotStarted:
                    print(f"Event #{entry.name[6:]} not started.")
                    pass
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

                    if entrant.deck:
                        self.write_decklist_tts(entrant.deck)
                    if entrant.topcut_deck:
                        self.write_decklist_tts(entrant.topcut_deck)
                for judge in e.judges:
                    known_judges[judge.id].append(judge)
        # Add judges to player profiles where they exist
        for jid, events_judged in known_judges.items():
            if jid in known_players.keys():
                events_judged.sort(key=lambda x:x.event.date)
                known_players[jid].events_judged = events_judged
            else:
                #print(f"Judge with no player instances? {judge}")
                pass

        seasons_sorted = {k:seasons[v] for k,v in SEASONS.items() if v in seasons.keys()}

        for szn in seasons.values():
            self.write_season(szn)

        formats_desc = list(reversed(FORMATS.values()))
        self.write_formats(formats_desc)

        # Card stats has to come before player stuff for "first play" to work.
        for cardname, cardstat in ALL_CARD_STATS:
            cardstat.analyze()
        ALL_CARD_STATS.sort()
        card_stats_by_set = ALL_CARD_STATS.split_by_set()

        HIPSTER_FLOOR = 99999
        for e in all_events.values():
            for p in e.players:
                if p.deck:
                    p.deck.rate_hipster(ALL_CARD_STATS)
                    if p.deck.hipster < HIPSTER_FLOOR:
                        HIPSTER_FLOOR = p.deck.hipster
                if p.topcut_deck:
                    p.topcut_deck.rate_hipster(ALL_CARD_STATS)
                    if p.topcut_deck.hipster < HIPSTER_FLOOR:
                        HIPSTER_FLOOR = p.topcut_deck.hipster

        for cardname, cardstat in ALL_CARD_STATS:
            self.write_card_page(cardname, cardstat, events=all_events)

        known_pids_sorted = [pid for pid, pl in known_players.items()]
        known_pids_sorted.sort(key=lambda x: known_players[x].sortkey())

        for pid in known_pids_sorted:
            known_players[pid].analyze_hipster(HIPSTER_FLOOR)

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
            # if a.shortname == "": # Quasi-sub archetypes like Fatestone
            #     continue
            if a.name not in aew.keys():
                aew[a.name] = []
            a.analyze()
            a.load_videos()
            self.write_archetype(a, known_players, all_events, seasons_sorted, aew[a.name])
        NO_ARCHETYPE.analyze()
        self.write_archetype(NO_ARCHETYPE, known_players, all_events, seasons_sorted, [])

        arches_sorted = [a for a in ARCHETYPES.values()]
        arches_sorted.sort(key=lambda x: len(x.matched_decks), reverse=True)
        current_season = list(seasons_sorted.values())[0]
        # Calculate "naive" win rate for current season, to match overall win rate.
        # This doesn't match Battlechart win rate because BC omits matches where one
        # deck is unknown, intentional draws, byes, etc.
        csa_wins = defaultdict(int) # current season archetype wins
        csa_losses = defaultdict(int)
        csa_ties = defaultdict(int)
        for s_e in current_season.events:
            for s_p in s_e.players:
                if s_p.deck:
                    for a in s_p.deck.archetypes:
                        csa_wins[a] += s_p.wins
                        csa_losses[a] += s_p.losses
                        csa_ties[a] += s_p.ties
        cswr = {}
        for a in csa_wins.keys():
            csa_matches = csa_wins[a]+csa_losses[a]+csa_ties[a]
            cswr[a] = round( 100*(csa_wins[a] + (csa_ties[a] / 2)) / csa_matches, 1)
        self.write_archetype_index(arches_sorted+[NO_ARCHETYPE], aew, cswr=cswr)

        for e in all_events.values():
            self.write_event(e)

        self.write_card_index(card_stats_by_set)

        GAS.total_players = len(known_players)
        for achievement in ACHIEVEMENTS.values():
            self.write_achievement(achievement)
        self.write_achievements_index()

        spoilers = {}
        for entry in os.scandir("./data/spoilers"):
            if entry.is_dir() and len(entry.name) == 3:
                szn = entry.name.lower()
                spoilers[szn] = SpoilerEvent(szn)
        self.write_spoilers(spoilers)

        self.render("index.html.jinja2", "index.html", seasons=seasons_sorted)

def main(args):

    if args.fast:
        config.SharedConfig.go_fast = True
    builder = PageBuilder()
    for i in args.event_id:
        i_s = str(i)
        get_event(i, force_redownload=args.update, save=True, dl_decklists=True)
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
