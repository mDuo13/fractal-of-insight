from collections import defaultdict

from datalayer import get_spoiler, sideload_deck, carddata, spoilerdata, card_is_floating
from deck import lineage
from cards import ELEMENTS, SPIRITTYPES, LINEAGE_BREAK

SPOILER_SEASONS = [
    "HVN"
]

def get_card_or_spoiler(cardname):
    if cardname in spoilerdata.keys():
        return spoilerdata[cardname]
    return carddata[cardname]

def get_card_img(cardname):
    if cardname in spoilerdata.keys():
        return spoilerdata[cardname]["img"]
    return carddata[cardname]["img"]

class MockDeck:
    def __init__(self, szn, id, deck):
        fname = f"data/spoilers/{szn.lower()}/deck_{id}.txt"
        self.dl = sideload_deck(id, -1, fname=fname)
        for card_o in self.dl["main"]:
            cardname = card_o["card"]
            if cardname in spoilerdata.keys():
                card_o["newspoiler"] = spoilerdata[cardname].get("newspoiler", False)
        self.archetypes = deck["archetypes"]
        self.lineages = deck["lineages"]
        self.els = deck["els"]
        self.subtypes = []
        
        self.find_champs()
        self.find_spirits()
        self.count_cards()
        self.cardlist_imgs()

    def count_cards(self):
        card_types = defaultdict(int)
        self.floating = 0
        m = 0
        for card_o in self.dl["material"]:
            m += card_o["quantity"] # should be 1 unless there's something weird going on
        self.mat_total = m
        n = 0
        for card_o in self.dl["main"]:
            n += card_o["quantity"]
            card = get_card_or_spoiler(card_o["card"])
            for cardtype in card["types"]:
                card_types[cardtype] += card_o["quantity"]
            if card_is_floating(card, self.champs):
                self.floating += card_o["quantity"]
        self.main_total = n
        card_types_sorted = [(k,v) for k,v in card_types.items()]
        card_types_sorted.sort(key=lambda x:x[0])
        self.card_types = {k:v for k,v in card_types_sorted}

        b = 0
        p = 0
        for card_o in self.dl["sideboard"]:
            card = get_card_or_spoiler(card_o["card"])
            b += card_o["quantity"]
            if "CHAMPION" in card["types"] or "REGALIA" in card["types"]:
                p += 3 * card_o["quantity"]
            else:
                p += 1 * card_o["quantity"]
        self.side_total = b
        self.side_points = p
    
    def find_spirits(self):
        self.spirits = []
        for card_o in self.dl["material"]:
            cardname = card_o["card"]
            card = get_card_or_spoiler(cardname)
            if card.get("level") == 0:
                self.spirits.append(cardname)
    
    def find_champs(self):
        self.champs = []
        lineages = []
        levels = set()
        self.is_hybrid = False
        for card_o in self.dl["material"]:
            cardname = card_o["card"]
            card = get_card_or_spoiler(cardname)
            
            if "CHAMPION" in card.get("types", []):
                if card["level"] == 1 or cardname in LINEAGE_BREAK:
                    lineages.append(lineage(cardname))
                    if card["level"] in levels:
                        self.is_hybrid = True
                    self.champs.append(cardname)
                    levels.add(card["level"])
                elif lineage(cardname) in lineages:
                    self.champs.append(cardname)
                    levels.add(card["level"])

        self.lineages = list(dict.fromkeys(lineages)) # Uniquified
    
    def cardlist_imgs(self):
        for cat in ("material", "main", "sideboard"):
            for card_o in self.dl[cat]:
                card_o["img"] = get_card_img(card_o["card"])

    def __str__(self):
        spiritstr = ""
        if len(self.spirits) < 1:
            spiritstr = "(Spiritless???) "
        elif len(self.spirits) > 1:
            if len(self.els) == 1:
                spirittypes = []
                for spirit in self.spirits:
                    for keyword in SPIRITTYPES:
                        if keyword in spirit:
                            spirittypes.append(keyword)
                            break
                    else:
                        spirittypes.append("Regular")
                spirittypes.sort(key=lambda x: "zzz" if x=="Regular" else x) #Sort "Regular" last
                spiritstr = "/".join(spirittypes) + " " + self.els[0]
            else:
                spiritstr = "(Multi-Element) "
        else:
            spirit = self.spirits[0]
            for keyword in SPIRITTYPES:
                if keyword in spirit:
                    spiritstr += keyword + " "
            
            spiritstr += "/".join(self.els)

        if len(self.lineages) == 1:
            champstr = list(self.lineages)[0]
        elif len(self.lineages) > 1:
            champset = {lineage(c):True for c in self.champs if lineage(c) in self.lineages}
            champstr = "/".join(champset.keys())
        else:
            champstr = ""
        if self.is_hybrid:
            champstr += " Hybrid"

        if not self.archetypes:
            archetypestr = ""
        else:
            archetype_list = []
            for st in self.subtypes:
                archetype_list.append(SUBTYPES[st].shortname)
            for arche in self.archetypes:
                archetype_list.append(arche)
            archetypestr = " ".join(archetype_list)

        return " ".join((spiritstr, archetypestr, champstr)).replace("  "," ")

class MockEntrant:
    def __init__(self, data, szn):
        self.id = data["id"]
        self.username = data["username"]
        self.wins = data["statsWins"]
        self.losses = data["statsLosses"]
        self.ties = data["statsTies"]
        self.record = f"{self.wins}-{self.losses}-{self.ties}"
        self.elo = data["scoreElo"]
        self.elo_diff = 0
        deckdata = data["deck"]
        self.deck = MockDeck(szn, self.id, deckdata)
    
    def __str__(self):
        if self.id:
            return f'{self.username} #{self.id}'
        return self.username

class SpoilerEvent:
    def __init__(self, szn):
        data = get_spoiler(szn)
        self.season = szn.upper()
        self.players = []
        for p in data["players"]:
            self.players.append(MockEntrant(p, szn))
