from collections import defaultdict

from datalayer import get_card_img

class Achievement:
    def __init__(self, name, emoji, description, skip_date=False, 
                 refracted=False, image="", notes="", artist="", artisturl=""):
        self.name = name
        self.emoji = emoji
        self.description = description
        self.skip_date = skip_date
        self.refracted = refracted
        self.img = image
        self.notes = notes
        self.artist = artist
        self.artisturl = artisturl

ACHIEVEMENTS = {}
def add_achievement(name, emoji, description, skip_date=False):
    a = Achievement(name, emoji, description, skip_date)
    ACHIEVEMENTS[name] = a

def add_refracted(name, description, image="", notes="", artist="", artisturl=""):
    if image:
        image = "/static/refracted/"+image
        emoji = ""
    else:
        emoji = "🚧"
    a = Achievement(name, emoji, description, refracted=True, image=image,
                    notes=notes, artist=artist, artisturl=artisturl)
    ACHIEVEMENTS[name] = a

class GlobalAchievementStats:
    def __init__(self):
        self.count_achieved = defaultdict(int)
        self.first_achieved = {}
        self.achieved_by = defaultdict(list) # list of (entrant,achievement) pairs
        self.total_players = 0 # Update this before calling for_achievement

    def achieve(self, achieved, entrant):
        aname = achieved.name
        self.count_achieved[aname] += 1
        if aname in self.first_achieved.keys():
            if achieved.date and achieved.date < self.first_achieved[aname].date:
                self.first_achieved[aname] = achieved
        else:
            self.first_achieved[aname] = achieved
        self.achieved_by[aname].append((entrant, achieved))

    def __getitem__(self, aname):
        rate = round(100 * self.count_achieved[aname] / self.total_players, 1)
        players = self.achieved_by[aname]
        players.sort(key=lambda x:x[0].event.date, reverse=True)
        if aname not in self.first_achieved.keys():
            print("Unachieved achievement:", aname)
            first = None
        else:
            first = self.first_achieved[aname].entrant
        return {
            "count": self.count_achieved[aname],
            "first": first,
            "rate": rate,
            "players": players
        }
GAS = GlobalAchievementStats()

class Achieved:
    def __init__(self, achievement_name, emoji, description, entrant, details="", skip_date=False, refracted=False):
        self.name = achievement_name
        self.emoji = emoji
        self.description = description
        if entrant:
            self.event = entrant.event
            self.entrant = entrant
        else:
            self.entrant = None
        if skip_date:
            self.date = ""
        else:
            self.date = entrant.event.date
        self.details = details
        if refracted:
            self.atype = "refracted"
            # TODO: add automatic image for refracted achievements?
        else:
            self.atype = "normal"

    @classmethod
    def from_template(cls, achievement_name, entrant, details=""):
        emoji = ACHIEVEMENTS[achievement_name].emoji
        description = ACHIEVEMENTS[achievement_name].description
        skip_date = ACHIEVEMENTS[achievement_name].skip_date
        refracted = ACHIEVEMENTS[achievement_name].refracted
        self = cls(achievement_name, emoji, description, entrant, details=details, skip_date=skip_date, refracted=refracted)
        if ACHIEVEMENTS[achievement_name].img:
            self.img = ACHIEVEMENTS[achievement_name].img
        if ACHIEVEMENTS[achievement_name].artist:
            self.artist = ACHIEVEMENTS[achievement_name].artist
        if ACHIEVEMENTS[achievement_name].artisturl:
            self.artisturl = ACHIEVEMENTS[achievement_name].artisturl
        return self

    @classmethod
    def card_first(cls, cardname, entrant):
        name = f"First Play: {cardname}"
        emoji = ""
        description = cardname
        self = cls(name, emoji, description, entrant)
        self.img = get_card_img(cardname)
        self.shortname = "First Play"
        self.atype = "first"
        return self

    @classmethod
    def card_top_user(cls, cardname, score, rank):
        name = f"Top {rank} User: {cardname}"
        emoji = ""
        description = cardname
        details = f"Score: {score}"
        self = cls(name, emoji, description, None, details=details, skip_date=True)
        self.img = get_card_img(cardname)
        self.atype = "top"
        self.shortname = f"#{rank} Wielder"
        return self


