from collections import defaultdict

from .shared import OVERALL
from .cards import ELEMENTS
from .config import MAX_TOP_USERS

class ElementStats:
    def __init__(self):
        self.elements = {el: 0 for el in ELEMENTS}
        self.total_items = 0

    def add_deck(self, deck):
        self.total_items += 1
        if not deck.els: # avoid div/0
            return
        el_frac = 1/len(deck.els)
        for el in deck.els:
            self.elements[el] += el_frac

    def add_unknown(self):
        self.total_items += 1
        if "Unknown" in self.elements.keys():
            self.elements["Unknown"] += 1
        else:
            self.elements["Unknown"] = 1

    def __iter__(self):
        for el,quant in self.elements.items():
            if self.total_items:
                dec = quant / self.total_items
            else:
                dec = 0
            pct = round(dec*100, 1)
            yield (el, quant, pct)
    
    def __getitem__(self, el):
        quant = self.elements[el]
        if self.total_items == 0:
            pct = 0.0
        else:
            pct = round(100*quant/self.total_items, 1)
        return (quant, pct)

    def top(self):
        typedata = [(i,q) for i,q in self.elements.items() if i != "Unknown" and q>0]
        if not typedata:
            return []
        typedata.sort(key=lambda x:x[1], reverse=True)
        top_quant = typedata[0][1]
        tied_top = [t[0] for t in typedata if t[1] >= top_quant]
        return tied_top
    
    def exists_for(self, item):
        if item in self.elements.keys():
            return True
        return False

class TypeStats:
    def __init__(self):
        self.total_items = 0
        self.items = {}
        self.item_elements = {}

    def add_unknown(self):
        self.total_items += 1

        ## Don't actually add explicit "Unknown" entries for archetypes;
        ## the bar charts are better without them.
        # if "Unknown" in self.items:
        #     self.items["Unknown"] += 1
        #     self.item_elements["Unknown"].add_unknown()
        # else:
        #     self.items["Unknown"] = 1
        #     self.item_elements["Unknown"] = ElementStats()
        #     self.item_elements["Unknown"].add_unknown()

    def exists_for(self, item):
        if item == OVERALL:
            return False
        if item in self.items.keys():
            if self.items[item] > 0:
                return True
        return False

    def __iter__(self):
        typedata = [(i,q) for i,q in self.items.items()]
        typedata.sort(key=lambda x:x[1], reverse=True)
        if typedata and self.total_items == 0:
            print(f"Total item count mismatch: {len(typedata)} vs {self.total_items}")
            print(typedata)
            exit(1)
        for t, quant in typedata:
            pct = round(100*quant/self.total_items, 1)
            yield (t, pct, quant, self.item_elements[t])

    def __getitem__(self, item):
        quant = self.items[item]
        pct = round(100*quant/self.total_items, 1)
        return (quant, pct, self.item_elements[item])

    def top(self):
        if not self.items:
            return []
        typedata = [(i,q) for i,q in self.items.items()]
        typedata.sort(key=lambda x:x[1], reverse=True)
        top_quant = typedata[0][1]
        tied_top = [t[0] for t in typedata if t[1] >= top_quant]
        return tied_top

class ChampStats(TypeStats):
    def add_deck(self, deck):
        self.total_items += 1
        if not deck.lineages:
            return

        # Multi-lineage decks (intentionally) count wholly for each champion
        for lineage in deck.lineages:
            if lineage in self.items.keys():
                self.items[lineage] += 1
                self.item_elements[lineage].add_deck(deck)
            else:
                self.items[lineage] = 1
                self.item_elements[lineage] = ElementStats()
                self.item_elements[lineage].add_deck(deck)


