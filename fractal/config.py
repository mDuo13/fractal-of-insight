OUTDIR = "/another/site/fractal-of-insight"
TOP_CUTOFF = 300 # Use this many players by Elo to make the "Top Players" charts
UPSET_CUTOFF = 50 # Elo difference to consider something an upset
TEMPLATE_DIR = "./template/"
SUBTYPE_MATCH_MIN = 10 # Number of "true" matches a sub-archetype needs to be considered notable enough to show up in a battlechart

# Card & deck stats settings
HOT_WINDOW = 60*60*24*61 # last ~60 days in seconds, for "Hot" card numbers
PAD_UNTIL = 500 # Minimum number of appearances for a card to be eligible for "winningest" list
M_PER_APP = 6 # Empirically, an average "appearance" consists of ~5.9 matches.
MAX_TOP_USERS = 10 # How many players can be considered "top users" of a card.
PAD_HOT_MATCHES = 500 # for hot cards, weight for this many *matches* (not appearances)

# Archetype & champ stats settings
SIMILAR_DECKS_CUTOFF = 85
MONEY_CARD_COUNT = 20
MONEY_CARD_PRICE_CUTOFF = 5.00 # Only include cards that cost at least $ this
RISING_CARDS_CUTOFF_PCT = 0.0 # only include cards that gained by this much
MAT_DIFF_CARD_LIMIT = 12
MAIN_DIFF_CARD_LIMIT = 15
SIDE_DIFF_CARD_LIMIT = 8
RISING_CARD_LIMIT = 10

# Crawler settings
CRAWLER_FILE = "./data/crawler.json"
INTERESTING_PLAYER_COUNT = 20 # Crawler skips events with less than this number
REALLY_INTERESTING_PLAYER_COUNT = 60 # Crawler includes events with at least this many players even if they're "Regular" and have no decklists.
CRAWL_SAVE_INTERVAL = 50
EVT_MAX_LENGTH = 60*60*24*3 # Consider an event stale if it's "started" but at least this many seconds ago (3 days)
STALE_GRACE_PERIOD = EVT_MAX_LENGTH # Consider an event stale if it hasn't started this long after its scheduled start time
MAX_404_STREAK = 5 # If there are this many 404s in a row it probably means we've hit the end of registered events
SHOW_RDO_SPOILERS = True

class SharedConfig:
    """Global configs set at runtime"""
    go_fast = False
