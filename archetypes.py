from collections import defaultdict
from bisect import insort
from logging import warning

from config import SharedConfig
from shared import ElementStats, ChampStats, lineage
from cards import BANLIST, REMOVED_FROM_PRXY
from datalayer import get_card_img, carddata, get_card_price

SIMILAR_DECKS_CUTOFF = 85
MAT_DIFF_CARD_LIMIT = 12
MAIN_DIFF_CARD_LIMIT = 15
SIDE_DIFF_CARD_LIMIT = 8
MONEY_CARD_COUNT = 20
MONEY_CARD_PRICE_CUTOFF = 5.00 # Only include cards that cost at least $ this
SUBTYPES = {}

class Archetype:
    def __init__(self, name, require_cards, exclude_cards=[],
                require_types={}, require_combos=[],
                require_element=None, shortname=None):
        self.name = name
        self.require = require_cards
        self.exclude = exclude_cards
        self.require_types = require_types
        self.require_combos = require_combos
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
            if tcount > 0:
                if t not in deck.card_types.keys() or deck.card_types[t] < tcount:
                    return False
            if tcount < 0: # negative require_types means it's a maximum
                if t in deck.card_types.keys() and deck.card_types[t] > abs(tcount):
                    return False

        if self.require_combos:
            combo_found = False
            for combo in self.require_combos:
                combopieces_found = []
                for cardname in deck:
                    if cardname in combo and cardname not in combopieces_found:
                        combopieces_found.append(cardname)
                        if len(combopieces_found) == len(combo):
                            combo_found = True
                            break
                if combo_found:
                    break
            if not combo_found:
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
            self.total_matches = matches

        self.analyze_card_freq()
        self.analyze_card_stats()
        self.analyze_money_cards()
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
        card_freqs = {
            "mat": defaultdict(int),
            "main": defaultdict(int),
            "side": defaultdict(int)
        }
        card_etc = defaultdict(None)
        for deck in self.matched_decks:
            for card_o in deck.mat:
                card_freqs["mat"][card_o["card"]] += 1
            for card_o in deck.main:
                card_freqs["main"][card_o["card"]] += 1
            for card_o in deck.side:
                card_freqs["side"][card_o["card"]] += 1
        total_decks = len(self.matched_decks)
        self.card_freqs = {}
        for cf_type, card_freq in card_freqs.items():
            cf_sorted = list(card_freq.items())
            cf_sorted.sort(key=lambda x:x[1], reverse=True)
            self.card_freqs[cf_type] = {
                c: {
                    "card": c,
                    "pct": round(100*f/total_decks, 1),
                    "img": get_card_img(c),
                    "banned": (True if c in BANLIST else False),
                    "removed": (True if c in REMOVED_FROM_PRXY.keys() else False),
                } for c,f in cf_sorted
            }

    def analyze_card_stats(self):
        total_decks = 0
        total_floating = 0
        total_of_type = defaultdict(int)
        for deck in self.matched_decks:
            total_decks += 1
            total_floating += deck.floating
            for k,v in deck.card_types.items():
                total_of_type[k] += v
        if total_decks == 0:
            warning(f"No decks for archetype {self.name}")
            return
        self.average_floating = round(total_floating / total_decks, 0)
        total_of_type_sorted = [(k,v) for k,v in total_of_type.items()]
        total_of_type_sorted.sort(key=lambda x:x[1], reverse=True)
        self.average_of_type = {k: round(v / total_decks, 0) for k,v in total_of_type_sorted}

    def analyze_money_cards(self):
        money_cards = []
        for sect,limit in ( ("mat", MAT_DIFF_CARD_LIMIT),
                            ("main", MAIN_DIFF_CARD_LIMIT),
                            ("side", SIDE_DIFF_CARD_LIMIT) ):
            for cardname in list(self.card_freqs[sect].keys())[:limit]:
                price = get_card_price(cardname)
                if price:
                    money_cards.append( (cardname, price) )
        money_cards.sort(key=lambda x:x[1], reverse=True)
        self.money_cards = {}
        for cardname,price in money_cards[:MONEY_CARD_COUNT]:
            if price >= MONEY_CARD_PRICE_CUTOFF:
                self.money_cards[cardname] = {
                    "card": cardname,
                    "price": price,
                    "img": get_card_img(cardname)
                }


    def load_videos(self):
        videos = []
        for d in self.matched_decks:
            videos += d.videos
        self.videos = []
        for v in videos:
            if v not in self.videos:
                self.videos.append(v)
        self.videos.sort(key=lambda v:v["event"].date, reverse=True)

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

add_archetype(
    "Rile",
    [
        "Rile the Abyss",
    ]
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
        "Imperial Panzer",
        "Aquifer Seneschal",
        "Vigil Rempart",
        "Sablier Guard",
    ],
    exclude_cards=[
        "Spirit Blade: Ensoul",
        "Dawn of Ashes",
        "Fabled Sapphire Fatestone",
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
        "Liu Bei, Oathkeeper",
        "Imperial Panzer",
        "Unrelenting Warden",
        "Chrysalis, Hazy Caterpillar",
    ],
    exclude_cards=[
        "Spirit Blade: Ascension",
        "Shadowstrike",
        "Storm Slime",
        "Wildgrowth Feline",
        "Dawn of Ashes",
        "Seiryuu's Command",
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
        "Cinder Geyser",
        "Peppered Chef",
    ],
    require_element="Fire",
    shortname="Aggro",
    exclude_cards=[
        "Vanitas, Obliviate Schemer",
        "Relentless Outburst",
        "Ghosts of Pendragon",
        "Dungeon Guide",
        "Ashen Riffle", # Suited is its own category for now
    ]
)

