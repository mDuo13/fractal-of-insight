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

        # TODO: save instances of archetype,
        # track and record them;
        # record card frequency stats
    
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
            return True
        return False

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
        "Shadow's Twin"
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
