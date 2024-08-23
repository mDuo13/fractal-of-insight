from deck import Deck

from datalayer import get_deck, NoDeck
from cards import ELEMENTS

class Entrant:
    """
    Represents one player's entry into one event
    """
    def __init__(self, data, evt_id, evt_time=0):
        self.id = data["id"]
        self.evt_id = evt_id
        self.evt_time = evt_time
        self.wins = data["statsWins"]
        self.losses = data["statsLosses"]
        self.ties = data["statsTies"]
        self.byes = data["statsByes"]
        self.score = data["statsScore"]
        self.omw = data["statsPercentOMW"]
        self.gwp = data["statsPercentGW"]
        self.username = data["username"]
        self.elo = round(data["scoreElo"]) # seems this is the player's "current" elo at the time of looking up the event??
        self.elo_diff = 0 # modified when analyzing matchups
        self.rank_elo = data["rankElo"]

        self.record = f"{self.wins + self.byes}-{self.losses}-{self.ties}"

        # if data.get("isDecklistPublic"):
        try:
            is_public = data.get("isDecklistPublic")
            dl = get_deck(self.id, evt_id, is_public)
            self.deck = Deck(dl, evt_time)
        # else:
        except (NoDeck):
            self.deck = None
    
    def sortkey(self):
        return self.score + (self.omw/100) + (self.gwp / 100000)
    
    def __str__(self):
        return f'{self.username} #{self.id}'

class Player:
    """
    Represents a player across multiple events
    """
    def __init__(self, entrant):
        self.id = entrant.id
        self.username = entrant.username
        self.events = [entrant]
    
    def add_entry(self, entrant):
        self.events.append(entrant)
    
    def analyze(self):
        # To be called after all event entries have been added
        self.events.sort(key=lambda x: x.evt_time, reverse=True)
        self.num_decklists = len([e for e in self.events if e.deck])
        self.analyze_champions()
        
    def analyze_champions(self):
        champcount = {}
        champelcount = {}
        champelements = {}
        elcount = {el:0 for el in ELEMENTS}
        for e in self.events:
            if e.deck:
                el_frac = 1/len(e.deck.els)
                for el in e.deck.els:
                    elcount[el] += el_frac

                if not e.deck.lineages:
                    #print("Deck with no lineages??", e.evt_id, self.username, e.deck.lineages)
                    # Turns out this is a real thing that happens
                    # probably as a result of incorrect decklists.
                    continue
                c_frac = 1/len(e.deck.lineages)
                for c in e.deck.lineages:
                    if c in champcount.keys():
                        champcount[c] += c_frac
                        champelcount[c] += 1
                        for el in e.deck.els:
                            champelements[c][el] += el_frac
                    else:
                        champcount[c] = c_frac
                        champelcount[c] = 1
                        champelements[c] = {el: 0 for el in ELEMENTS}
                        for el in e.deck.els:
                            champelements[c][el] += el_frac
                
            # Note: not tracking cases w/ no decklist

        self.elements = []
        if self.num_decklists: # Skip if no deck data (avoid divby0)
            for el, elct in elcount.items():
                pct = round(100*elct/self.num_decklists)
                self.elements.append( (el, pct) )
        self.champdata = []
        for c,cc in champcount.items():
            pct = round(100*cc/self.num_decklists, 1)
            dec = champelcount[c]
            el_pcts = {el: round(100*ev/dec, 1) for el,ev in champelements[c].items()}
            self.champdata.append( (c, pct, el_pcts) )
        self.champdata.sort(key=lambda x:x[1], reverse=True)
        
        #TODO: implement more stuff like archetype analysis

    def mostplayed(self):
        if not self.champdata:
            return "?"
        top_champ = self.champdata[0]
        tied_champs = [crow[0] for crow in self.champdata if crow[1] == top_champ[1]]
        return "/".join(tied_champs)

    
    def sortkey(self):
        # Sort players by # of tracked events entered descending
        # then alphabetically by username (case-insensitive) ascending
        # Assumes no player will enter 10,000+ events
        return f"{10000-len(self.events):05d} {self.username.lower()}"
