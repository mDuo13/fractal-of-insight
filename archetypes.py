from collections import defaultdict
from bisect import insort

from config import SharedConfig
from shared import ElementStats, ChampStats, lineage
from datalayer import get_card_img, carddata

SIMILAR_DECKS_CUTOFF = 85

def card_freq_exclude(cardname):
    card = carddata[cardname]
    if "CHAMPION" in card.get("types",[]):
        return True
    return False

SUBTYPES = {}

class Archetype:
    def __init__(self, name, require_cards, exclude_cards=[],
                require_types={},
                require_element=None, shortname=None):
        self.name = name
        self.require = require_cards
        self.exclude = exclude_cards
        self.require_types = require_types
        if shortname is not None:
            self.shortname = shortname
        else:
            self.shortname = name
        self.require_element = require_element
        self.earliest = None
        self.subtypes = []
        self.champ_subtypes = {}
        self.el_subtypes = {}
        self.subtype_of = None

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
        
        for t,tcount in self.require_types.items():
            if t in deck.card_types.keys() and deck.card_types[t] < tcount:
                return False

        if found_cards:
            self.add_match(deck)
            return True

        return False

    def add_match(self, deck):
        if not SharedConfig.go_fast and not self.subtype_of:
            for d in self.matched_decks:
                sim = deck.similarity_to(d)
                if sim >= SIMILAR_DECKS_CUTOFF:
                    if d in [d2[0] for d2 in deck.similar_decks]:
                        # Already matched, probably via a different overlapping archetype
                        continue
                    #print(f"Similarity: {sim}% ({deck.entrant} {deck.date} vs {d.entrant} {d.date})")
                    # if (d in [x[1] for x in deck.similar_decks]):
                    #     print(f"Inserting duplicate similar_deck?? {d} vs {deck}")
                    #     exit(1)
                    insort(deck.similar_decks, [d, sim], key=lambda x:x[0].date)
                    #deck.similar_decks.append([d, sim])
                    insort(d.similar_decks, [deck, sim], key=lambda x:x[0].date)
                    #d.similar_decks.append([deck, sim])
        self.matched_decks.append(deck)

        for lineage in deck.lineages:
            if lineage not in self.champ_subtypes.keys():
                self.champ_subtypes[lineage] = Champtype(lineage, self)
            self.champ_subtypes[lineage].matched_decks.append(deck)
        
        for deck_el in deck.els:
            if deck_el not in self.el_subtypes.keys():
                self.el_subtypes[deck_el] = Eltype(deck_el, self)
            self.el_subtypes[deck_el].matched_decks.append(deck)

    
    def analyze(self):
        self.matched_decks.sort(key=lambda d: d.entrant.evt_time *1000 + 9999-d.entrant.placement, reverse=True)
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
        if self.subtypes:
            self.subtypes.sort(key=lambda x: len(x.matched_decks), reverse=True)
            for st in self.subtypes:
                st.analyze()

        if self.champ_subtypes:
            sorted_subtypes = [(k,v) for k,v in self.champ_subtypes.items()]
            sorted_subtypes.sort(key=lambda x: len(x[1].matched_decks), reverse=True)
            self.champ_subtypes = {k:v for k,v in sorted_subtypes}
            for ct in self.champ_subtypes.values():
                ct.analyze()

        if self.el_subtypes:
            sorted_subtypes = [(k,v) for k,v in self.el_subtypes.items()]
            sorted_subtypes.sort(key=lambda x: len(x[1].matched_decks), reverse=True)
            self.el_subtypes = {k:v for k,v in sorted_subtypes}
            for et in self.el_subtypes.values():
                et.analyze()
        
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
        if total_decks == 0:
            raise ZeroDivisionError(f"No decks for archetype {self.name}")
        self.average_floating = round(total_floating / total_decks, 0)
        total_of_type_sorted = [(k,v) for k,v in total_of_type.items()]
        total_of_type_sorted.sort(key=lambda x:x[1], reverse=True)
        self.average_of_type = {k: round(v / total_decks, 0) for k,v in total_of_type_sorted}

    def add_subtype(self, *args, **kwargs):
        st = Archetype(*args, **kwargs)
        self.subtypes.append(st)
        st.subtype_of = self
        SUBTYPES[st.name] = st