class ArcheStats(TypeStats):
    def __init__(self):
        self.known_subtypes = []
        super().__init__()

    def add_deck(self, deck):
        self.total_items += 1
        if not deck.archetypes:
            return

        for arche in deck.archetypes:
            if arche in self.items.keys():
                self.items[arche] += 1
                self.item_elements[arche].add_deck(deck)
            else:
                self.items[arche] = 1
                self.item_elements[arche] = ElementStats()
                self.item_elements[arche].add_deck(deck)

        for arche in deck.subtypes:
            if arche in self.items.keys():
                self.items[arche] += 1
                self.item_elements[arche].add_deck(deck)
            else:
                self.known_subtypes.append(arche)
                self.items[arche] = 1
                self.item_elements[arche] = ElementStats()
                self.item_elements[arche].add_deck(deck)

    def __iter__(self):
        for item, pct, quant, elstats in super().__iter__():
            if item in self.known_subtypes:
                continue
            yield item, pct, quant, elstats

class ConvRateStats:
    def __init__(self, stats_before, stats_after, bcr):
        self.bcr = bcr
        conversions = []
        if isinstance(stats_before, TypeStats):
            # These have pct/quant/elstats data
            for name, pre_pct, pre_quant, pre_elstats in stats_before:
                if stats_after.exists_for(name):
                    after_quant = stats_after[name][0]
                else:
                    after_quant = 0
                conversions.append( (name, self.calc_conversion(
                    pre_quant, after_quant, bcr
                )) )
        elif isinstance(stats_before, ElementStats):
            # These have only quant/pct data.
            for name, pre_quant, pre_pct in stats_before:
                if stats_after.exists_for(name):
                    after_quant = stats_after[name][0]
                else:
                    after_quant = 0
                conversions.append( (name, self.calc_conversion(
                    pre_quant, after_quant, bcr
                )) )
        else:
            raise TypeError("Unexpected conversion rate stats type: "+type(stats_before))
        conversions.sort(key=lambda x:x[1]["after"], reverse=True)
        self.data = {k:v for k,v in conversions}
    
    def calc_conversion(self, pre_quant, after_quant, bcr):
        if pre_quant == 0:
            cr = 0.0
        else:
            cr = after_quant / pre_quant
        rate_multiplier = cr / bcr
        vs_expected_decks = after_quant - (pre_quant * bcr)
        return {
            "rate": round(100*cr, 1),
            "mult": round(rate_multiplier, 2),
            "quant": round(vs_expected_decks, 1),
            "before": int(pre_quant),
            "after": int(after_quant),
        }
    
    def __iter__(self):
        for name, cr in self.data.items():
            yield name, cr

class RegionStats:
    def __init__(self):
        self.total_items = 0
        self.items = {}

    def add_player(self, player):
        self.total_items += 1
        region = player.region or "Unknown"
        if region in self.items.keys():
            self.items[region] += 1
        else:
            self.items[region] = 1

    def __iter__(self):
        regdata = [(i,q) for i,q in self.items.items()]
        regdata.sort(key=lambda x:x[1], reverse=True)
        for reg,quant in regdata:
            if self.total_items:
                dec = quant / self.total_items
            else:
                dec = 0
            pct = round(dec*100, 1)
            yield (reg, quant, pct)

class Wielders:
    def __init__(self, name):
        self.name = name
        self.users = defaultdict(int)
        self.pdict = {} # Note: doesn't map to actual Player instances,
                        # just an arbitrary Entrant instance for that player

    def add(self, entrant, usage_score):
        if entrant.score <= 0:
            # You don't get to be a top wielder if you don't score any points
            return
        self.users[entrant.id] += usage_score
        self.pdict[entrant.id] = entrant

    def sort(self):
        sorted_users = [(uid,score) for uid,score in self.users.items()]
        sorted_users.sort(key=lambda x: x[1], reverse=True)
        self.users = {k:v for k,v in sorted_users}

    def top(self):
        user_pids = list(self.users.keys())
        if user_pids:
            return self.pdict[user_pids[0]]
        else:
            return "None"

    def __iter__(self):
        n = 0
        for pid,score in self.users.items():
            yield (self.pdict[pid],round(score, 1))
            n += 1
            if n >= MAX_TOP_USERS:
                break
