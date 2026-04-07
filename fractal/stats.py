from .shared import OVERALL
from .cards import ELEMENTS

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
