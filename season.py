from time import strftime, gmtime

from archetypes import ARCHETYPES
from cards import ELEMENTS, LINEAGES
from competition import SEASONS
from shared import ElementStats, ArcheStats, ChampStats

class Season:
    def __init__(self, season):
        self.code = season
        self.events = []
        self.data = {}

    def add_event(self, e):
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
                self.start_time = strftime(r"%Y-%m-%d", gmtime(data["startsAt"]/1000))
                self.end_time = strftime(r"%Y-%m-%d", gmtime(data["endsAt"]/1000))
                self.season_guide = data["file"]

    def analyze(self):
        # Call after all events have been added & analyzed
        self.events.sort(key=lambda x:x.date, reverse=True)
        self.analyze_decks()
        self.battlechart = self.calc_headtohead()
        self.bc_top = self.calc_headtohead(True)
        self.analyze_finishes()
        self.analyze_draws()

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
        archetypes = [a[0] for a in self.archedata]
        bc = {a: {b:{"win":0,"draw":0,"matches":0} for b in archetypes} for a in archetypes}
        for e in self.events:
            if use_top:
                event_bc = e.bc_top
            else:
                event_bc = e.battlechart

            for as_deck in event_bc.keys():
                for vs_deck, record in event_bc[as_deck].items():
                    bc[as_deck][vs_deck]["win"] += record["win"]
                    bc[as_deck][vs_deck]["draw"] += record["draw"]
                    bc[as_deck][vs_deck]["matches"] += record["matches"]
        
        # Calculate win% and favored/unfavored status
        for as_type, records in bc.items():
            for opp, r in records.items():
                if r["matches"] > 0:
                    pct = round(100 * (r["win"] + (r["draw"] / 2)) / r["matches"], 1)
                    
                    if pct > 60:
                        rating = "favored"
                    elif pct < 40:
                        rating = "unfavored"
                    else:
                        rating = "even"
                    r["rating"] = rating
                    r["pct"] = pct
                else:
                    r["rating"] = "no_data"
        
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