add_archetype(
    "Astra Cleric",
    [
        "Cosmic Bolt",
        "Cometfall",
        "Astra Sight",
        "Spellshield: Astra",
        "Astral Seal",
        "Prima Materia",
        "Astromech Attendant",
    ],
    exclude_cards=[
        "Diana, Moonpiercer",
    ],
    shortname="Astra",
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
    exclude_cards=[
        "Ciel, Mirage's Grave"
    ],
    shortname="Umbra"
)

lwa = add_archetype(
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
lwa.add_subtype(
    "Serene",
    [
        "Spirit of Serene Fire",
        "Spirit of Serene Water",
        "Spirit of Serene Wind",
    ],
    shortname="",
)
lwa.add_subtype(
    "Non-Serene",
    [
        "Lightweaver's Assault",
        "Luxera's Map",
        "Insignia of the Corhazi",
        "Thousand Refractions",
        "Gleaming Cut",
    ],
    exclude_cards=[
        "Spirit of Serene Fire",
        "Spirit of Serene Water",
        "Spirit of Serene Wind",
    ],
    shortname="",
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
    exclude_cards=[
        "Guo Jia, Blessed Scion",
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
        "Guo Jia, Blessed Scion",
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
    ],
    exclude_cards=[
        "Baleful Oblation",
        "Guo Jia, Heaven's Favored",
    ]
)

add_archetype(
    "Slimes",
    [
        "Storm Slime",
        "Ethereal Slime",
    ],
    exclude_cards=[
        "Merlin, Kingslayer"
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

crux.add_subtype(
    "Ensoul",
    ["Spirit Blade: Ensoul"]
)

crux.add_subtype(
    "Sword Saint's Vow",
    ["Sword Saint's Vow"],
    shortname="Vow",
)

shadowstrike = add_archetype(
    "Shadowstrike",
    [
        "Shadowstrike",
    ]
)
shadowstrike.add_subtype(
    "Inspiring",
    [
        "Inspiring Call",
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
    ],
    exclude_cards=[
        "Beguiling Coup", # Aside: this doesn't even work the way you want it to
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
        "Bagua of Vital Demise",
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
        # "Excalibur, Cleansing Light", # Genbu decks with a couple Excaliburs for Nullifying Lantern shouldn't qualify as a different archetype
        "Glorious Presence",
        # "Sunblessed Gazelle", # Try to split these from Seiryuu decks
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
    ],
    exclude_cards=[
        "Rai, Archmage",
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

add_archetype(
    "Dawn of Ashes",
    [
        "Dawn of Ashes",
    ]
)

add_archetype(
    "Suited",
    [
        "Ashen Riffle",
        "Noire, Ace of Spades",
        "Rouge, Ace of Hearts",
        "Verita, Queen of Hearts",
    ]
)

umbra_guardian = add_archetype(
    "Umbra Guardian",
    [
        "Beguiling Coup",
        "Carter, Synthetic Reaper",
        "Extorting Blackjack",
        "Soutirer Vortex",
        "Ombreux Chevalier",
        "Baleful Oblation",
    ],
    exclude_cards=[
        "Diana, Duskstalker",
        "Diana, Cursebreaker",
    ],
    shortname="Umbra",
)

umbra_guardian.add_subtype(
    "Oblation",
    [
        "Baleful Oblation",
    ],
    require_combos=[
        [
            "Baleful Oblation",
            "Advent of the Stormcaller",
        ]
    ]
)

add_archetype(
    "Astra Ranger",
    [
        "Constellation's Blessing",
        "Guided Starlight",
        "Meteoric Volley",
        "Sidereal Spellshot",
        "Poised Occlusion",
    ],
    shortname="Astra",
)

aetherwing = add_archetype(
    "Aetherwing",
    [
        "Aetheric Calibration",
        "Drown in Aether",
        "Prudent Nock",
        "Undercurrent Vantage",
        "Charge the Soul",
        "Manabolt Convergence",
        "Blazing Cindercharge",
    ],
    require_types={
        "ACTION": 30,
    }
)
aetherwing.add_subtype(
    "Carpsong",
    [
        "Carpsong Coda"
    ]
)

add_archetype(
    "Wakeup Combo",
    [
        "Second Wind",
        "Rallied Advance",
        "Draught of Stamina",
    ],
    exclude_cards=[
        "Seiryuu's Command",
        "Incarnate Majesty",
    ],
    require_combos=[
        [
            "Mad Hatter, Morose Heritor",
            "Ranger Strides",
        ],
        [
            "Invective Instruction",
            "Second Wind",
        ],
        [
            "Ranger Strides",
            "Second Wind",
        ],
        [
            "Invigorating Concoction",
            "Draught of Stamina",
        ]
    ],
    # require_types={
    #     # Compared to "Wind Allies" decks, these decks run far fewer allies
    #     # and really try to combo off by making one tall ally and attacking
    #     # multiple times in one turn.
    #     "ALLY": -21
    # },
    shortname="Wakeup",
)

add_archetype(
    "Horse and Taxes",
    [
        "Vanitas, Dominus Rex",
    ],
    require_combos=[[
        "Dilu, Auspicious Charger",
        "Red Hare, Unrivaled Stallion",
        "Dungeon Guide",
    ]],
    require_element="Fire"
)

add_archetype(
    "Triskit",
    [
        "Triskit, Guidance Angel"
    ]
)
