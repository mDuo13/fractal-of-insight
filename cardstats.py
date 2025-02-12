from collections import defaultdict

from datalayer import get_card_img
from shared import keydefaultdict
from shared import ElementStats, ChampStats

# Minimum number of appearances for a card to be eligible for "winningest" list
MIN_SIGHTINGS = 20

class CardStats:
    def __init__(self, cardname):
        self.name = cardname
        self.appearances = []
        self.num_appearances = 0
        self.wins = 0
        self.losses = 0
        self.ties = 0
        self.winrate = 0
    
    def add_entrant(self, e):
        self.appearances.append(e)
        self.num_appearances += 1
        self.wins += e.wins
        self.losses += e.losses
        self.ties += e.ties
    
    def analyze(self):
        self.appearances.sort(key=lambda e: e.evt_time*1000 + 9999-e.placement, reverse=True)
        if self.num_appearances:
            # TODO: handle ties for first user?
            self.first_user = self.appearances[-1]
        
        self.elements = ElementStats()
        self.champdata = ChampStats()
        
        for e in self.appearances:
            self.elements.add_deck(e.deck)
            self.champdata.add_deck(e.deck)
        
        matches = self.wins+self.losses+self.ties
        winscore = self.wins + (self.ties/2)
        if matches:
            self.winrate = round(100*winscore/matches, 1)
        
        self.analyze_associated_cards()
    
    def analyze_associated_cards(self):
        card_freq = defaultdict(int)
        for e in self.appearances:
            for cardname in e.deck:
                if cardname != self.name:
                    card_freq[cardname] += 1
        cf_sorted = list(card_freq.items())
        cf_sorted.sort(key=lambda x:x[1], reverse=True)
        self.related_cards = {
            c: {
                "card": c,
                "pct": round(100*f/self.num_appearances, 1),
                "img": get_card_img(c)
            } for c,f in cf_sorted
        }

class CardStatSet:
    def __init__(self):
        self.items = keydefaultdict(CardStats)
    
    def add_deck(self, d):
        for card in d: # Iterates material and main deck card names
            self.items[card].add_entrant(d.entrant)
        for card_o in d.dl["sideboard"]:
            if card_o["card"] not in d: # Don't double-add a deck if a card is in main+side
                self.items[card_o["card"]].add_entrant(d.entrant)

    def sort(self):
        newitems = keydefaultdict(CardStats)
        statdata = [(k,v) for k,v in self.items.items()]
        statdata.sort(key=lambda x:x[1].num_appearances, reverse=True)
        for k,v in statdata:
            newitems[k] = v
        self.items = newitems
        
        statdata.sort(key=lambda x:x[1].winrate, reverse=True)
        self.winningest = {k:v for k,v in statdata if v.num_appearances >= MIN_SIGHTINGS}

        statdata.sort(key=lambda x:x[0])
        self.alphabetical = {k:v for k,v in statdata}
    
    def __iter__(self):
        for cardname, cardstats in self.items.items():
            yield cardname, cardstats
    
    def __len__(self):
        return len(self.items)
    
    def __contains__(self, item):
        return (item in self.items)

ALL_CARD_STATS = CardStatSet()
