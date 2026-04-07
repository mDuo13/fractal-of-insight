# Create a slugs json file for FRⱯCTL
import json

from fractal.datalayer import carddata
from fractal.cardstats import ALL_CARD_STATS
from main import PageBuilder

b = PageBuilder()
b.read_events()
for szn in b.seasons.values():
    szn.analyze()
ALL_CARD_STATS.analyze()
ALL_CARD_STATS.sort()

# Easy: top 100 most played cards
easy = [carddata[cn]["slug"] for cn,cs in ALL_CARD_STATS][:100]

# Medium: at least 1k appearances but not in Easy
med = [carddata[cn]["slug"] for cn,cs in ALL_CARD_STATS if cs.num_appearances >= 1000][100:]

# Hard: 100-1000 appearances or selected tokens
SELECTED_TOKENS = ["blightroot", "fraysia", "manaroot", "powercell", "razorvine", "silvershine", "springleaf", "ominous-shadow"]
hard = [carddata[cn]["slug"] for cn,cs in ALL_CARD_STATS if cs.num_appearances >= 100]
hard = [slug for slug in hard if slug not in med and slug not in easy]
hard += SELECTED_TOKENS

# Maniac: Everything else
maniac = [carddata[cn]["slug"] for cn,cs in ALL_CARD_STATS if cs.num_appearances < 100 and carddata[cn]["slug"] not in SELECTED_TOKENS]

slugs = {
    "easy": easy,
    "med": med,
    "hard": hard,
    "maniac": maniac,
}

with open("newslugs.json", "w", encoding="utf-8") as f:
    json.dump(slugs, f, indent=None)
