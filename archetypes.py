from collections import defaultdict

from shared import ElementStats, ChampStats
from datalayer import get_card_img, carddata
from cards import LV0, LV1, LV2, LV3

EXCLUDE_LIST = LV0+LV1+LV2+LV3#+[
#     "Grand Crusader's Ring",
#     "Quicksilver Grail",
#     "Dungeon Guide",
# ]
def card_freq_exclude(cardname):
    if cardname in EXCLUDE_LIST:
        return True
    return False

class Archetype:
    def __init__(self, name, require_cards, exclude_cards=[], require_element=None, shortname=None):
        self.name = name
        self.require = require_cards
        self.exclude = exclude_cards
        if shortname:
            self.shortname = shortname
        else:
            self.shortname = name
        self.require_element = require_element
        self.earliest = None

        # TODO: 
        # record card frequency stats
        self.matched_decks = []
    
    def match(self, deck):
        """
        To be called on a Deck instance that has already
        had deck.els populated by find_elements().
        Returns True if the deck matches this archetype and False otherwise.
        """
        if self.require_element and self.require_element not in deck.els:
            return False
        found_cards = 0
        for cardname in deck:
            if cardname in self.exclude:
                return False
            
            if cardname in self.require:
                # Keep looking in case an exclude card comes later
                found_cards += 1
        
        # TODO: consider using "found_cards" count for better matching
        if found_cards:
            self.matched_decks.append(deck)
            return True
        return False
    
    def analyze(self):
        self.matched_decks.sort(key=lambda d: d.entrant.evt_time, reverse=True)
        if self.matched_decks:
            self.earliest = self.matched_decks[-1].date
        
        self.elements = ElementStats()
        self.champdata = ChampStats()
        wins = 0
        matches = 0
        for d in self.matched_decks:
            self.elements.add_deck(d)
            self.champdata.add_deck(d)
            wins += d.entrant.wins
            wins += d.entrant.ties/2
            matches += d.entrant.wins+d.entrant.losses+d.entrant.ties
        
        if matches:
            self.winrate = round(100*wins/matches, 1)
        
        self.analyze_card_freq()
        self.analyze_card_stats()
        
    def analyze_card_freq(self):
        card_freq = defaultdict(int)
        for deck in self.matched_decks:
            for cardname in deck:
                if not card_freq_exclude(cardname):
                    card_freq[cardname] += 1
                else:
                    #print("excluding", cardname)
                    pass
        cf_sorted = list(card_freq.items())
        cf_sorted.sort(key=lambda x:x[1], reverse=True)
        total_decks = len(self.matched_decks)
        self.card_freq = {
            c: {
                "card": c,
                "pct": round(100*f/total_decks, 1),
                "img": get_card_img(c)
            } for c,f in cf_sorted
        }
    
    def analyze_card_stats(self):
        total_decks = 0
        total_floating = 0
        total_of_type = defaultdict(int)
        for deck in self.matched_decks:
            # floating = 0
            # allies = 0
            # for cardname in deck:
            #     card = carddata.get(cardname, None)
            #     if not card:
            #         print("No data saved for card:", cardname)
            #         continue
            #     card_quantity = deck.quantity_of(cardname)
            #     if is_floating(card):
            #         floating += card_quantity
            #     card_types = card["types"]
            #     if "ALLY" in card_types:
            #         allies += card_quantity
            # print("This deck has", floating, "floating memory.")
            total_decks += 1
            total_floating += deck.floating
            for k,v in deck.card_types.items():
                total_of_type[k] += v
        # print("Average floating memory for", self.name, "decks:", (total_floating/total_decks))
        self.average_floating = round(total_floating / total_decks, 0)
        total_of_type_sorted = [(k,v) for k,v in total_of_type.items()]
        total_of_type_sorted.sort(key=lambda x:x[1], reverse=True)
        self.average_of_type = {k: round(v / total_decks, 0) for k,v in total_of_type_sorted}
        
    

ARCHETYPES = {}
def add_archetype(*args,**kwargs):
    a = Archetype(*args, **kwargs)
    ARCHETYPES[a.name] = a


add_archetype(
    "Water Allies",
    [
        "Gildas, Chronicler of Aesa",
        "Lurking Assailant",
        "Esteemed Knight",
        "Trained Sharpshooter",
        "Corhazi Trapper",
    ],
    exclude_cards=[
        "Spirit Blade: Ensoul",
    ],
    require_element="Water",
    shortname="Allies"
)

