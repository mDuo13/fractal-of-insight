from deck import Deck

from datalayer import get_deck, NoDeck
from cards import ELEMENTS
from shared import keydefaultdict, ElementStats, ChampStats, ArcheStats
RIVAL_THRESHOLD = 3 # min matches to count as a rival
RIVAL_MAXCOUNT = 5 # trim rivals list if it's over this size

class Entrant:
    """
    Represents one player's entry into one event
    """
    def __init__(self, data, evt_id, season, evt_time=0):
        self.id = data["id"]
        self.evt_id = evt_id
        self.season = season
        self.evt_time = evt_time
        self.wins = data["statsWins"]
        self.losses = data["statsLosses"]
        self.ties = data["statsTies"]
        self.byes = data["statsByes"]
        self.score = data["statsScore"]
        self.omw = data["statsPercentOMW"]
        self.gwp = data["statsPercentGW"]
        self.ogw = data["statsPercentOGW"]
        self.username = data["username"]
        self.elo = round(data["scoreElo"]) # seems this is the player's "current" elo at the time of looking up the event??
        self.elo_diff = 0 # modified when analyzing matchups
        self.rank_elo = data["rankElo"]
        self.region = data.get("addressCountryCode")
        if "team" in data:
            self.team = data["team"]
            self.seat = data["teamSlot"]

        # At some point Omnidex changed from the "wins" number being inclusive of byes
        # to it not being.
        if self.evt_time >= 1715340600001 or evt_id == "1687":
            self.record = f"{self.wins + self.byes}-{self.losses}-{self.ties}"
            if 3*(self.wins + self.byes) + self.ties > self.score:
                print(f"event {evt_id}: byes counted in wins when not expected")
                exit(1)
        else:
            self.record = f"{self.wins}-{self.losses}-{self.ties}"
            if 3*(self.wins + self.byes) + self.ties <= self.score and self.byes > 0:
                print(f"event {evt_id}: byes NOT counted in wins when expected")
                exit(1)
            

        # if data.get("isDecklistPublic"):
        try:
            is_public = data.get("isDecklistPublic")
            dl = get_deck(self.id, evt_id, is_public)
            self.deck = Deck(dl, self)
        # else:
        except (NoDeck):
            self.deck = None
    
    def sortkey(self):
        return self.score + (self.omw/100) + (self.gwp / 100000) + (self.ogw / 10000000)
    
    def __str__(self):
        return f'{self.username} #{self.id}'

class Rivalry:
    def __init__(self, opp_id):
        self.opp_id = opp_id
        self.wins = 0
        self.losses = 0
        self.draws = 0
    
    @property
    def matches(self):
        return self.wins+self.losses+self.draws
    
    @property
    def pct(self):
        if self.matches == 0:
            return "?"
        return round(100 * (self.wins + (self.draws / 2)) / self.matches, 1)

class Player:
    """
    Represents a player across multiple events
    """
    def __init__(self, entrant):
        self.id = entrant.id
        self.username = entrant.username
        self.events = [entrant]
        self.rivalries=keydefaultdict(Rivalry)
        self.region = entrant.region
    
    def add_entry(self, entrant):
        self.events.append(entrant)
    
    def analyze(self):
        # To be called after all event entries have been added
        self.events.sort(key=lambda x: x.evt_time, reverse=True)
        self.num_decklists = len([e for e in self.events if e.deck])
        self.analyze_champions()
        self.analyze_rivals()
        
    def analyze_champions(self):
        self.elements = ElementStats()
        self.champdata = ChampStats()
        self.archedata = ArcheStats()

        for e in self.events:
            if e.deck:
                self.elements.add_deck(e.deck)
                self.champdata.add_deck(e.deck)
                self.archedata.add_deck(e.deck)
            else:
                self.elements.add_unknown()

    def track_rivals_for_event(self, e):
        for stage in e.evt["stages"]:
            for rnd in stage["rounds"]:
                for match in rnd["matches"]:
                    for mpl in match["pairing"]:
                        if mpl["id"] == self.id:
                            if str(self.id) not in rnd["pairings"].keys():
                                # This happens for byes
                                continue
                            oppid = rnd["pairings"][str(self.id)]

                            if mpl["status"] == "loser":
                                self.rivalries[oppid].losses += 1
                            elif mpl["status"] == "winner":
                                self.rivalries[oppid].wins += 1
                            elif mpl["status"] == "tied":
                                self.rivalries[oppid].draws += 1
    
    def analyze_rivals(self):
        rivalries_sorted = [r for r in self.rivalries.values() if r.matches >= RIVAL_THRESHOLD]
        rivalries_sorted.sort(key=lambda x:x.matches, reverse=True)

        # If list is over size, trim the opponent(s) w/ the fewest matches off
        self.rivals = rivalries_sorted
        rival_threshold = RIVAL_THRESHOLD
        while len(self.rivals) > RIVAL_MAXCOUNT:
            rival_threshold += 1
            trimmed_rivals = [r for r in self.rivals if r.matches >= rival_threshold]
            if trimmed_rivals:
                self.rivals = trimmed_rivals
            else:
                # Prefer an oversized list to an empty one
                break

    def mostplayed(self):
        topchamps = self.champdata.top()
        if not topchamps:
            return "?"
        return "/".join(topchamps)

    
    def sortkey(self):
        # Sort players by # of tracked events entered descending
        # then alphabetically by username (case-insensitive) ascending
        # Assumes no player will enter 10,000+ events
        return f"{10000-len(self.events):05d} {self.username.lower()}"
