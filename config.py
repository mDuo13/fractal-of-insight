OUTDIR = "/another/site/fractal-of-insight"
TOP_CUTOFF = 300 # Use this many players by Elo to make the "Top Players" charts
UPSET_CUTOFF = 50 # Elo difference to consider something an upset
TEMPLATE_DIR = "./template/"
SUBTYPE_MATCH_MIN = 10 # Number of "true" matches a sub-archetype needs to be considered notable enough to show up in a battlechart

# Crawler settings
CRAWLER_FILE = "./data/crawler.json"
INTERESTING_PLAYER_COUNT = 20 # Crawler skips events with less than this number
REALLY_INTERESTING_PLAYER_COUNT = 60 # Crawler includes events with at least this many players even if they're "Regular" and have no decklists.
CRAWL_SAVE_INTERVAL = 50
EVT_MAX_LENGTH = 60*60*24*2 # Consider an event stale if it's "started" but at least this many seconds ago (2 days)
MAX_404_STREAK = 5 # If there are this many 404s in a row it probably means we've hit the end of registered events

class SharedConfig:
    """Global configs set at runtime"""
    go_fast = False
