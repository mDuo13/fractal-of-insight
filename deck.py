from time import strftime, gmtime
from collections import defaultdict

from shared import slugify, fix_case
from datalayer import get_card_img, carddata, card_is_floating
from cards import LV0, LV1, LV2, LV3, ELEMENTS, SPIRITTYPES, LINEAGE_BREAK
from archetypes import ARCHETYPES

def rank_mat_card(card_o):
    card = card_o["card"]
    if card in LV0:
        return "0"+card
    if card in LV1:
        return "1"+card
    if card in LV2:
        return "2"+card
    if card in LV3:
        return "3"+card
    return card

def lineage(champname):
    return champname.split(",",1)[0]

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
        #self.similar_decks.sort(key=lambda x:x[0].date)

    def find_spirits(self):
        self.spirits = []
        for card_o in self.dl["material"]:
            card = card_o["card"]
            if card in LV0:
                self.spirits.append(card)
    
    def find_champs(self):
        self.champs = []
        raw_lineages = []
        self.is_hybrid = False
        for card_o in self.dl["material"]:
            card = card_o["card"]
            for lv in [LV1,LV2,LV3]:
                if card in lv:
                    existing_lv_champs = set(self.champs) & set(lv)
                    if existing_lv_champs and lineage(card) not in [lineage(c) for c in existing_lv_champs]:
                        self.is_hybrid = True
                    self.champs.append(card)
                    if lv == LV1:
                        raw_lineages.append(card)
                    elif card in LINEAGE_BREAK:
                        raw_lineages.append(card)
        raw_lineages.sort(key=lambda x: rank_mat_card({"card":x}))
        self.lineages = [lineage(c) for c in raw_lineages]

    
    def find_archetypes(self):
        self.archetypes = []
        self.subtypes = []
        for archetype in ARCHETYPES.values():
            if archetype.match(self):
                self.archetypes.append( archetype.name )
                for st in archetype.subtypes:
                    if st.match(self):
                        self.subtypes.append(st)

    
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
                p += 4 * card_o["quantity"]
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
        Material deck cards are 4 points
        Main deck cards are 1 point per copy of a card
        Sideboard cards are scored the same except at ⅔ value since
            they're available for 2 games in a best of 3.
        T=118 if a deck has 12 material, 60 maindeck, and a 15-point sideboard.
        Returned as a percentage rounded to 1 decimal point.
        """
        
        total_me = 4*self.mat_total + self.main_total + ((2/3)*self.side_points)
        total_them = 4*other_deck.mat_total + other_deck.main_total + ((2/3)*other_deck.side_points)
        t = max(total_me, total_them)

        s = 0
        for sect,mult in (("material", 4), ("main", 1), ("sideboard", 1)):
            # Optimization since comparing deck similarity is pretty slow:
            # iterate both lists in parallel (they should be sorted at this point)
            # which should cut down on the calls to quantity_of on maindeck
            i = 0
            j = 0
            imax = len(self.dl[sect])
            jmax = len(other_deck.dl[sect])
            them_o = {"card": "","quantity":0}
            while i < imax and j < jmax:
                # TODO: make prize spirits to count the same as basic spirits?
                card_o = self.dl[sect][i]
                them_o = other_deck.dl[sect][j]
                if card_o["card"] < them_o["card"]:
                    i += 1
                    continue
                elif card_o["card"] > them_o["card"]:
                    j += 1
                    continue
                # Else the names match, compare quantities
            
                # TODO: optimize sideboard checking
                # q_me = card_o["quantity"] + ((2/3) * self.quantity_of(card_o["card"], search_sections=["sideboard"]))
                # # q_them = other_deck.quantity_of(cardname, search_sections=[sect]) + (
                # #             (2/3) * other_deck.quantity_of(cardname, search_sections=["sideboard"]))
                # q_them = them_o["quantity"] + ((2/3) * other_deck.quantity_of(card_o["card"], search_sections=["sideboard"]))
                q_me = card_o["quantity"]
                q_them = them_o["quantity"]
                if sect == "sideboard":
                    card = carddata[card_o["card"]]
                    if "CHAMPION" in card["types"] or "REGALIA" in card["types"]:
                        mult = 8/3
                    else:
                        mult = 2/3
                    
                s += mult * min(q_me, q_them)

                i+=1
                j+=1
        
        # for card_o in self.dl["sideboard"]:
        #     cardname = card_o["card"]
        #     #if self.quantity_of(cardname, search_sections=["material","main"]) == 0:
        #     if True:
        #         q_me = card_o["quantity"]
        #         q_them = other_deck.quantity_of(cardname, search_sections=["sideboard"])
        #         card = carddata[cardname]
        #         if "CHAMPION" in card["types"] or "REGALIA" in card["types"]:
        #             pointmult = 4
        #         else:
        #             pointmult = 1
        #         s += (2/3) * pointmult * min(q_me, q_them)
        return round(100*s/t, 1)
    
    def split_similar_decks(self):
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
        return decks_before, decks_sameday, decks_after
    
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

        #lineages = set([lineage(c) for c in self.champs])
        if len(self.lineages) == 1:
            champstr = list(self.lineages)[0]
        elif len(self.lineages) > 1:
            self.champs.sort(key=lambda x: rank_mat_card({"card":x}))
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
                archetype_list.append(st.shortname)
            for arche in self.archetypes:
                archetype_list.append(ARCHETYPES[arche].shortname)
            archetypestr = " ".join(archetype_list)

        return " ".join((spiritstr, archetypestr, champstr)).replace("  "," ")
    
    def __iter__(self):
        for card_o in self.dl["material"]:
            yield card_o["card"]
        for card_o in self.dl["main"]:
            yield card_o["card"]
