OUTDIR = "/another/site/fractal-of-insight"
TOP_CUTOFF = 300 # Use this many players by Elo to make the "Top Players" charts
UPSET_CUTOFF = 50 # Elo difference to consider something an upset
TEMPLATE_DIR = "./template/"

# Crawler settings
CRAWLER_FILE = "./data/crawler.json"
INTERESTING_PLAYER_COUNT = 20 # Crawler skips events with less than this number
REALLY_INTERESTING_PLAYER_COUNT = 60 # Crawler includes events with at least this many players even if they're "Regular" and have no decklists.
CRAWL_SAVE_INTERVAL = 50
