from collections import defaultdict

from deck import Deck
from datalayer import get_deck, NoDeck
from cards import ELEMENTS
from shared import keydefaultdict, ElementStats, ChampStats, ArcheStats
from competition import TEAM_STANDARD
from achievements import AchievementSet

RIVAL_THRESHOLD = 3 # min matches to count as a rival
RIVAL_MAXCOUNT = 5 # trim rivals list if it's over this size

class Entrant:
    """
    Represents one player's entry into one event
    """
    def __init__(self, data, evt_id, evt):
        self.id = data["id"]
        self.evt_id = evt_id
        self.event = evt
        self.evt_time = evt.evt["startAt"]
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
        self.vp = round(data["scoreVP"])
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
            
        try:
            is_public = data.get("isDecklistPublic")
            dl = get_deck(self.id, evt_id, is_public)
            self.deck = Deck(dl, self)
        # else:
        except (NoDeck):
            self.deck = None
        
        self.first_plays = [] # List of card names first played in this deck.
                              # Populated by cardstats.
    
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
        self.region = entrant.region
        self.achievements = AchievementSet()
        self.peak_elo = entrant.rank_elo
        self.vp = entrant.vp
    
    def add_entry(self, entrant):
        self.events.append(entrant)
        if entrant.elo > self.peak_elo:
            self.peak_elo = entrant.elo
    
    def analyze(self):
        # To be called after all event entries have been added
        self.events.sort(key=lambda x: x.evt_time, reverse=True)
        self.num_decklists = len([e for e in self.events if e.deck])
        self.analyze_champions()
        self.track_rivals()
        self.check_achievements()
        
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

    def track_rivals(self):
        rivalries=keydefaultdict(Rivalry)
        for entry in self.events:
            e = entry.event
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
                                    rivalries[oppid].losses += 1
                                elif mpl["status"] == "winner":
                                    rivalries[oppid].wins += 1
                                elif mpl["status"] == "tied":
                                    rivalries[oppid].draws += 1
    
        rivalries_sorted = [r for r in rivalries.values() if r.matches >= RIVAL_THRESHOLD]
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

    def check_achievements(self):
        events_chrono = list(reversed(self.events))
        # Globetrotter
        visited_countries = set()
        for e in events_chrono:
            if e.event.country:
                visited_countries.add(e.event.country)

                if len(visited_countries) > 2:
                    self.achievements.add("Globetrotter", e, details=", ".join(visited_countries))
                    break
        
        # Match results achievements
        for e in events_chrono:
            if e.event.matchformat_swiss != "bo3":
                continue
            # Skipping multi-stage events... usually stage 2 is untimed anyway
            swiss = e.event.evt["stages"][0]
            for rnd_num, rnd in enumerate(swiss["rounds"]):
                for match in rnd["matches"]:
                    for p in match["pairing"]:
                        if p["id"] == self.id and p["score"] == 1 and p["status"] == "winner":
                            #print(f"Long game: {self.username} in {e.event.name}")
                            self.achievements.add("Play the Long Game", e, details=f"Round {rnd_num+1}")
                        if p["id"] == self.id and p["score"] == 0 and p["status"] == "tied":
                            self.achievements.add("Hand Shaker", e, details=f"Round {rnd_num+1}")
        
        # Achievements for entering & winning different event types
        regionals_by_season = defaultdict(int)
        for e in events_chrono:
            if e.event.category["name"] == "Regular":
                self.achievements.add("Just Chillin'", e)
                if e.placement == 1 and len(e.event.players) >= 40:
                    self.achievements.add("Big Chillin'", e, details=f"{len(e.event.players)} players")
            elif e.event.category["name"] == "Store Champs":
                self.achievements.add("Throw Down", e, details=e.event.evt["store"]["name"])
                if e.placement == 1:
                    self.achievements.add("This Is My House", e, details=e.event.evt["store"]["name"])
            elif e.event.category["name"] == "Regionals":
                self.achievements.add("Turf Warrior", e)
                if e.placement == 1:
                    self.achievements.add("King of the Hill", e)
                regionals_by_season[e.event.season] += 1
                if regionals_by_season[e.event.season] >= 2:
                    self.achievements.add("Nomad", e)
            elif e.event.category["name"] == "Ascent":
                self.achievements.add("Mountain Climber", e)
                if (e.placement <= 8 and e.event.evt["format"] != TEAM_STANDARD) or \
                   (e.placement <= 4 and e.event.evt["format"] == TEAM_STANDARD):
                    self.achievements.add("Spirited Competitor", e)
            elif e.event.category["name"] == "Nationals":
                self.achievements.add("Join the Battle", e)
                if e.placement == 1:
                    self.achievements.add("Hometown Hero", e)
            elif e.event.category["name"] == "Worlds":
                self.achievements.add("World-Class Competitor", e)
                if e.placement == 1:
                    self.achievements.add("Ascendant", e)
        
        # Achievements for decklist quirks
        elements_used = set()
        classes_used = set()
        champ_times = defaultdict(int)
        for e in events_chrono:
            if e.deck:
                for el in e.deck.els:
                    elements_used.add(el)
                    if len(elements_used) >= 3:
                        self.achievements.add("Elementalist", e, details=", ".join(elements_used))
                for klass in e.deck.classes:
                    classes_used.add(klass)
                    if len(classes_used) >= 7:
                        self.achievements.add("Classy", e)
                for lineage in e.deck.lineages:
                    champ_times[lineage] += 1
                    if champ_times[lineage] >= 5:
                        self.achievements.add("Loyalist", e, details=lineage)
                if "Crux" in e.deck.archetypes:
                    self.achievements.add("Crux is Fine", e, details=str(e.deck))
                if e.deck.is_hybrid:
                    self.achievements.add("Hybrid Theory", e, details="/".join(e.deck.lineages))
                if e.deck.main_total > 60:
                    self.achievements.add("Big Deck Energy", e, details=f"{e.deck} ({e.deck.main_total} cards)")
                if e.deck.floating >= 30:
                    self.achievements.add("Antigravity", e, details=str(e.deck))
        
        # Four Seasons
        seasons_played = set()
        for e in events_chrono:
            if e.event.season != "OFF":
                seasons_played.add(e.event.season)
                if len(seasons_played) >= 4:
                    self.achievements.add("Four Seasons", e, details=", ".join(seasons_played))
                    break

        # Achievements for decklist similarity
        for e in events_chrono:
            if not e.deck:
                continue
            decks_before, decks_sameday, decks_after = e.deck.split_similar_decks(limit=99999)
            for d, sim in decks_before:
                if sim >= 100 and d.entrant.id == self.id:
                    self.achievements.add("Runback", e, details=str(e.deck))
            for d, sim in decks_sameday:
                if sim >= 100 and d.entrant.evt_id == e.evt_id:
                    self.achievements.add("Team Builder", e, details=d.entrant.username)
            if decks_after and not decks_before:
                all_after = [d for d,sim in decks_after if d.entrant.id != self.id]
                if all_after:
                    all_after.sort(key=lambda d: d.date)
                    netdecked_by = all_after[0]
                    self.achievements.add("I Made This", netdecked_by.entrant, details=f"{netdecked_by.entrant}'s {netdecked_by}")
        
        # We Meet Again
        for e in events_chrono:
            opps_played = set()
            for stage in e.event.evt["stages"]:
                for rnd in stage["rounds"]:
                    opp = rnd["pairings"].get(str(self.id))
                    if not opp:
                        continue
                    if opp in opps_played:
                        self.achievements.add("We Meet Again", e)
                    else:
                        opps_played.add(opp)
        
        # Ladder Leaper
        for e in events_chrono:
            if round(e.elo_diff,0) >= 50:
                self.achievements.add("Ladder Leaper", e)
            if round(e.elo, 0) >= 1400:
                self.achievements.add("Deadly Duelist", e)
        
        # Capped Veteran
        for e in events_chrono:
            if e.vp >= 800:
                self.achievements.add("Capped Veteran", e)
        
        # Technically Undefeated
        for e in events_chrono:
            if e.losses == 0 and e.ties >= 2:
                self.achievements.add("Technically Undefeated", e, details=e.record)
        
        # First card plays
        for e in events_chrono:
            for cardname in e.first_plays:
                self.achievements.add_card_first(cardname, e)

    
    def sortkey(self):
        # Sort players by # of tracked events entered descending
        # then alphabetically by username (case-insensitive) ascending
        # Assumes no player will enter 10,000+ events
        return f"{10000-len(self.events):05d} {self.username.lower()}"