class Champtype(Archetype):
    def __init__(self, lineage, parent):
        self.name = lineage
        self.shortname = lineage
        self.earliest = None
        self.subtypes = []
        self.subtype_of = parent
        self.matched_decks = []

        self.champ_subtypes = None
        self.require_element = None
        self.el_subtypes = None

    # def match(self, deck):
    #     for card_o in deck.dl["material"]:
    #         cardname = card_o["card"]
    #         card = carddata[cardname]
    #         if "CHAMPION" in card.get("types",[]):
    #             card_lineage = lineage(cardname)
    #             if card_lineage == self.name:
    #                 self.matched_decks.append(deck)
    #                 return True
    #     return False

class Eltype(Archetype):
    def __init__(self, el, parent):
        self.name = el
        self.shortname = el
        self.require_element = el
        self.subtypes = []
        self.subtype_of = parent
        self.matched_decks = []
        self.champ_subtypes = None
        self.el_subtypes = None

ARCHETYPES = {}
def add_archetype(*args,**kwargs):
    a = Archetype(*args, **kwargs)
    ARCHETYPES[a.name] = a
    return a

NO_ARCHETYPE  = Archetype(
    "Rogue Decks",
    [],
    shortname=""
)

water_allies = add_archetype(
    "Water Allies",
    [
        "Gildas, Chronicler of Aesa",
        "Lurking Assailant",
        "Esteemed Knight",
        "Trained Sharpshooter",
        "Corhazi Trapper",
        "Halocline Scout",
        "Sword Saint of Eventide",
        "Lunete, Frostbinder Priest",
        "Jueying, Shadowmare",
    ],
    exclude_cards=[
        "Spirit Blade: Ensoul",
        "Dawn of Ashes",
    ],
    require_types={
        "ALLY": 20
    },
    require_element="Water",
    shortname="Allies"
)

water_allies.add_subtype(
    "Water Unique Allies",
    [
        "Jueying, Shadowmare"
    ],
    require_types={
        "UNIQUE": 12
    },
    shortname="Unique"
)

wind_allies = add_archetype(
    "Wind Allies",
    [
        "Gildas, Chronicler of Aesa",
        "Inspiring Call",
        "Woodland Squirrels",
        "Lurking Assailant",
        "Esteemed Knight",
        "Trained Sharpshooter",
        "Vigilant Sentry",
        "Shimmercloak Assassin",
        "Dilu, Auspicious Charger",
        "Oath of the Sakura",
        "Guan Yu, Prime Exemplar",
        "Liu Bei, Oathkeeper",
    ],
    exclude_cards=[
        "Spirit Blade: Ascension",
        "Shadowstrike",
        "Storm Slime",
        "Wildgrowth Feline",
        "Dawn of Ashes",
    ],
    require_types={
        "ALLY": 22
    },
    require_element="Wind",
    shortname="Allies"
)

wind_allies.add_subtype(
    "Unique Wind Allies",
    [
        "Mortal Ambition",
        "Dilu, Auspicious Charger",
    ],
    shortname="Unique"
)
wind_allies.add_subtype(
    "Robo Wind Allies",
    [
        "Manufacture Cell",
    ],
    shortname="Robo",
)
wind_allies.add_subtype(
    "Balance Wind Allies",
    [
        "Gildas, Chronicler of Aesa"
    ],
    exclude_cards=[
        "Dilu, Auspicious Charger",
    ],
    shortname="Balance",
)

add_archetype(
    "Fire Aggro",
    [
        "Arthur, Young Heir",
        "Rococo, Explosive Maven",
        "Hone by Fire",
        "Fang of Dragon's Breath",
        "Flamewing Fowl",
        "Heated Vengeance",
        "Rending Flames",
        "Blazing Bowman",
    ],
    require_element="Fire",
    shortname="Aggro",
    exclude_cards=[
        "Vanitas, Obliviate Schemer",
        "Relentless Outburst",
        "Ghosts of Pendragon",
        "Dungeon Guide",
    ]
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
        "False Step",
        "Gloamspire Wraith",
    ],
    shortname="Umbra"
)

add_archetype(
    "Luxem Assassin",
    [
        "Lightweaver's Assault",
        "Luxera's Map",
        "Insignia of the Corhazi",
        "Thousand Refractions",
        "Gleaming Cut",
    ],
    exclude_cards=[
        "Guo Jia, Heaven's Favored"
    ],
    shortname="Luxem"
)

add_archetype(
    "Erupting",
    ["Erupting Rhapsody"]
)

add_archetype(
    "Ravishing Mill",
    [
        "Ravishing Finale",
    ],
    shortname="Mill"
)

