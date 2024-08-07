from deck import Deck

from datalayer import get_deck

class Player:
    def __init__(self, data, evt_id, evt_time=0):
        self.id = data["id"]
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

        if data.get("isDecklistPublic"):
            dl = get_deck(self.id, evt_id)
            self.deck = Deck(dl, evt_time)
        else:
            self.deck = None
    
    def sortkey(self):
        return self.score + (self.omw/100) + (self.gwp / 100000)
    
    def __str__(self):
        return f'{self.username} #{self.id}'
