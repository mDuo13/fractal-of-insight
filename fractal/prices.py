import json
import re
from os import scandir

from .cards import PRIZE_EQUIVALENTS
from .shared import fix_case

TCG_ABBR = {
    # Mapping of official prefixes from Index : [list of abbreviations used by tcgcsv that may contain those cards]
    # not including cases where they match exactly
    "ALC 1st": ["ALC"],
    "AMB 1st": ["AMB1E"],
    "AMB": ["AMB1E"],
    "DTR 1st": ["DTR1E"],
    "DTR": ["DTR1E"],
    "EVP": ["EVP","EVP2","EVP3","EVP4"],
    "FTCA": ["FTC"],
    "HVN 1st": ["HVN"],
    "MRC 1st": ["MRC"],
    "MRC Alter": ["MH Alter"],
    "P22": ["P"],
    "P23": ["P"],
    "P24": ["P"],
    "P25": ["P"],
    "P26": ["P"],
    "PTMEVP": ["PHME"],
    "PTM 1st": ["PTM"],
    "PTMLGS": ["PTM"],
    "RDO 1st": ["RDO"],
    "RDOA": ["RDO"],
    "ReC-AUR": ["AURR"],
    "ReC-HVF": ["HVNFV"],
    "ReC-IDY": ["IDLCRS"],
    "ReC-SHD": ["SHD", "SHDLTE"],
    "ReC-SLM": ["SLM", "SLMLTE"],
    "ReC-BRV": ["BRLVST"],
}

TCGP_CARDNAMES = {
    # For cases where the data on TCGPlayer is entered inconsistently or has
    # additional info like variant number added to the card name.
    # May need to be updated if/when TCGP fixes their data.
    # Many DFCs incorrectly have separate listings per face.
    # Technically I could add curio foil and CSR entries here too for
    # completeness, but something is very weird if those are cheaper than the
    # regular versions.
    "Fatestone of Unrelenting // Cheetah of Bound Fury": [
        "Fatestone of Unrelenting",
        "Cheetah of Bound Fury",
    ],
    "Craggy Fatestone // Obstinate Cragback": [
        "Craggy Fatestone",
        "Obstinate Cragback",
    ],
    "Fatestone of Revelations // Young Wyrmling": [
        "Fatestone of Revelations",
        "Young Wyrmling",
    ],
    "Fatestone of Heaven // Heavenly Drake": [
        "Fatestone of Heaven",
        "Heavenly Drake",
    ],
    "Companion Fatestone // Fatebound Caracal": [
        "Companion Fatestone",
        "Fatebound Caracal",
    ],
    "Lavaplume Fatestone // Firebird Trailblazer": [
        "Lavaplume Fatestone",
        "Firebird Trailblazer",
    ],
    "Fabled Azurite Fatestone // Seiryuu, Azure Dragon": [
        #tcgp has both, but the one with the // is the sapphire promo only
        "Fabled Azurite Fatestone",
        "Fabled Azurite Fatestone // Seiryuu, Azure Dragon",
    ],
    "Overlapping Visages": [
        "Overlapping Visages (025A)",
        "Overlapping Visages (025B)",
    ],
    "Gemini Starbearer": "Gemini StarBearer",
    "Angelic Channeling": [
        "Angelic Channeling (044A)",
        "Angelic Channeling (044B)",
    ],
    "Seraphic Legion's Descent": [
        "Seraphic Legion's Descent (139A)",
        "Seraphic Legion's Descent (139B)",
    ],
}

class PriceDB:
    def __init__(self, prices_folder, carddata):
        self.pricedata = {}
        self.carddata = carddata # pass card db from datalayer
        try:
            for entry in scandir(prices_folder):
                if entry.is_file() and entry.name[-5:] == ".json" and entry.name != "price-meta.json":
                    with open(entry) as f:
                        pricelist = json.load(f)
                    self.pricedata[entry.name[:-5]] = pricelist
        except FileNotFoundError:
            print("Didn't find cached price data")

        # try:
        #     with open(path.join(prices_folder, "price-meta.json")) as f:
        #         PRICE_META = json.load(f)
        # except FileNotFoundError:
        #     print("Didn't find price metadata")
        #     PRICE_META = {"Updated": "Never", "prefixes": []}
    
    def get_card_price(self, cardname, sub_prizes=False):
        """
        Return the price for the cheapest version of the given cardname,
        """
        if sub_prizes and cardname in PRIZE_EQUIVALENTS.keys():
            # Get the price of regular Spirit of Wind, for example, instead of Kaze
            cardname = PRIZE_EQUIVALENTS[cardname]
        card = self.carddata[cardname]
        fullname = fix_case(card["fullname"]) # For double-faced cards for example
        
        prices = []
        for ed in card["editions"]:
            prefix = ed["set"]["prefix"]
            if prefix == "PRXY":
                # Proxia's Vault cards are, by definition, free to proxy.
                # But let's return a nonzero price so it doesn't get
                # treated the same as None.
                return 0.001
            ed_price = self.low_price_by_edition(fullname, prefix)
            if ed_price:
                prices.append(ed_price)
        if prices:
            price = min(prices)
            return price

        #print(f"Couldn't get a price for {fullname}.")
        return None
    
    def get_formatted_price(self, cardname):
        """
        Get a card price as a string in the format of "$NN.NN",
        or an explanation like "Unavailable" or "N/A (Proxia's Vault)"
        """
        price = self.get_card_price(cardname)
        if price == 0.001:
            return f"N/A (Proxia's Vault)"
        elif price:
            return f"${price:.2f}"
        return "Unavailable"
    
    def low_price_by_edition(self, fullname, prefix):
        """
        Check card listings from TCGP, including multiple listings that have
        different names due to art variants, editions, or other inconsistencies.
        Return lowest price of any matched card.
        """
        if fullname in TCGP_CARDNAMES.keys():
            if type(TCGP_CARDNAMES[fullname]) == list:
                tcgp_names = TCGP_CARDNAMES[fullname]
            else:
                tcgp_names = [TCGP_CARDNAMES[fullname]]
        else:
            tcgp_names = [fullname]

        low_price = None
        if prefix in TCG_ABBR.keys():
            for abbr in TCG_ABBR[prefix]:
                for item in self.pricedata[abbr].values():
                    if item.get("name") in tcgp_names:
                        new_price = self.low_price_for_product(item)
                        if not new_price: # could be None for no listings
                            continue
                        if not low_price or new_price < low_price:
                            low_price = new_price
        elif prefix not in self.pricedata.keys():
            print(f"No tcgp data for set '{prefix}'")
        else: # Prefix should match
            for item in self.pricedata[prefix].values():
                trimmed_name = re.sub(r"\(\w+\)", "", item.get("name","")).strip()
                if trimmed_name in tcgp_names:
                    new_price = self.low_price_for_product(item)
                    if not new_price: # could be None for no listings
                        continue
                    if not low_price or new_price < low_price:
                        low_price = new_price
        return low_price

    def low_price_for_product(self, item):
        # May have multiple price listings, like foil vs nonfoil
        all_prices = [p["lowPrice"] for p in item["prices"] if p.get("lowPrice")]
        if not all_prices:
            # No price data, maybe no listings
            return None
        return min(all_prices)
    
    def __getitem__(self, item):
        return self.get_formatted_price(item)
