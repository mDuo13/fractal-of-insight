# Fractal of Insight
A Grand Archive TCG tournament analysis site

This site shows information and analysis of Grand Archive tournament results. It uses the Omnidex API, which is beta and subject to change without notice, in a way that is officially unsupported but hopefully OK with Weebs of the Shore.

## Setup & Usage

Fractal is essentially a static site builder that uses locally-cached data from various public sources (Omnidex, Index, & TCGCSV). So after setup, the process is download → run → preview as static HTML site.

After cloning the repo, edit `fractal/config.py` and change the `OUTDIR` to be a path where the ouput should go (e.g. `/srv/http`).

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./scrape-index.py
./scrape-tcgprice.py
./main 52777
```

Use `./crawl-omni.py` to iterate through Omnidex IDs looking for events, or pass omni IDs to `./main.py` directly as in the above example. When run with no args, `main.py` builds all previously crawled/saved events (stored in `data/`).

You can start a local dev server to preview the site by going to your configured output directory and running `python -m http.server`. You can of course use something more powerful like Apache HTTPD, Nginx, etc.

## TODO / Planned Features

- refine archetype classification
    - use machine-learning clustering to identify archetypes?
    - archetype overlap chart?
    - add advanced elements to name without needing them to be archetypes necessarily
- calculate stats on upsets
- make dynamic sections, i.e. flask app or something, for showing individual events or doing dynamic queries
- track invite points/cards, if possible? (might require sideloading number of invites per event)
- sideboard / tech cards prevalence rate (season/format)
- path of silver data
- more achievements in general
- improve presentation of price data
    - maybe show average or median price per archetype?
    - maybe optimize it to load a price sheet dynamically to reduce churn on page builds?
    - add historical price data (timed by major events?)
- maybe make more tables sortable.
- report even more stats in a rolling window or seasonal basis
    - e.g. individual card stats (on card page)
- backfill old store champs
- improve champion pages:
    - seasonal data
    - link cards in lineage to their card pages
    - link to champion pages from other pages
- Show timeline of meta (within a season?) w/ major events and archetype share marked
- adjust conversion rate stats to better handle players who qualified but dropped?
- on card pages, show other arts for card
- double-check numbers on rising cards
- add a wielder points section to player profiles
- improve display of About Refracted Events page.
- add an icon & other styles to highlight Refracted events
- update FRCTL to show RDO spoilers directly now that they're not hidden in the main site anymore
- improve reliability / resilience to bad/unexpected/missing data
- improve experience / instructions for building with a fresh clone of the repo
- improve sorting of events on main page to sort by close time (not just date)
- save event filtering settings to browser storage
- add vods for ascent Icebound Slam Cup
- make condensed view of battlechart with top 10-ish archetypes only
- archetype head-to-head analysis: cards more/less prevalent in winning lists?
- improve pagination & filtering on players page
    - filter by region
    - jump to start/end/middle?
- improve decklist delta:
    - link back to decklists
    - try to handle topcut decks & other things not in omni (using tts format maybe?)
    - permalink button for current comparison
    - update query params when you run a comparison?
    - collapse controls?
    - better graphics for ⇒?
- switch to dynamic sightings on more pages (cards, champs)
    - look into saving data?
