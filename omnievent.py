from time import strftime, gmtime

from player import Entrant
from datalayer import get_event
from archetypes import ARCHETYPES
from cards import ELEMENTS
from competition import SEASONS, EVENT_TYPES
from config import TOP_CUTOFF

def pct_with_archetype(players, arche):
    nom = 0
    for p in players:
        if p.deck and arche in p.deck.archetypes:
            nom += 1
    dec = nom / len(players)
    return round(dec*100, 1)

class OmniEvent:
    def __init__(self, evt_id, force_redownload=False):
        self.id = evt_id
        self.evt = get_event(self.id, force_redownload)
        self.name = self.evt["name"]
        self.date = strftime(r"%Y-%m-%d", gmtime(self.evt["startAt"]/1000))
        self.season = SEASONS.get(self.evt["season"]["name"], "OTHER")
        self.category = EVENT_TYPES.get(self.evt["category"], {"name": "Unknown"})
        self.country = self.evt.get("addressCountryCode", "")

        if self.evt["format"] == "team-standard-3v3":
            raise NotImplementedError

        self.load_players() # populates self.players, self.num_decklists, self.decklist_status
        self.analyze_elements() # populates self.elements
        self.analyze_archetypes() # populates self.archedata
        self.champdata = self.analyze_champions()
        self.battlechart = self.calc_headtohead(track_elo=True)
        self.bc_top = self.calc_headtohead(TOP_CUTOFF)
        self.parse_top_cut() # populates self.top_cut
    
    def load_players(self):
        self.num_decklists = 0
        self.players = []
        for pdata in self.evt["players"]:
            p = Entrant(pdata, self.id, evt_time=self.evt["startAt"])
            self.players.append(p)
            if p.deck:
                self.num_decklists += 1
        self.players.sort(key=lambda x:x.sortkey(), reverse=True)
        self.pdict = {p.id: p for p in self.players}
        if self.num_decklists == len(self.players):
            self.decklist_status = "full"
        elif self.num_decklists == 0:
            self.decklist_status = "none"
        else:
            self.decklist_status = "partial"
    
    def analyze_elements(self):
        self.elements = []
        for el in ELEMENTS:
            nom = 0
            for p in self.players:
                if p.deck and el in p.deck.els:
                    nom += 1
            dec = nom / len(self.players)
            pct = round(dec*100, 1)
            self.elements.append( (el, pct) ) 
        if self.decklist_status == "partial":
            nom = len(self.players) - self.num_decklists
            dec = nom / len(self.players)
            pct = round(dec*100, 1)
            self.elements.append( ("Unknown", pct) )
    
    def analyze_archetypes(self):
        self.archedata = []
        for archetype in ARCHETYPES.keys():
            pct = pct_with_archetype(self.players, archetype)
            if pct > 0:
                # calculate element breakdown of archetype
                archetype_elements = {
                    e: 0 for e in ELEMENTS
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
    
    def analyze_champions(self):
        champcount = {}
        champelcount = {}
        champelements = {}
        for p in self.players:
            if p.deck:
                for c in p.deck.lineages:
                    if c in champcount.keys():
                        champcount[c] += 1/len(p.deck.lineages)
                        champelcount[c] += 1
                        for el in p.deck.els:
                            champelements[c][el] += 1/len(p.deck.els)
                    else:
                        champcount[c] = 1/len(p.deck.lineages)
                        champelcount[c] = 1
                        champelements[c] = {e: 0 for e in ELEMENTS}
                        for el in p.deck.els:
                            champelements[c][el] += 1/len(p.deck.els)    
            else:
                if "Unknown" in champcount:
                    champcount["Unknown"] += 1
                    champelcount["Unknown"] += 1
                else:
                    champcount["Unknown"] = 1
                    champelcount["Unknown"] = 1
                    champelements["Unknown"] = {e: 0 for e in ELEMENTS}

        champdata = []
        for c,cc in champcount.items():
            pct = round(100*cc/len(self.players), 1)
            dec = champelcount[c]
            el_pcts = {e: round(100*ev/dec, 1) for e,ev in champelements[c].items()}
            champdata.append( (c, pct, el_pcts) )
        champdata.sort(key=lambda x:x[1], reverse=True)

        return champdata

    def parse_top_cut(self):
        self.top_cut = []
        try:
            cutsize = int(self.evt.get("cutSize", "0"))
        except ValueError:
            print("Unknown cutSize value:", self.evt.get("cutSize"))
            cutsize = 0
        if not cutsize:
            return
        
        finalstage = self.evt["stages"][-1]
        if finalstage["type"] != "single-elimination":
            print("Final stage isn't single elim??", finalstage)
            return
        
        for rnd in finalstage["rounds"]:
            if rnd == finalstage["rounds"][-1]:
                # Final stage of single elim needs special treatment
                tier = []
                matches = rnd["matches"]
                if len(matches) > 1:
                    if len(matches) > 2:
                        print("WARNING: 3+ matches in final stage of single-elim?")
                    
                    bronze_contenders = [p.id for p in self.top_cut[-2:]]

                    if matches[0]["pairing"][0]["id"] in bronze_contenders:
                        bronze_match = matches[0]
                        finals_match = matches[1]
                    else:
                        bronze_match = matches[1]
                        finals_match = matches[0]

                else:
                    bronze_match = None
                    finals_match = matches[0]
                
                if bronze_match:
                    if bronze_match["pairing"][0]["status"] == "loser":
                        place4_id = bronze_match["pairing"][0]["id"]
                        place3_id = bronze_match["pairing"][1]["id"]
                    else:
                        place3_id = bronze_match["pairing"][0]["id"]
                        place4_id = bronze_match["pairing"][1]["id"]
                    tier.append(self.pdict[place4_id])
                    tier.append(self.pdict[place3_id])
                    # Remove 3rd/4th from top cut list so we can re-add them in
                    # the correct order below
                    self.top_cut = self.top_cut[:-2]
                
                if finals_match["pairing"][0]["status"] == "loser":
                    place2_id = finals_match["pairing"][0]["id"]
                    place1_id = finals_match["pairing"][1]["id"]
                else:
                    place1_id = finals_match["pairing"][0]["id"]
                    place2_id = finals_match["pairing"][1]["id"]
                tier.append(self.pdict[place2_id])
                tier.append(self.pdict[place1_id])
            
            else:
                tier = []
                for match in rnd["matches"]:
                    if match["pairing"][0]["status"] == "loser":
                        loser_id = match["pairing"][0]["id"]
                        tier.append(self.pdict[loser_id])
                    elif match["pairing"][1]["status"] == "loser":
                        loser_id = match["pairing"][1]["id"]
                        tier.append(self.pdict[loser_id])
                    else:
                        print("No loser in single-elim match?", match)
                tier.sort(key=lambda x:x.sortkey())

            self.top_cut += tier
            
        self.top_cut.reverse()
    
    def calc_headtohead(self, threshold=None, track_elo=False):
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

                    if match["status"] == "started":
                        #print("         Match ongoing")
                        continue

                    p1r = match["pairing"][0]
                    p2r = match["pairing"][1]

                    p1 = self.pdict[p1r["id"]]
                    p2 = self.pdict[p2r["id"]]

                    if track_elo:
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
                            #print(f"This is a match between two top-{threshold} players")
                            pass
                    
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

    def __repr__(self):
        return f"Event#{self.id}"