class AchievementSet:
    def __init__(self):
        self.achieved = {}

    def add(self, achievement_name, entrant, details=""):
        if achievement_name in self.achieved.keys():
            return
        a = Achieved.from_template(
            achievement_name,
            entrant,
            details=details
        )
        self.achieved[a.name] = a
        GAS.achieve(a, entrant)

    def add_card_first(self, cardname, entrant):
        # Maybe check for duplicate firsts here? Shouldn't be needed though
        a = Achieved.card_first(cardname, entrant)
        self.achieved[a.name] = a

    def add_card_top(self, cardname, score, rank):
        a = Achieved.card_top_user(cardname, score, rank)
        self.achieved[a.name] = a

    def __iter__(self):
        for a in self.achieved.values():
            yield a

# Entering/Winning Event Types
add_achievement("Just Chillin'", "🧊", "Enter a Regular event.")
add_achievement("Big Chillin'", "☃️", "Win a Regular event with 40+ entrants.")
add_achievement("Throw Down", "🏟", "Enter a Store Championship.")
add_achievement("This Is My House", "🏠", "Win a Store Championship.")
add_achievement("Turf Warrior", "🗺", "Enter a Regionals event.")
add_achievement("King of the Hill", "⛰", "Win a Regionals event.")
add_achievement("Join the Battle", "✉️", "Enter a Nationals event.")
add_achievement("Hometown Hero", "🏁", "Win a Nationals event.")
add_achievement("Mountain Climber", "🌄", "Enter an Ascent.")
add_achievement("Spirited Competitor", "🌟",  "Make top cut of an Ascent.")
add_achievement("View from the Top", "🏔", "Win an Ascent.")
add_achievement("World-Class Competitor", "🏅", "Enter a Worlds event.")
add_achievement("Ascendant", "🌞", "Win a Worlds event.")

# Deck quirks
add_achievement("Antigravity", "🛰", "Play 30+ floating memory.")
add_achievement("Big Deck Energy", "💪", "Play over 60 cards in your main deck.")
add_achievement("Hybrid Theory", "🌓",  "Play a deck with a hybrid lineage.")
add_achievement("We Need Guns. Lots of Guns", "🔫", "Play a deck with 3+ guns.")

# Deck elements
add_achievement("Stormchaser", "⛈", "Play an Arcane deck.")
add_achievement("The Best at Space", "☄", "Play an Astra deck.")
add_achievement("Crux is Fine", "👌",  "Play a Crux deck.")
add_achievement("Too Angry to Die", "😡", "Play an Exia deck.")
add_achievement("Flashy", "🎇", "Play a Luxem deck.")
add_achievement("Is that Jimmy Le?", "🌆", "Play a Neos deck.")
add_achievement("One with Nature", "🌱", "Play a Tera deck.")
add_achievement("In the Shadows", "😈", "Play an Umbra deck.")


# Decklist similarity
add_achievement("Team Builder", "👬",  "Play the same list as another entrant in the same event.")
add_achievement("Runback", "🏃‍♀", "Play the exact same decklist again.")
add_achievement("I Made This", "🛠️", "Have someone play a list similar to yours.")

# Completionist
add_achievement("Classy", "🤵",  "Play all 7 classes.")
add_achievement("Elementalist", "🌦",  "Play 3+ basic elements.")
add_achievement("Four Seasons", "📆",  "Play in 4+ competitive seasons.")
add_achievement("Globetrotter", "🌏",  "Played in 3+ countries.")
add_achievement("Loyalist", "🐕",  "Play the same champion 5+ times.")
add_achievement("Nomad", "🐫", "Enter 2+ Regionals in one season.")
add_achievement("True Nomad", "🐪", "Enter 2+ in-person Regionals in one season.")

# Elo, etc.
## skip_date for some of these because the data is based on when I re-downloaded the event, not the player's stats at the time of the event.
add_achievement("Deadly Duelist", "⚜️", "Have 1400+ peak Elo.", skip_date=True)
add_achievement("Demigod", "😇", "Have 1600+ peak Elo.", skip_date=True)
add_achievement("Ladder Leaper", "🪜",  "Gain 50+ Elo from one event.")
add_achievement("Capped Veteran", "🧢", "Have 800+ Veterancy Points.", skip_date=True)
add_achievement("Titan Slayer", "😲", "Win in an upset.")
add_achievement("Attack and Dethrone God", "👹", "Defeat a player with 1600+ Elo.")

# Match details
add_achievement("Hand Shaker", "🤝",  "Take an intentional draw.")
add_achievement("Play the Long Game", "⌛️",  "Win 1-0 in a best-of-3.")
add_achievement("Technically Undefeated", "☝️", "Finish with no losses but 2+ draws.")
add_achievement("We Meet Again", "♻️",  "Face the same opponent again in one event.")
add_achievement("Movie Star", "🎥", "Play an on-stream match.")