add_archetype(
    "Wind Allies",
    [
        "Gildas, Chronicler of Aesa",
        "Aesan Protector",
        "Inspiring Call",
        "Woodland Squirrels",
        "Lurking Assailant",
        "Esteemed Knight",
        "Trained Sharpshooter",
        "Vigilant Sentry",
        "Shimmercloak Assassin",
    ],
    exclude_cards=[
        "Spirit Blade: Ascension",
        "Shadowstrike",
        "Storm Slime",
        "Baby Gray Slime",
    ],
    require_element="Wind",
    shortname="Allies"
)

add_archetype(
    "Fire Aggro",
    [
        "Arthur, Young Heir",
        "Rococo, Explosive Maven",
        "Hone by Fire",
    ],
    require_element="Fire",
    shortname="Aggro"
)

add_archetype(
    "Astra",
    [
        "Cosmic Bolt",
        "Cometfall",
        "Astra Sight",
        "Spellshield: Astra",
        "Astral Seal",
        "Prima Materia",
        "Astromech Attendant",
    ]
)

add_archetype(
    "Ensoul",
    ["Spirit Blade: Ensoul"]
)

add_archetype(
    "Umbra Ranger",
    [
        "Carter, Synthetic Reaper",
        "Mindbreak Bullet",
        "Umbral Tithe",
    ],
    shortname="Umbra"
)

add_archetype(
    "Luxem",
    [
        "Luxera's Map",
        "Insignia of the Corhazi",
        "Luxem Sight",
        "Lightweaver's Assault",
    ]
)

add_archetype(
    "Erupting",
    ["Erupting Rhapsody"]
)

add_archetype(
    "Mill",
    [
        "Magebane Lash",
        "Ravishing Finale",
    ]
)

add_archetype(
    "Arcane",
    [
        "Rai, Storm Seer",
        "Arcane Blast",
        "Advent of the Stormcaller",
        "Erratic Bolt",
        "Voltaic Sphere",
        "Spellshield: Arcane",
    ]
)

add_archetype(
    "Slimes",
    [
        "Storm Slime",
        "Ethereal Slime",
    ]
)

add_archetype(
    "Crux",
    [
        "The Majestic Spirit",
        "Prismatic Edge",
        "Ghosts of Pendragon",
        "Spirit Blade Ascension",
    ]
)

add_archetype(
    "Shadowstrike",
    [
        "Shadowstrike",
    ]
)

add_archetype(
    "Neos",
    [
        "Atmos Armor Type-Ares",
        "Cordelia, Aurous Kaiser",
        "Summon Sentinels",
        "Assemble the Ancients",
        "Blade of Creation",
        "Smash with Obelisk",
        "Amorphous Strike",
    ]
)

# Keep an eye on if Tera and non-Tera beasts should stay together.
add_archetype(
    "Beast",
    [
        "Geldus, Terror of Dorumegia",
        "Capricious Lynx",
        "Tempest Silverback",
        "Kraal, Stonescale Tyrant",
        "Vertus, Gaia's Roar",
    ],
    exclude_cards=[
        "Fireball",
        "Spirit Blade: Ascension",
        "Storm Slime",
        "Ethereal Slime",
    ]
)

add_archetype(
    "Overlord",
    ["Overlord Mk III"]
)

add_archetype(
    "Domains",
    [
        "Wayfinder's Map",
        "The Eternal Kingdom",
    ]
)

add_archetype(
    "Exia",
    [
        "Enrage",
        "Relentless Outburst",
        "Exia Sight",
        "Mend Flesh",
        "Proof of Life",
        "Seize Fate",
    ]
)

add_archetype(
    "Tera Mage",
    [
        "Leeching Bolt",
        "Yudi, Gossamer Jade",
        "Ruinous Pillars of Qidao",
        "Semiternal Sage",
        "Spellshield: Tera",
        "Conduit of Seasons",
        "Sempiternal Sage",
    ],
    exclude_cards=[
        "Silvie, Loved by All",
        "Silvie, Earth's Tune",
        "Silvie, Slime Sovereign",
    ],
    shortname = "Tera",
)
