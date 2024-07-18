from time import strftime, gmtime

from player import Player
from datalayer import get_event
from archetypes import ARCHETYPES
from cards import ELEMENTS
from competition import SEASONS

def pct_with_archetype(players, arche):
    nom = 0
    for p in players:
        if p.deck and arche in p.deck.archetypes:
            nom += 1
    dec = nom / len(players)
    return round(dec*100, 1)

class OmniEvent:
    def __init__(self, evt_id):
        self.id = evt_id
        self.evt = get_event(self.id)
        self.name = self.evt["name"]
        self.date = strftime(r"%Y-%m-%d", gmtime(self.evt["startAt"]/1000))
        self.season = SEASONS.get(self.evt["season"]["name"], "OTHER")

        self.load_players() # populates self.players
        self.analyze_elements() # populates self.elements
        self.analyze_archetypes() # populates self.archedata
        self.battlechart = self.calc_headtohead()
    
    def load_players(self):
        self.players = []
        for pdata in self.evt["players"]:
            p = Player(pdata, self.id)
            self.players.append(p)
        self.players.sort(key=lambda x:x.sortkey(), reverse=True)
        self.pdict = {p.id: p for p in self.players}
    
    def analyze_elements(self):
        self.elements = []
        for el in ELEMENTS+["Norm"]:
            nom = 0
            for p in self.players:
                if p.deck and el in p.deck.els:
                    nom += 1
            dec = nom / len(self.players)
            pct = round(dec*100, 1)
            self.elements.append( (el, pct) ) 
    
    def analyze_archetypes(self):
        self.archedata = []
        for archetype in ARCHETYPES.keys():
            pct = pct_with_archetype(self.players, archetype)
            if pct > 0:
                # calculate element breakdown of archetype
                archetype_elements = {
                    e: 0 for e in ELEMENTS+["Norm"]
                }
                archetype_total = 0
                for p in self.players:
                    if p.deck and archetype in p.deck.archetypes:
                        el_quant = 1/len(p.deck.els)
                        for el in p.deck.els:
                            archetype_elements[el] += el_quant
                        archetype_total += 1
                el_pcts = {e: round(100*ev/archetype_total,1) for e,ev in archetype_elements.items()}
                self.archedata.append( (archetype, pct, el_pcts) )
        
        self.archedata.sort(key=lambda x:x[1], reverse=True)
    
    def calc_headtohead(self, threshold=None):
        use_archetypes = [a[0] for a in self.archedata]
        
        battlechart = {a: {b:{"win":0,"draw":0,"matches":0} for b in use_archetypes} for a in use_archetypes}
        
        for stage in self.evt["stages"]:
            #print(f"Stage {stage['id']} ({stage['type']})")
            for rnd in stage["rounds"]:
                #print(f"    Round {rnd['id']}")

                for match in rnd["matches"]:
                    if len(match["pairing"]) < 2:
                        #print("        And a bye")
                        continue

                    p1r = match["pairing"][0]
                    p2r = match["pairing"][1]

                    p1 = self.pdict[p1r["id"]]
                    p2 = self.pdict[p2r["id"]]

                    # Update player Elo changes
                    p1.elo_diff += match["pairing"][0]["eloChange"]
                    p2.elo_diff += match["pairing"][1]["eloChange"]

                    if p1r["score"] == p2r["score"] and p1r["score"] == 0:
                        #print(f"        intentional draw")
                        continue
                    elif not p1.deck or not p2.deck:
                        #print("        (decklist unavailable)")
                        continue
                    
                    if threshold:
                        if p1.rank_elo > threshold or p2.rank_elo > threshold:
                            # Match below ranking threshold; don't count it
                            continue
                        else:
                            print("This is a match between two top-{threshold} players")
                    
                    if p1r["score"] > p2r["score"]:
                        outcome = "beats"
                        for as_t in p1.deck.archetypes:
                            for vs_t in p2.deck.archetypes:
                                battlechart[as_t][vs_t]["win"] += 1
                                battlechart[as_t][vs_t]["matches"] += 1
                                battlechart[vs_t][as_t]["matches"] += 1

                    elif p1r["score"] < p2r["score"]:
                        outcome = "loses to"
                        for as_t in p1.deck.archetypes:
                            for vs_t in p2.deck.archetypes:
                                battlechart[vs_t][as_t]["win"] += 1
                                battlechart[as_t][vs_t]["matches"] += 1
                                battlechart[vs_t][as_t]["matches"] += 1

                    else:
                        outcome = "ties"
                        for as_t in p1.deck.archetypes:
                            for vs_t in p2.deck.archetypes:
                                battlechart[as_t][vs_t]["draw"] += 1
                                battlechart[vs_t][as_t]["draw"] += 1
                                battlechart[as_t][vs_t]["matches"] += 1
                                battlechart[vs_t][as_t]["matches"] += 1

                    #print(f"        {p1.deck} {outcome} {p2.deck}")
        
        # Calculate win% and favored/unfavored status
        for as_type, records in battlechart.items():
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
        
        return battlechart