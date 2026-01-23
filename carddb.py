import json
from os import scandir

from cards import REMOVED_FROM_PRXY
from shared import fix_case

CARDS_FOLDER = "./data/index/"

class CardDB:
    """
    Mimics a dictionary of cardname:card_details where card_details are loaded
    from a local cache of GA Index (JSON files), with minor postprocessing.
    The data is not loaded until the first time anything queries it, so that an
    instance of this class can be a shared global in datalayer.py without
    affecting load times when importing other things from datalayer.
    """
    def __init__(self):
        self.data = {}
        self.set_groups = {}
        self.initialized = False

    def load(self):
        for entry in scandir(CARDS_FOLDER):
            if entry.is_file() and entry.name[-5:] == ".json" and entry.name[:1] != "_":
                with open(entry) as f:
                    setlist = json.load(f)
                for card in setlist:
                    cardname = fix_case(card["name"])

                    o_orients = card["editions"][0].get("other_orientations")
                    if o_orients:
                        card["back"] = o_orients[0]

                    if cardname not in self.data.keys():
                        self.data[cardname] = card
                    else:
                        self.data[cardname]["result_editions"] += card["result_editions"]
        self.load_set_groups()
        for cardname, card in self.data.items():
            self.set_card_defaults(cardname, card)
        self.initialized = True
    
    def load_set_groups(self):
        try:
            with open("data/index/_set-groups.json") as f:
                set_groups_list = json.load(f)
            set_groups_list.reverse() # Put them with, generally, oldest group first
            self.set_groups = {s["name"]:s for s in set_groups_list}
            self.set_groups["Other"] = {"name": "Other", "sets": []}

            for card in self.data.values():
                self.add_set_introduced(card)
        
        except FileNotFoundError:
            print("No data on set groups. Can't determine oldest edition of cards accurately")
            # Fallback method relies on set release_date field which is not a reliable
            # indicator of when a card actually released (mostly because of promos)
            for card in self.data.values():
                eds = sorted(card["editions"], key=lambda x:x["set"]["release_date"])
                oldest_ed = eds[0]
                card["set_introduced"] = oldest_ed["set"]["prefix"]
    
    def add_removed_cards(self):
        """
        Add legacy card data for cards that have been removed from Proxia's Vault
        """
        for cardname, fname in REMOVED_FROM_PRXY.items():
            with open(f"data/index/{fname}") as f:
                old_data = json.load(f)
                for oldcard in old_data:
                    if oldcard["name"] == cardname:
                        self.add_set_introduced(oldcard)
                        oldcard["removed"] = True
                        self.data[cardname] = oldcard
                        break
    
    def add_set_introduced(self, card):
        in_sets = [ed["set"]["prefix"] for ed in card["editions"]]
        found_sg = False
        for prefix in in_sets:
            for sg in self.set_groups.values():
                for sgs in sg["sets"]:
                    if sgs["prefix"] in in_sets:
                        card["set_introduced"] = sg["name"]
                        found_sg = True
                        break
                if found_sg:
                    break
            if found_sg:
                break
        if not found_sg:
            #print("Couldn't find set group for card:", card["name"])
            card["set_introduced"] = "Other"
    
    def set_card_defaults(self, cardname, card):
        """
        Pick default card image based on lowest rarity edition of card
        (excluding Supporter Packs) and add full name of double-sided cards.
        """
        lowest_rarity = 99
        for ced in card["result_editions"]:
            if ced["set"]["name"][:14] == "Supporter Pack":
                # Skip supporter pack editions since they're always reprints
                continue
            if ced["rarity"] < lowest_rarity:
                lowest_rarity = ced["rarity"]
                lowest_ced = ced
        if lowest_rarity == 99:
            exit(f"Error finding lowest rarity for {cardname}.")
        ed_img = lowest_ced["image"]
        card["img"] = f"https://api.gatcg.com{ed_img}"
        if card.get("back"):
            back_img = card["back"]["edition"]["image"]
            card["back"]["img"] = f"https://api.gatcg.com{back_img}"
            card["fullname"] = f"{card['name']} // {card['back']['name']}"
        else:
            card["fullname"] = card["name"]
    
    def get_set_groups(self):
        if not self.initialized:
            self.load()
        return self.set_groups

    def __getitem__(self, item):
        if not self.initialized:
            self.load()
        return self.data[item]

    def keys(self):
        if not self.initialized:
            self.load()
        return self.data.keys()

    def values(self):
        if not self.initialized:
            self.load()
        return self.data.values()
    
    def items(self):
        if not self.initialized:
            self.load()
        return self.data.items()
    
    def get(self, item, default=None):
        if not self.initialized:
            self.load()
        return self.data.get(item, default)
