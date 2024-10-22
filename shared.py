import re
from cards import ELEMENTS

def slugify(s):
    unacceptable_chars = re.compile(r"[^A-Za-z0-9 -]+")
    whitespace_regex = re.compile(r"\s+")
    s = re.sub(unacceptable_chars, "", s)
    s = re.sub(whitespace_regex, "-", s)
    if not s:
        s = "_"
    return s.lower()

def fix_case(cardname):
    repls = {
        "'S":"'s",
        "’S":"'s",
        " And ": " and ",
        " At ":" at ",
        " By ": " by ",
        " De ": " de ",
        " For ": " for ",
        " From ":" from ",
        " In ":" in ",
        " Into ":" into ",
        " Of ": " of ",
        "Mk Iii": "Mk III",
        "Mk Ii": "Mk II",
        " The ":" the ",
        " To ":" to ",
        " With ":" with ",
        ", with ": ", With ", # "Silvie, With the Pack" vs "Smack with Flute"
        "\u2019S": "'s",
    }
    cardname = cardname.title()
    for k,v in repls.items():
        cardname = cardname.replace(k,v)

    return cardname

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
            dec = quant / self.total_items
            pct = round(dec*100, 1)
            yield (el, quant, pct)

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
            yield (t, pct, self.item_elements[t])

    def __getitem__(self, item):
        quant = self.items[item]
        pct = round(100*quant/self.total_items, 1)
        return (item, pct, self.item_elements[item])

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
        
        # TODO: fractional numbers for multi-lineage decks?
        #lin_frac = 1/len(deck.lineages)
        for lineage in deck.lineages:
            if lineage in self.items.keys():
                self.items[lineage] += 1
                self.item_elements[lineage].add_deck(deck)
            else:
                self.items[lineage] = 1
                self.item_elements[lineage] = ElementStats()
                self.item_elements[lineage].add_deck(deck)
    

class ArcheStats(TypeStats):
    def add_deck(self, deck):
        self.total_items += 1
        if not deck.archetypes:
            return
        
        # TODO: fractions for multi-archetype decks?
        for arche in deck.archetypes:
            if arche in self.items.keys():
                self.items[arche] += 1
                self.item_elements[arche].add_deck(deck)
            else:
                self.items[arche] = 1
                self.item_elements[arche] = ElementStats()
                self.item_elements[arche].add_deck(deck)
