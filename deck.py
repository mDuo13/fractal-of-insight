from time import strftime, gmtime
from collections import defaultdict

from shared import slugify, fix_case, lineage
from datalayer import get_card_img, carddata, card_is_floating
from cards import ELEMENTS, SPIRITTYPES, LINEAGE_BREAK
from archetypes import ARCHETYPES, SUBTYPES
from cardstats import ALL_CARD_STATS

def rank_mat_card(card_o):
    cardname = card_o["card"]
    return rank_mat_cardname(cardname)
def rank_mat_cardname(cardname):
    card = carddata[cardname]
    if card["level"] is not None:
        return str(card["level"]) + cardname
    return cardname


def trim_similar(dlist, limit):
    """
    Given a list of (d,sim) tuples where d is a deck,
    return the limit most similar decks, ordered by date
    """
    if len(dlist) > limit:
        dlist2 = [x for x in dlist]
        dlist2.sort(key=lambda x:x[1], reverse=True)
        dlist2 = dlist2[:limit]
        dlist2.sort(key=lambda x:x[0].date)
        return dlist2
    return dlist

class Deck:
    def __init__(self, dl, entrant):
        self.dl = dl
        self.entrant = entrant
        self.date = strftime(r"%Y-%m-%d", gmtime(self.entrant.evt_time/1000))
        self.similar_decks = []
        self.fix_dl()
        self.find_spirits()
        self.find_champs()
        self.find_elements()
        self.count_cards() # populates self.card_types and self.floating as well as total counts
        self.find_archetypes()
        self.cardlist_imgs()
        
        ALL_CARD_STATS.add_deck(self)

    def find_spirits(self):
        self.spirits = []
        for card_o in self.dl["material"]:
            cardname = card_o["card"]
            card = carddata[cardname]
            if card.get("level") == 0:
                self.spirits.append(cardname)
    
    def find_champs(self):
        self.champs = []
        lineages = []
        levels = set()
        self.is_hybrid = False
        for card_o in self.dl["material"]:
            cardname = card_o["card"]
            card = carddata[cardname]
            
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

    
    def find_archetypes(self):
        self.archetypes = []
        self.subtypes = []
        for archetype in ARCHETYPES.values():
            if archetype.match(self):
                self.archetypes.append( archetype.name )
                for st in archetype.subtypes:
                    if st.match(self):
                        self.subtypes.append(st.name)

    
    def find_elements(self):
        # Doesn't include advanced elements or basic-elemental champs
        els = []
        for spirit in self.spirits:
            for element in ELEMENTS:
                if element in spirit:
                    if element not in els:
                        els.append(element)
                    break
        if not els:
            els.append("Norm")
        self.els = els
    
    def fix_dl(self):
        # TODO: handle more cases where card name isn't properly cased
        if not self.dl.get("main"):
            raise ValueError(f"Decklist has no maindeck? {self.dl}")
        for card_o in self.dl["main"]:
            card_o["card"] = fix_case(card_o["card"])
        for card_o in self.dl["material"]:
            card_o["card"] = fix_case(card_o["card"])
        for card_o in self.dl["sideboard"]:
            card_o["card"] = fix_case(card_o["card"])

        # Special case for Yeti local 9/5 which used Gate of Alterity as a placeholder for Polaris, Twinkling Cauldron
        if self.entrant.evt_time == 1725580800000:
            for card_o in self.dl["material"]:
                if card_o["card"] == "Gate of Alterity":
                    card_o["card"] = "Polaris, Twinkling Cauldron"

        self.dl["main"].sort(key=lambda x:x["card"])
        self.dl["sideboard"].sort(key=lambda x:x["card"])
        self.dl["material"].sort(key=rank_mat_card)
    
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
            card = carddata[card_o["card"]]
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
            card = carddata[card_o["card"]]
            b += card_o["quantity"]
            if "CHAMPION" in card["types"] or "REGALIA" in card["types"]:
                p += 3 * card_o["quantity"]
            else:
                p += 1 * card_o["quantity"]
        self.side_total = b
        self.side_points = p
    
    def quantity_of(self, cardname, search_sections=("material","main")):
        """
        Count how many copies of a card are in the mainboard/materials for the deck.
        """
        n = 0
        for cat in search_sections:
            for card_o in self.dl[cat]:
                if card_o["card"] == cardname:
                    n += card_o["quantity"]
        return n
        

    def cardlist_imgs(self):
        for cat in ("material", "main", "sideboard"):
            for card_o in self.dl[cat]:
                card_o["img"] = get_card_img(card_o["card"], at=self.entrant.evt_time)
    
    def similarity_to(self, other_deck):
        """
        Calculate a similarity score between two decks, as S/T, where
        S = total points in common and
        T = total points in the larger deck.
        Points are calculated as follows:
        Material deck cards are 3 points
        Main deck cards are 1 point per copy of a card
        Sideboard cards are scored the same except at ⅔ value since
            they're available for 2 games in a best of 3.
        T=118 if a deck has 12 material, 60 maindeck, and a 15-point sideboard.
        Returned as a percentage rounded to 1 decimal point.
        """
        
        total_me = 3*self.mat_total + self.main_total + ((2/3)*self.side_points)
        total_them = 3*other_deck.mat_total + other_deck.main_total + ((2/3)*other_deck.side_points)
        t = max(total_me, total_them)

        s = 0
        for sect,mult in (("material", 3), ("main", 1), ("sideboard", 1)):
            # Optimization since comparing deck similarity is pretty slow:
            # iterate both lists in parallel (they should be sorted at this point)
            # which should cut down on the calls to quantity_of on maindeck
            i = 0
            j = 0
            imax = len(self.dl[sect])
            jmax = len(other_deck.dl[sect])
            while i < imax and j < jmax:
                # TODO: make prize spirits to count the same as basic spirits?
                card_o = self.dl[sect][i]
                them_o = other_deck.dl[sect][j]
                # Use rank_mat_card instead of comparing names so sure prize spirits don't screw up the ordering
                if rank_mat_card(card_o) < rank_mat_card(them_o):
                    i += 1
                    continue
                elif rank_mat_card(card_o) > rank_mat_card(them_o):
                    j += 1
                    continue
                # Else the names match, compare quantities
                # TODO: look at sideboard in parallel for better matching
                q_me = card_o["quantity"]
                q_them = them_o["quantity"]
                if sect == "sideboard":
                    card = carddata[card_o["card"]]
                    if "CHAMPION" in card["types"] or "REGALIA" in card["types"]:
                        use_mult = 2 # ⅔ * 3
                    else:
                        use_mult = 2/3
                else:
                    use_mult = mult
                    
                s += use_mult * min(q_me, q_them)

                i+=1
                j+=1
        
        return round(100*s/t, 1)
    
    def split_similar_decks(self, limit=10):
        decks_before = []
        decks_sameday = []
        decks_after = []
        for d,sim in self.similar_decks:
            if d.date < self.date:
                decks_before.append([d,sim])
            elif d.date == self.date:
                decks_sameday.append([d,sim])
            else:
                decks_after.append([d,sim])
        
        return trim_similar(decks_before, limit), trim_similar(decks_sameday, limit), trim_similar(decks_after, limit)
    
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
                archetype_list.append(ARCHETYPES[arche].shortname)
            archetypestr = " ".join(archetype_list)

        return " ".join((spiritstr, archetypestr, champstr)).replace("  "," ")
    
    def __iter__(self):
        for card_o in self.dl["material"]:
            yield card_o["card"]
        for card_o in self.dl["main"]:
            yield card_o["card"]
