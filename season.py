from collections import defaultdict

from shared import ElementStats, ArcheStats, ChampStats, OVERALL, date_to_ms, ms_to_date
from battlechart import BattleChart

class Season:
    def __init__(self, season):
        self.code = season
        self.events = []
        self.data = {}
        self.pdict = defaultdict(list) # list of events entered by player ID

    def add_event(self, e):
        if e in self.events:
            raise ValueError(f"Duplicate event: {e}")
        self.events.append(e)

        if not self.data:
            if self.code == "OFF":
                self.name = "Offseason"
                self.id = 0
                self.start_time = "N/A"
                self.end_time = "N/A"
                self.season_guide = None
            else:
                # There's no good API method to look up season data,
                # but we can save it from the first event to get added
                data = e.evt["season"]
                self.name = data["name"]
                self.id = data["id"]
                self.start_time = ms_to_date(data["startsAt"])
                self.end_time = ms_to_date(data["endsAt"])
                self.season_guide = data["file"]

    def analyze(self):
        # Call after all events have been added & analyzed
        self.events.sort(key=lambda x:x.date, reverse=True)
        self.analyze_players()
        self.analyze_decks()
        self.battlechart = self.calc_headtohead()
        self.bc_top = self.calc_headtohead(True)
        self.analyze_finishes()
        self.analyze_draws()

    def analyze_players(self):
        for e in self.events:
            for p in e.players:
                self.pdict[p.id].append(p)
        self.total_players = len(self.pdict.keys())

    def analyze_decks(self):
        self.elements = ElementStats()
        self.archedata = ArcheStats()
        self.champdata = ChampStats()
        self.decks = 0
        for e in self.events:
            for p in e.players:
                if p.deck:
                    self.decks += 1
                    self.elements.add_deck(p.deck)
                    self.archedata.add_deck(p.deck)
                    self.champdata.add_deck(p.deck)

    def calc_headtohead(self, use_top=False):
        if use_top:
            bc_list = [e.bc_top for e in self.events]
        else:
            bc_list = [e.battlechart for e in self.events]
        bc = BattleChart.from_merge(bc_list)
        return bc

    def analyze_finishes(self):
        self.arche_wins = {}
        for e in self.events:
            if e.winner and e.winner.deck:
                for arche in e.winner.deck.archetypes:
                    if arche in self.arche_wins.keys():
                        self.arche_wins[arche].append(e)
                    else:
                        self.arche_wins[arche] = [e]

    def analyze_draws(self):
        if not self.events:
            return
        total_matches = 0
        draws = 0
        nat_draws = 0
        for e in self.events:
            total_matches += e.total_matches
            draws += e.draws
            nat_draws += e.nat_draws
        self.draws = draws
        self.nat_draws = nat_draws
        self.draw_pct = round(100*draws/total_matches, 1)
        self.nat_draw_pct = round(100*nat_draws/total_matches, 1)

    def __repr__(self):
        if self.name == "Offseason":
            return "Offseason"
        return f"{self.code} Season"

class Format(Season):
    def __init__(self, name, start, end=None, desc=""):
        self.name = name
        self.start_time = start
        self.end_time = end
        self.season_guide = None
        self.desc = desc
        self.events = []
        self.data = None
        self.pdict = defaultdict(list)

    def add_event(self, e):
        self.events.append(e)

    def should_include(self, evt):
        """
        Returns True if evt occurs during this format's timeframe.
        """
        if evt.evt["format"] != "standard":
            # Omit Team Standard from stats because it's weird.
            return False

        fmt_start = date_to_ms(self.start_time, weebs_time=True)
        if self.end_time:
            fmt_end = date_to_ms(self.end_time, weebs_time=True)

        evt_start = evt.evt["startAt"]
        if fmt_start <= evt_start and (not self.end_time or evt_start < fmt_end):
            return True
        return False

    def __repr__(self):
        return self.name


SEASONS = {
    "Distorted Reflections": "DTR",
    "Abyssal Heaven": "HVN",
    "Mortal Ambition": "AMB",
    "Mercurial Heart": "MRC",
    "Alchemical Revolution": "ALC",
    "Offseason": "OFF",
}

FORMATS = {}
def add_format(*args,**kwargs):
    f = Format(*args, **kwargs)
    FORMATS[f.name] = f

add_format("ALC Release",
    start="2024-02-04",
    end="2024-02-16",
    desc="Start of Omnidex and Alchemical Revolution season."
)
add_format("ALC Post-Ontario",
    start="2024-02-16",
    end="2024-05-17",
    desc="Crystal of Empowerment banned."
)
# Technically the 2024 April Fools champions were legal for one day, but I don't care.
add_format("MRC Release",
    start="2024-05-17",
    end="2024-08-05",
    desc="Mercurial Heart released alongside Silvie, Slime Sovereign and Tristan, Shadowdancer Re:Collection decks."
)
add_format("MRC Post-Chicago",
    start="2024-08-05",
    end="2024-09-02",
    desc="Stonescale Band received errata."
)
add_format("MRC Post-Outlook",
    start="2024-09-02",
    end="2024-10-11",
    desc="Corhazi Outlook banned; Polaris, Twinkling Cauldron added to Proxia's Vault."
)
add_format("AMB Release",
    start="2024-10-11",
    end="2024-10-28",
    desc="Mortal Ambition released; Erupting Rhapsody banned."
)
add_format("AMB Post-Toronto",
    start="2024-10-28",
    end="2025-01-10",
    desc="Three Visits received errata; Nullifying Mirror added to Proxia's Vault."
)
add_format("AMB + ALC Alter",
    start="2025-01-10",
    end="2025-02-10",
    desc="Alchemical Revolution Alter released."
)
add_format("AMB + Reciprocity",
    start="2025-02-10",
    end="2025-02-17",
    desc="Reciprocity, Dorumegia's Call added to Proxia's Vault"
)
add_format("AMB Post-Feb Bans",
    start="2025-02-17",
    end="2025-03-07",
    desc="Icebound Slam and Baby Gray Slime banned."
)
add_format("HVN Release",
    start="2025-03-07",
    end="2025-04-28",
    desc="Abyssal Heaven released; Scepter of Lumina received errata."
)
add_format("HVN + Clarent",
    start="2025-04-28",
    end="2025-05-31",
    desc="Clarent, Reimagined added to Proxia's Vault."
)
add_format("HVN + MRC Alter",
    start="2025-05-31",
    end="2025-06-02",
    desc="Mercurial Heart Alter Edition released."
)
add_format("HVN Post-June Ban",
    start="2025-06-02",
    end="2025-07-25",
    desc="Dissonant Fractal banned."
)
add_format("DTR Release",
    start="2025-07-25",
    end="2025-08-25",
    desc="Distorted Reflections released; Lost in Thought banned; Polaris, Twinkling Cauldron received errata."
)
add_format("DTR + Thurible",
    start="2025-08-25",
    desc="Purifying Thurible added to Proxia's Vault"
)