# Judging
add_achievement("JUDGE!", "⚖️", "Judge an event.")
add_achievement("Juuuuuuudge!", "🗯", "Judge a 7+ round event.")
add_achievement("Wisdom of the Mountain", "🦉", "Judge an Ascent.")

# Refracted Achievements -------------------------------------------------------
MIIU_URL = "https://vgen.co/Miiuchuu"
add_refracted("Look, Two Hands", "Have 14+ influence.", 
    image="look-two-hands.png",
    artist="Miiu", artisturl=MIIU_URL,
    notes="Must be counted when state-based effects are checked. For example, it wouldn't count if Creative Shock draws you to 14 and discards down to 13.")
add_refracted("One Punch!", "Deal 25+ combat damage in one attack.", 
    image="one-punch.png",
    artist="Miiu", artisturl=MIIU_URL,
    notes="Damage can be dealt to a champion or an ally. Generally still counts if opponent concedes as attack is being declared.")
add_refracted("Perfect Quartet", "Control 4 non-tokens with the same name.", 
    image="perfect-quartet.png",
    artist="Miiu", artisturl=MIIU_URL,
    notes="Must be objects on the field. Generally, the player has their entire playset of a card in play.")
add_refracted("Guidance Angel", "Make Triskit, Guidance Angel your champion.", 
    image="guidance-angel.png",
    artist="Miiu", artisturl=MIIU_URL,
    )
add_refracted("Wrath Incarnate", "Make Lu Bu, Wrath Incarnate your champion.", 
    image="wrath-incarnate.png",
    artist="Miiu", artisturl=MIIU_URL,
    )
add_refracted("White Tiger", "Transform Fabled Emerald Fatestone.", 
    image="white-tiger.png",
    artist="Miiu", artisturl=MIIU_URL,
    )
add_refracted("Bloodmonger", "Draw 3 cards with Zhang Liao, Bloodmonger's effect.", 
    image="bloodmonger.png",
    artist="Miiu", artisturl=MIIU_URL,
    )
add_refracted("Muda muda muda", "Attack 3+ times with the same unit in one turn.", notes="It's OK if the attacks never finished—for example, due to Song of Frost.")
add_refracted("In Resonance", "Get the Harmonize effect of a card.")
add_refracted("Trace...on!", "Control 2+ token Weapons.")
add_refracted("A Bouquet, for You", "Make your opponent summon 3+ Flower tokens.", notes="Typically achieved by resolving Bloom: Summer's Glow, Bloom: Winter's Chill, or Bloom: Autumn's Fall while an opponent has 3 or more Flowerbud tokens.")
add_refracted("Leap Through Time", "Cause time to be distorted.", notes="Achieved by resolving Chronowarp.")
add_refracted("The Infinite Stars", "Play Scry the Stars during The Elysian Astrolabe's effect.", notes="After resolving The Elysian Astrolabe's activated ability, Scry the Stars lets you play your whole deck by starcalling indefinitely. Generally still counts if opponent concedes as the player is about to activate Scry the Stars.")
add_refracted("El Scry Congroo", "Glimpse 10+.", 
    image="el-scry-congroo.png",
    artist="Miiu", artisturl=MIIU_URL,
    )
add_refracted("Restart from Zero", "Play a game that ends in a draw before time is up.", notes="For example, both champions died at the same time due to retaliation in combat.")
add_refracted("Pretty Derby", "Get the Equestrian effect of a card.", notes="For static effects like Horse Archer or War Marshal, only counts if it affects the game state.")
add_refracted("Atelier", "Brew a card.", notes="Aside from potions, Hide in Bush and Prima Materia also count.")
add_refracted("Crit!", "Do double damage with a Critical attack.", notes="Coup de Grace, Bushwack Bandit, and Corhazi Lightblade are cards that can have the Critical keyword. Not awarded if the opponent chooses to discard to the Critical effect.")
add_refracted("Trojan Horse", "Control a token Majestic Spirit.", 
    image="trojan-horse.png",
    artist="Miiu", artisturl=MIIU_URL,
    notes="For example, one created using Duplicitous Replication.")
add_refracted("Elite Four", "Attack with an ally that has Pride 4+.",
    image="elite-four.png",
    artist="Miiu", artisturl=MIIU_URL,
    notes="Causing the ally to lose Pride does not count.")

REFRACTED_ARTISTS = {}
for a in ACHIEVEMENTS.values():
    if a.refracted and a.artist:
        REFRACTED_ARTISTS[a.artist] = a.artisturl
