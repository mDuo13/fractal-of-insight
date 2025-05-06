from shared import keydefaultdict
from cards import ELEMENTS

LINEAGES = set()

class BCCell:
    def __init__(self, name):
        self.name = name
        self.wins = 0
        self.draws = 0
        self.matches = 0
        self.mirrors = 0
    
    def merge(self, cell):
        if self.name != cell.name:
            raise KeyError(f"BC cell merge mismatch: {self.name} vs {cell.name}")
        self.wins += cell.wins
        self.draws += cell.draws
        self.matches += cell.matches
        self.mirrors += cell.mirrors
    
    @property
    def rating(self):
        if self.matches == 0 or self.pct is None:
            return "no_data"
        if self.pct > 60:
            return "favored"
        elif self.pct < 40:
            return "unfavored"
        else:
            return "even"
    
    @property
    def true_matchcount(self):
        # Fix double-counting of mirror matches
        return self.matches - self.mirrors
    
    @property
    def pct(self):
        if self.matches == 0:
            return "?"
        return round(100 * (self.wins + (self.draws / 2)) / self.matches, 1)


class BCRow:
    def __init__(self, name):
        self.name = name
        self.wins = 0
        self.draws = 0
        self.matches = 0
        self.mirrors = 0
        self.intentional_draws = 0
        self.byes = 0
        self.cols = keydefaultdict(BCCell)
        self.subrows = keydefaultdict(BCRow)
    
    def id_vs(self, vs_deck, as_deck=None):
        # TODO: vs_deck might be None here
        self.intentional_draws += 1
    
    def bye(self, as_deck=None):
        self.byes += 1

    def win_vs(self, vs_deck, as_deck=None):
        self.wins += 1
        self.matches += 1
        for vs_t in vs_deck.archetypes:
            self.cols[vs_t].wins += 1
            self.cols[vs_t].matches += 1
            if self.name == vs_t:
                self.cols[vs_t].mirrors += 1/2
                self.mirrors += 1/2
        if as_deck:
            [LINEAGES.add(l) for l in as_deck.lineages]
            subtypes = as_deck.subtypes + as_deck.lineages + as_deck.els
            for as_t in subtypes:
                self.subrows[as_t].win_vs(vs_deck)
                if self.name in vs_deck.archetypes and (as_t in vs_deck.els or as_t in vs_deck.lineages):
                    self.subrows[as_t].mirrors += 1/2
        
    
    def loss_vs(self, vs_deck, as_deck=None):
        self.matches += 1
        for vs_t in vs_deck.archetypes:
            self.cols[vs_t].matches += 1
            if self.name == vs_t:
                self.cols[vs_t].mirrors += 1/2
                self.mirrors += 1/2
        if as_deck:
            [LINEAGES.add(l) for l in as_deck.lineages]
            subtypes = as_deck.subtypes + as_deck.lineages + as_deck.els
            for as_t in subtypes:
                self.subrows[as_t].loss_vs(vs_deck)
                if self.name in vs_deck.archetypes and (as_t in vs_deck.els or as_t in vs_deck.lineages):
                    self.subrows[as_t].mirrors += 1/2
    
    def draw_vs(self, vs_deck, as_deck=None):
        self.matches += 1
        self.draws += 1
        for vs_t in vs_deck.archetypes:
            self.cols[vs_t].matches += 1
            self.cols[vs_t].draws += 1
            if self.name == vs_t:
                self.cols[vs_t].mirrors += 1/2
                self.mirrors += 1/2
        if as_deck:
            [LINEAGES.add(l) for l in as_deck.lineages]
            subtypes = as_deck.subtypes + as_deck.lineages + as_deck.els
            for as_t in subtypes:
                self.subrows[as_t].draw_vs(vs_deck)
                if self.name in vs_deck.archetypes and (as_t in vs_deck.els or as_t in vs_deck.lineages):
                    self.subrows[as_t].mirrors += 1/2
    
    def merge(self, row):
        if self.name != row.name:
            raise KeyError(f"BC row merge mismatch: {self.name} vs {row.name}")
        self.wins += row.wins
        self.draws += row.draws
        self.matches += row.matches
        self.mirrors += row.mirrors
        self.intentional_draws += row.intentional_draws
        self.byes += row.byes
        for cname, c in row.cols.items():
            self.cols[cname].merge(c)
        for as_sub,subrow in row.subrows.items():
            self.subrows[as_sub].merge(subrow)

    def sortby(self, keyorder):
        newcols = keydefaultdict(BCCell)
        for key in keyorder:
            newcols[key] = self.cols[key]
            newcols[key].mirrors = int(newcols[key].mirrors)
        self.cols = newcols
        for subrow in self.subrows.values():
            subrow.sortby(keyorder)
        # Reorder sub-rows with elements → lineages → subtypes
        subrow_keys = list(self.subrows.keys())
        subrow_keys.sort(key=lambda x:self.subrows[x].sortkey(), reverse=True)
        new_subrows = keydefaultdict(BCRow)
        for k in subrow_keys:
            new_subrows[k] = self.subrows[k]
        self.subrows = new_subrows
        self.mirrors = int(self.mirrors)
    
    def sortkey(self):
        if self.name in ELEMENTS:
            key1 = 9
        elif self.name in LINEAGES:
            key1 = 8
        else:
            key1 = 0

        return f"{key1}{self.true_matchcount:07}"
        # return self.true_matchcount
    
    @property
    def true_matchcount(self):
        # Fix double-counting of mirror matches
        return self.matches - self.mirrors

    @property
    def overall_pct(self):
        if self.matches == 0:
            return "?"
        return round(100 * (self.wins + (self.draws / 2)) / self.matches, 1)

    def items(self):
        for k,v in self.cols.items():
            yield k,v
    
    def __getitem__(self, key):
        return self.cols[key]

