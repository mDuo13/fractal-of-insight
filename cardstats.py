from collections import defaultdict
from time import time

from datalayer import carddata, get_card_img
from shared import keydefaultdict
from shared import ElementStats, ChampStats, ArcheStats

# Minimum number of appearances for a card to be eligible for "winningest" list
#MIN_SIGHTINGS = 20
MIN_SIGHTINGS = 1 # temp: trying disabled since the weighting should handle this
PAD_UNTIL = 500
M_PER_APP = 6 # Empirically, an average "appearance" consists of ~5.9 matches.

HOT_CARDS_WINDOW = 60*60*24*61 # last ~60 days in seconds
PAD_HOT_MATCHES = 500 # for hot cards, weight for this many *matches* (not appearances)

class TopCutAppearance:
    # A shim for an "Entrant" but using only the different deck they played
    # in the single-elim top cut of a Worlds event.
    def __init__(self, e):
        self.entrant = e
        self.calc_topcut_record()
    
    def __getattr__(self, attr):
        if attr == "deck":
            return self.entrant.topcut_deck
        return getattr(self.entrant, attr)
    
    def calc_topcut_record(self):
        self.wins = 0
        self.losses = 0
        self.ties = 0
        topcut_stage = self.event.evt["stages"][-1]
        for rnd in topcut_stage["rounds"]:
            for match in rnd["matches"]:
                if len(match["pairing"]) < 2:
                    # Maybe record the bye in stats? Meh
                    continue

                p1r = match["pairing"][0]
                p2r = match["pairing"][1]
                if self.entrant.id not in (p1r["id"], p2r["id"]):
                    # Someone else's match. Ignore.
                    continue
                if p1r["score"] == p2r["score"] and p1r["score"] == 0:
                    # Intentional draw
                    self.ties += 1
                elif p1r["id"] == self.entrant.id:
                    if p1r["status"] == "winner":
                        self.wins += 1
                    elif p1r["status"] == "loser":
                        self.losses += 1
                    elif p1r["status"] == "tied":
                        self.ties += 1
                elif p2r["id"] == self.entrant.id:
                    if p2r["status"] == "winner":
                        self.wins += 1
                    elif p2r["status"] == "loser":
                        self.losses += 1
                    elif p2r["status"] == "tied":
                        self.ties += 1



class CardStats:
    def __init__(self, cardname):
        self.name = cardname
        self.appearances = []
        self.num_appearances = 0
        self.wins = 0
        self.losses = 0
        self.ties = 0
        self.winrate = 0
        self.hipster = 0 # %ile rating of how uncommonly played the card is.
                         # Populated by CardStatSet.sort()
    
    def add_entrant(self, e, is_topcut_deck=False):
        if is_topcut_deck:
            e = TopCutAppearance(e)
        self.appearances.append(e)
        self.num_appearances += 1
        self.wins += e.wins
        self.losses += e.losses
        self.ties += e.ties
    
    def analyze(self):
        self.appearances.sort(key=lambda e: e.evt_time*1000 + 9999-e.placement, reverse=True)
        if self.num_appearances:
            self.first_users = [self.appearances[-1]]
            self.appearances[-1].first_plays.append(self.name)
            i = 2
            first_date = self.appearances[-1].event.date
            while i <= len(self.appearances):
                u = self.appearances[-i]
                if u.event.date == first_date:
                    self.first_users.append(u)
                    u.first_plays.append(self.name)
                i+= 1
        
        self.elements = ElementStats()
        self.champdata = ChampStats()
        self.archedata = ArcheStats()
        
        for e in self.appearances:
            self.elements.add_deck(e.deck)
            self.champdata.add_deck(e.deck)
            self.archedata.add_deck(e.deck)
        
        matches = self.wins+self.losses+self.ties
        winscore = self.wins + (self.ties/2)
        if matches:
            self.winrate = round(100*winscore/matches, 1)

        ## Weighted match score. Assuming PAD_UNTIL appearances is enough data
        ## an expected win rate is 50%, and an appearance involves M_PER_APP
        ## matches on average, pad results with draws (half-wins) if data is
        ## under PAD_UNTIL appearances.
        if self.num_appearances >= PAD_UNTIL:
            self.weighted_winrate = self.winrate
        elif self.num_appearances:
            pad_amount = M_PER_APP * (PAD_UNTIL - self.num_appearances)
            winscore_padded = winscore + (pad_amount / 2)
            self.weighted_winrate = round(100*winscore_padded/(matches+pad_amount), 1)

        ## Hot cards: only count wins in the past ~60 days.
        cutoff_time_ms = (int(time()) - HOT_CARDS_WINDOW) * 1000
        hot_events = [e for e in self.appearances if e.evt_time > cutoff_time_ms]
        if not hot_events:
            self.hot_rating = 0
        else:
            hot_w = 0
            hot_l = 0
            hot_t = 0
            for e in hot_events:
                hot_w += e.wins
                hot_l += e.losses
                hot_t += e.ties
            hot_matches = hot_w + hot_l + hot_t
            if hot_matches < PAD_HOT_MATCHES:
                hot_t += (PAD_HOT_MATCHES - hot_matches)
                hot_matches = PAD_HOT_MATCHES
            self.hot_rating = round(100*(hot_w + (hot_t / 2)) / hot_matches, 1)
        
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
        if d.invalid_decklist:
            # Don't pollute stats with invalid decklists.
            # Also, don't award "first play" for that.
            return

        for card in d: # Iterates material and main deck card names
            if "TOKEN" in carddata[card]["types"]:
                # Some decklists mistakenly include tokens. Skip those.
                continue
            self.items[card].add_entrant(d.entrant, is_topcut_deck=d.is_topcut_deck)
        for card_o in d.side:
            if "TOKEN" in carddata[card_o["card"]]["types"]:
                # Skip tokens again
                continue
            if card_o["card"] not in d: # Don't double-add a deck if a card is in main+side
                self.items[card_o["card"]].add_entrant(d.entrant, is_topcut_deck=d.is_topcut_deck)

    def sort(self):
        mostappearances = keydefaultdict(CardStats)
        statdata = [(k,v) for k,v in self.items.items()]
        statdata.sort(key=lambda x:x[1].num_appearances, reverse=True)
        for i, (k,v) in enumerate(statdata):
            v.hipster = round(100 * i / len(statdata), 1)
            mostappearances[k] = v
        self.items = mostappearances
        
        #statdata.sort(key=lambda x:x[1].winrate, reverse=True)
        statdata.sort(key=lambda x:x[1].weighted_winrate, reverse=True)
        self.winningest = {k:v for k,v in statdata if v.num_appearances >= MIN_SIGHTINGS}

        statdata.sort(key=lambda x:x[1].hot_rating, reverse=True)
        self.hottest = {k:v for k,v in statdata if v.hot_rating > 0}

        statdata.sort(key=lambda x:x[0])
        self.alphabetical = {k:v for k,v in statdata}

    def split_by_set(self):
        setstats = {}
        for k,v in self.items.items():
            card = carddata[v.name]
            prefix = card["set_introduced"]
            if prefix not in setstats.keys():
                setstats[prefix] = CardStatSet()
            setstats[prefix].items[k] = v
        for ss in setstats.values():
            ss.sort()
        return setstats
    
    def __getitem__(self, item):
        return self.items[item]
    
    def __iter__(self):
        for cardname, cardstats in self.items.items():
            yield cardname, cardstats
    
    def __len__(self):
        return len(self.items)
    
    def __contains__(self, item):
        return (item in self.items)

ALL_CARD_STATS = CardStatSet()
