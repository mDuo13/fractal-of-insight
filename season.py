from archetypes import ARCHETYPES
from cards import ELEMENTS
from competition import SEASONS

class Season:
    def __init__(self, season):
        self.code = season
        self.events = []

    def analyze_decks(self):
        szn_els = {el:0 for el in ELEMENTS}
        szn_arches = {a:0 for a in ARCHETYPES.keys()}
        szn_arche_els = {a: {el:0 for el in ELEMENTS} for a in ARCHETYPES.keys()}
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
        
        self.elements = []
        self.archedata = []
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

    def calc_headtohead(self, threshold=None):
        archetypes = ARCHETYPES.keys()
        bc = {a: {b:{"win":0,"draw":0,"matches":0} for b in archetypes} for a in archetypes}
        for e in self.events:
            for as_deck in e.battlechart.keys():
                for vs_deck, record in e.battlechart[as_deck].items():
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
        
        self.battlechart = bc
        print(bc)

    def __repr__(self):
        return f"{self.code} Season"
