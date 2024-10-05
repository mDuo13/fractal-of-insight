# Fractal of Insight
A Grand Archive TCG tournament analysis site

This site shows information and analysis of Grand Archive tournament results. It uses the Omnidex API, which is beta and subject to change without notice, in a way that is officially unsupported but hopefully OK with Weebs of the Shore.

## TODO / Planned Features

- (partly done) improved visual styles overall
- (partly done) mobile-friendly tooltip alternative
    - works ok in player list, not so much in match list.
- refine archetype classification
    - require card combos or density (i.e. % allies or % resemblance to a predefined list)
    - use machine-learning clustering to identify archetypes?
    - archetype overlap chart?
- display more archetype stats:
    * typical ratio of card types in maindeck (ally, action, attack, item, phantasia)
    * average floating memory count?
    * top (?) finishes (aside from event wins)
- calculate stats on upsets
- champion overviews / stats
- handle team standard format (separately?)
- make dynamic sections, i.e. flask app or something, for showing individual events or doing dynamic queries
- stats on most-used cards, etc.
- divide matchup stats by before/after banlist changes & balance errata
- track seasonal invites, if possible? (might require sideloading number of invites per event)
- two-way rivalry stats?