add_archetype(
    "Penguin Mill",
    [
        "Fractal of Polar Depths",
    ],
    exclude_cards=[
        "Ravishing Finale",
    ],
    shortname="Mill"
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

slimes = add_archetype(
    "Slimes",
    [
        "Storm Slime",
        "Ethereal Slime",
    ]
)

add_archetype(
    "Slice & Dice",
    [
        "Slice and Dice",
    ],
    exclude_cards=[
        "Shadowstrike",
        "Corhazi Trapper",
        "Lightweaver's Assault",
    ]
)

crux = add_archetype(
    "Crux",
    [
        "The Majestic Spirit",
        "Prismatic Edge",
        "Ghosts of Pendragon",
        "Spirit Blade: Ascension",
    ],
    exclude_cards=[
        "Rai, Mana Weaver"
    ]
)
crux.add_subtype(
    "Prismatic Fire Crux",
    [
        "Favorable Winds",
        "Scatter Essence",
        "Repelling Palmblast",
        "Potion Infusion: Seal",
        "Freezing Steel",
        "Chilling Touch",
        "Fracturize",
        "Rising Tides",
        "Refracting Missile",
        "Primordial Ritual",
        "Lost in Thought",
    ],
    require_element="Fire",
    shortname="Prismatic",
)

crux.add_subtype(
    "Wind Crux Humans",
    [
        "Phalanx Captain",
        "Rally the Peasants",
    ],
    require_element="Wind",
    shortname="Humans",
)

shadowstrike = add_archetype(
    "Shadowstrike",
    [
        "Shadowstrike",
    ]
)
shadowstrike.add_subtype(
    "Waltz",
    [
        "Penumbral Waltz",
    ]
)
shadowstrike.add_subtype(
    "Outlook",
    [
        "Corhazi Outlook"
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
    ],
    exclude_cards=[
        "Fireball",
        "Spirit Blade: Ascension",
        "Storm Slime",
        "Ethereal Slime",
    ]
)

add_archetype(
    "Tera Tamer",
    [
        "Artificer's Opus",
        "Kraal, Stonescale Tyrant",
        "Vertus, Gaia's Roar",
        "Arima, Gaia's Wings",
    ],
    exclude_cards=[
        "Kongming, Fel Eidolon",
        "Diao Chan, Idyll Corsage",
    ],
    shortname="Tera"
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
        "Diao Chan, Idyll Corsage",
    ],
    shortname = "Tera",
)

add_archetype(
    "Razorgale",
    [
        "Razorgale Calling",
    ],
)

add_archetype(
    "Cats",
    [
        "Wildgrowth Feline",
        "Tempus Stalker",
    ]
)

add_archetype(
    "Dahlia",
    [
        "Dahlia, Idyllic Dreamer"
    ]
)

add_archetype(
    "Fractal",
    [
        "Burst Asunder",
        "Shimmering Refraction",
    ],
    exclude_cards=[
        "Dungeon Guide",
        "Strategem of Myriad Ice",
        "Firebloom Flourish",
    ]
)
add_archetype(
    "Luxem Tamer",
    [
        "Felicitous Flock",
        "Fatestone of Heaven",
        "Excalibur, Cleansing Light",
        "Glorious Presence",
        "Sunblessed Gazelle",
    ],
    exclude_cards=[
        "Zander, Blinding Steel",
        "Zander, Corhazi's Chosen",
        "Tonoris, Genesis Aegis",
    ],
    shortname="Luxem",
)

add_archetype(
    "Seiryuu",
    [
        "Fabled Azurite Fatestone"
    ]
)
add_archetype(
    "Genbu",
    [
        "Fabled Sapphire Fatestone"
    ]
)
add_archetype(
    "Byakko",
    [
        "Fabled Emerald Fatestone"
    ]
)
add_archetype(
    "Suzaku",
    [
        "Fabled Ruby Fatestone"
    ]
)

add_archetype(
    "Tera Cleric",
    [
        "Diao Chan, Idyll Corsage",
        "Season's End",
        "Bloom: Winter's Chill",
        "Maiden of Primal Virtue",
    ],
    shortname="Tera",
)

# Turns out Rebuke is a more distinctive indicator than Firebloom.
add_archetype(
    "Rebuke",
    [
        "Searing Rebuke",
    ]
)

add_archetype(
    "Dawn of Ashes",
    [
        "Dawn of Ashes",
    ]
)
