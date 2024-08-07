from time import strftime, gmtime

from archetypes import ARCHETYPES
from cards import ELEMENTS, LINEAGES
from competition import SEASONS

class Season:
    def __init__(self, season):
        self.code = season
        self.events = []
        self.data = {}

    def add_event(self, e):
        self.events.append(e)
        if not self.data:
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

    def analyze_decks(self):
        szn_els = {el:0 for el in ELEMENTS}
        szn_arches = {a:0 for a in ARCHETYPES.keys()}
        szn_arche_els = {a: {el:0 for el in ELEMENTS} for a in ARCHETYPES.keys()}
        szn_champs = {c:0 for c in LINEAGES}
        szn_champ_els = {c: {el:0 for el in ELEMENTS} for c in LINEAGES}
        self.decks = 0
        for e in self.events:
            for p in e.players:
                if p.deck:
                    self.decks += 1
                    el_frac =  1/len(p.deck.els)
                    for el in p.deck.els:
                        szn_els[el] += el_frac
                    for arche in p.deck.archetypes:
                        szn_arches[arche] += 1
                        for el in p.deck.els:
                            szn_arche_els[arche][el] += el_frac
                    for c in p.deck.lineages:
                        szn_champs[c] += 1/len(p.deck.lineages)
                        for el in p.deck.els:
                            szn_champ_els[c][el] += el_frac/len(p.deck.lineages)
        
        self.elements = []
        self.archedata = []
        self.champdata = []
        if not self.decks:
            return
        for el, total in szn_els.items():
            dec = szn_els[el] / self.decks
            pct = round(dec*100, 1)
            self.elements.append( (el, pct) )
        
        for a in ARCHETYPES.keys():
            a_decks = szn_arches[a]
            a_pct = round(100*a_decks / self.decks, 1)
            a_els = szn_arche_els[a]
            if a_decks > 0:
                el_pcts = {el: round(100*ev/a_decks, 1) for el,ev in a_els.items() }
            else:
                el_pcts = {el: 0 for el in ELEMENTS}
            self.archedata.append( (a, a_pct, el_pcts) )
        self.archedata.sort(key=lambda x:x[1], reverse=True)

        for c in LINEAGES:
            c_decks = szn_champs[c]
            c_pct = round(100*c_decks / self.decks, 1)
            c_els = szn_champ_els[c]
            if c_decks > 0:
                el_pcts = {el: round(100*ev/c_decks, 1) for el,ev in c_els.items() }
            else:
                el_pcts = {el: 0 for el in ELEMENTS}
            self.champdata.append( (c, c_pct, el_pcts) )
        self.champdata.sort(key=lambda x:x[1], reverse=True)

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

    def __repr__(self):
        return f"{self.code} Season"
