# Create a slugs json file for FRⱯCTL
import json

from main import PageBuilder

b = PageBuilder()

# Easy: top 100 most played cards
easy = [b.index[cn]["slug"] for cn,cs in b.cards][:100]

# Medium: at least 1k appearances but not in Easy
med = [b.index[cn]["slug"] for cn,cs in b.cards if cs.num_appearances >= 1000][100:]

# Hard: 100-1000 appearances or selected tokens
SELECTED_TOKENS = ["blightroot", "fraysia", "manaroot", "powercell", "razorvine", "silvershine", "springleaf", "ominous-shadow"]
hard = [b.index[cn]["slug"] for cn,cs in b.cards if cs.num_appearances >= 100]
hard = [slug for slug in hard if slug not in med and slug not in easy]
hard += SELECTED_TOKENS

# Maniac: Everything else
maniac = [b.index[cn]["slug"] for cn,cs in b.cards if cs.num_appearances < 100 and b.index[cn]["slug"] not in SELECTED_TOKENS]

slugs = {
    "easy": easy,
    "med": med,
    "hard": hard,
    "maniac": maniac,
}

with open("newslugs.json", "w", encoding="utf-8") as f:
    json.dump(slugs, f, indent=None)