class BattleChart:
    def __init__(self):
        self.rows = keydefaultdict(BCRow)

    @classmethod
    def from_event(cls, e, threshold=None, track_elo=False):
        self = cls()
        pdict = e.pdict
        stages = e.evt["stages"]

        for stage in stages:
            for rnd in stage["rounds"]:
                for match in rnd["matches"]:
                    if len(match["pairing"]) < 2:
                        p1r = match["pairing"][0]
                        p1 = pdict[p1r["id"]]
                        if p1.deck:
                            for as_t in p1.deck.archetypes:
                                self.rows[as_t].bye()
                        #print("        And a bye")
                        continue
                    if match["status"] == "started":
                        #print("         Match ongoing")
                        continue

                    p1r = match["pairing"][0]
                    p2r = match["pairing"][1]

                    p1 = pdict[p1r["id"]]
                    p2 = pdict[p2r["id"]]

                    if track_elo:
                        p1.elo_diff += match["pairing"][0].get("eloChange", 0)
                        p2.elo_diff += match["pairing"][1].get("eloChange", 0)

                    if p1r["score"] == p2r["score"] and p1r["score"] == 0:
                        #print(f"        intentional draw")
                        if p1.deck:
                            for as_t in p1.deck.archetypes:
                                self.rows[as_t].id_vs(p2.deck)
                        if p2.deck:
                            for as_t in p2.deck.archetypes:
                                self.rows[as_t].id_vs(p1.deck)
                        continue
                    elif not p1.deck or not p2.deck:
                        # TODO: maybe note the win vs an unknown deck?
                        # since it affects overall win rate.
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
                        # outcome = "beats"
                        for as_t in p1.deck.archetypes:
                            self.rows[as_t].win_vs(p2.deck, as_deck=p1.deck)
                        for vs_t in p2.deck.archetypes:
                            self.rows[vs_t].loss_vs(p1.deck, as_deck=p2.deck)
                    
                    elif p1r["score"] < p2r["score"]:
                        # outcome = "loses to"
                        for as_t in p1.deck.archetypes:
                            self.rows[as_t].loss_vs(p2.deck, as_deck=p1.deck)
                        for vs_t in p2.deck.archetypes:
                            self.rows[vs_t].win_vs(p1.deck, as_deck=p2.deck)

                    else:
                        # outcome = "ties"
                        for as_t in p1.deck.archetypes:
                            self.rows[as_t].draw_vs(p2.deck, as_deck=p1.deck)
                        for vs_t in p2.deck.archetypes:
                            self.rows[vs_t].draw_vs(p1.deck, as_deck=p2.deck)

                    # print(f"        {p1.deck} {outcome} {p2.deck}")
        self.sort()
        return self
    
    @classmethod
    def from_merge(cls, bclist):
        self = cls()
        for bc in bclist:
            for as_deck,row in bc.items():
                self.rows[as_deck].merge(row)
        self.sort()
        return self
    
    def sort(self):
        rowlist = list((k,v) for k,v in self.rows.items())
        rowlist.sort(key=lambda x:x[1].sortkey(), reverse=True)
        self.rows = {k:v for k,v in rowlist}
        for row in self.rows.values():
            row.sortby(self.rows.keys())

    def items(self):
        for k,v in self.rows.items():
            if not v.matches:
                continue
            yield k,v
    
    def has_data_for(self, arche):
        if arche in self.rows.keys():
            return True
        return False
    
    def __getitem__(self, key):
        return self.rows[key]
