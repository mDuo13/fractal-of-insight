# Fractal of Insight
A Grand Archive TCG tournament analysis site

This site shows information and analysis of Grand Archive tournament results. It uses the Omnidex API, which is beta and subject to change without notice, in a way that is officially unsupported but hopefully OK with Weebs of the Shore.

## TODO / Planned Features

improved visual styles overall
    pie chart for element composition
    fix archetype layout on event page when lots of archetypes
    unify event list style across index and season pages
decklist count for events
filter events on landing page
replace obscure unicode symbols with things that work on devices without the right fonts
mobile-friendly tooltip alternative
refine archetype classification
    require card combos or density (i.e. % allies or % resemblance to a predefined list)
    use machine-learning clustering to identify archetypes?
archetype overlap chart
archetype overall winrate stats
champion/class stats
fix overlay effect for deck view (click shaded area should close, controls shouldn't scroll)
crawler: track which events have been checked, which events might need updates
handle team standard format
    separate stats?
add ability to sideload decklists (e.g. for old events)
parse single-elimination stages / overall winner
omit empty sections (meta comp, head-to-head) for events w/o decklists
add player profiles across events?
make dynamic sections, i.e. flask app or something, for showing individual events
stats on most-used cards, etc.
