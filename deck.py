from shared import slugify
from datalayer import get_card_img
from cards import LV0, LV1, LV2, LV3, ELEMENTS, SPIRITTYPES
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
    def __init__(self, dl):
        self.dl = dl
        self.find_spirits()
        self.find_champs()
        self.find_archetypes()
        self.find_elements()
        self.count_cards()
        self.sort_dl()
        self.cardlist_imgs()
    
    def find_spirits(self):
        self.spirits = []
        for card_o in self.dl["material"]:
            card = card_o["card"]
            if card in LV0:
                self.spirits.append(card)
    
    def find_champs(self):
        self.champs = []
        self.is_hybrid = False
        for card_o in self.dl["material"]:
            card = card_o["card"]
            for lv in [LV1,LV2,LV3]:
                if card in lv:
                    existing_lv_champs = set(self.champs) & set(lv)
                    if existing_lv_champs and lineage(card) not in [lineage(c) for c in existing_lv_champs]:
                        self.is_hybrid = True
                    self.champs.append(card)
    
    def find_archetypes(self):
        self.archetypes = []
        for archetype, acards in ARCHETYPES.items():
            cancel = False
            for anticard in acards.get("notmain",[]):
                for card_o in self.dl["main"]:
                    if card_o["card"] == anticard:
                        cancel = True
                        break
            if cancel:
                continue

            for matcard in acards["mats"]:
                for card_o in self.dl["material"]:
                    if card_o["card"] == matcard:
                        self.archetypes.append( archetype )
                        cancel = True
                        break
                if cancel:
                    break
            if archetype in self.archetypes:
                continue

            for maincard in acards["main"]:
                for card_o in self.dl["main"]:
                    if card_o["card"] == maincard:
                        self.archetypes.append( archetype )
                        cancel = True
                        break
                if cancel:
                    break
    
    def find_elements(self):
        # Doesn't include advanced elements or basic-elemental champs
        els = []
        for spirit in self.spirits:
            for element in ELEMENTS:
                if element in spirit:
                    els.append(element)
                    break
        if not els:
            els.append("Norm")
        self.els = els
    
    def sort_dl(self):
        self.dl["main"].sort(key=lambda x:x["card"])
        self.dl["sideboard"].sort(key=lambda x:x["card"])
        self.dl["material"].sort(key=rank_mat_card)
    
    def count_cards(self):
        n = 0
        for card in self.dl["main"]:
            n += card["quantity"]
        self.main_total = n

        b = 0
        for card in self.dl["sideboard"]:
            b += card["quantity"]
        self.side_total = b

    def cardlist_imgs(self):
        for cat in ("material", "main", "sideboard"):
            for card_o in self.dl[cat]:
                card_o["img"] = get_card_img(card_o["card"])
    
    def __str__(self):
        spiritstr = ""
        if len(self.spirits) < 1:
            spiritstr = "(Spiritless???) "
        elif len(self.spirits) > 1:
            spiritstr = "(Multi-Spirit) "
        else:
            spirit = self.spirits[0]
            for keyword in SPIRITTYPES:
                if keyword in spirit:
                    spiritstr += keyword + " "
            
            spiritstr += "/".join(self.els)

        lineages = set([lineage(c) for c in self.champs])
        if len(lineages) == 1:
            champstr = list(lineages)[0]
        elif len(lineages) > 1:
            self.champs.sort(key=lambda x: rank_mat_card({"card":x}))
            champset = {lineage(c):True for c in self.champs}
            champstr = "/".join(champset.keys())
        if self.is_hybrid:
            champstr += " Hybrid"

        if not self.archetypes:
            archetypestr = ""
        else:
            archetypestr = " ".join(list(set(self.archetypes)))

        return " ".join((spiritstr, archetypestr, champstr)).replace("  "," ")
