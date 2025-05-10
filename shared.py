import re
from collections import defaultdict

from cards import ELEMENTS

OVERALL = "__overall__"

def slugify(s):
    unacceptable_chars = re.compile(r"[^A-Za-z0-9 -]+")
    whitespace_regex = re.compile(r"\s+")
    s = re.sub(unacceptable_chars, "", s)
    s = re.sub(whitespace_regex, "-", s)
    if not s:
        s = "_"
    return s.lower()

def lineage(champname):
    return champname.split(",",1)[0]

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

class keydefaultdict(defaultdict):
    # https://stackoverflow.com/questions/2912231/is-there-a-clever-way-to-pass-the-key-to-defaultdicts-default-factory
    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError( key )
        else:
            ret = self[key] = self.default_factory(key)
            return ret

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

REGIONS = {
    "":   {"name": "Online", "flag": "🌐"},
    "AE": {"name": "United Arab Emirates","flag": "🇦🇪"},
    "AT": {"name": "Austria", "flag": "🇦🇹"},
    "AU": {"name": "Australia","flag": "🇦🇺"},
    "BE": {"name": "Belgium","flag": "🇧🇪"},
    "BN": {"name": "Brunei","flag": "🇧🇳"},
    "CA": {"name": "Canada","flag": "🇨🇦"},
    "CH": {"name": "Switzerland","flag": "🇨🇭"},
    "CN": {"name": "China", "flag": "🇨🇳"},
    "CR": {"name": "Costa Rica", "flag": "🇨🇷"},
    "CZ": {"name": "Czech Republic","flag":"🇨🇿"},
    "DE": {"name": "Germany","flag": "🇩🇪"},
    "DK": {"name": "Denmark","flag": "🇩🇰"},
    "ES": {"name": "Spain","flag": "🇪🇸"},
    "FI": {"name": "Finland","flag":"🇫🇮"},
    "FR": {"name": "France", "flag": "🇫🇷"},
    "GB": {"name": "United Kingdom","flag": "🇬🇧"},
    "GR": {"name": "Greece","flag": "🇬🇷"},
    "HK": {"name": "Hong Kong","flag": "🇭🇰"},
    "HR": {"name": "Croatia","flag": "🇭🇷"},
    "HU": {"name": "Hungary","flag": "🇭🇺"},
    "ID": {"name": "Indonesia","flag": "🇮🇩"},
    "IT": {"name": "Italy","flag": "🇮🇹"},
    "JP": {"name": "Japan","flag": "🇯🇵"},
    "KR": {"name": "South Korea","flag": "🇰🇷"},
    "KW": {"name": "Kuwait","flag": "🇰🇼"},
    "MX": {"name": "Mexico","flag": "🇲🇽"},
    "MY": {"name": "Malaysia","flag": "🇲🇾"},
    "NL": {"name": "Netherlands","flag": "🇳🇱"},
    "NZ": {"name": "New Zealand","flag": "🇳🇿"},
    "PH": {"name": "Philippines","flag": "🇵🇭"},
    "PL": {"name": "Poland","flag": "🇵🇱"},
    "PR": {"name": "Puerto Rico","flag": "🇵🇷"},
    "PT": {"name": "Portugal","flag":"🇵🇹"},
    "SE": {"name": "Sweden","flag": "🇸🇪"},
    "SG": {"name": "Singapore","flag": "🇸🇬"},
    "SI": {"name": "Slovenia","flag":"🇸🇮"},
    "SK": {"name": "Slovakia","flag":"🇸🇰"},
    "TW": {"name": "Taiwan","flag": "🇹🇼"},
    "US": {"name": "United States of America","flag": "🇺🇸"},
}
