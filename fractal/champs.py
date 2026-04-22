import re
from collections import defaultdict

from .archetypes import Archetype, Eltype, ARCHETYPES
from .datalayer import carddata
from .stats import ArcheStats, Wielders
from .shared import lineage, rank_card

class ChampWielders(Wielders):
    """
    Wielder score for a champion: Each win scores 9 points if the champion is
    in your mainboard or 3 points if they're in your sideboard.
    Ties score 1/3 as much.
    """
    def add(self, entrant):
        # TODO: handle top-cut decks from Worlds
        usage = 0
        for card_o in entrant.deck.mat:
            if lineage(card_o["card"]) == self.name:
                usage = 3
                break
        else:
            for card_o in entrant.deck.side:
                if lineage(card_o["card"]) == self.name:
                    usage = 1
                    break
            else:
                print("ChampWielder without champ?", self.name, entrant)
                return
        
        usage_score = entrant.score * usage
        super().add(entrant, usage_score)


class ChampArchetype(Archetype):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.arche_subtypes = {}
        self.archedata = ArcheStats()
        self.cards = [carddata[c] for c in self.require]
        self.cards.sort(key=rank_card)
        self.wielders = ChampWielders(self.name)
    
    def add_match(self, deck):
        self.matched_decks.append(deck)
        for deck_el in deck.els:
            if deck_el not in self.el_subtypes.keys():
                self.el_subtypes[deck_el] = Eltype(deck_el, self)
            self.el_subtypes[deck_el].matched_decks.append(deck)
    
    def analyze(self):
        super().analyze()
        for d in self.matched_decks:
            self.wielders.add(d.entrant)
            for archename in d.archetypes:
                arche = ARCHETYPES[archename]
                if self.name in arche.champ_subtypes.keys():
                    self.arche_subtypes[arche.name] = arche.champ_subtypes[self.name]
            self.archedata.add_deck(d)
        self.wielders.sort()


champ_cards = defaultdict(list)

for cardname,card in carddata.items():
    if "CHAMPION" in card.get("types") and card.get("cost_memory",0) > 0:
        champ = lineage(cardname)
        champ_cards[champ].append(cardname)

CHAMP_DATA = {}
for champ, cards_of_champ in champ_cards.items():
    CHAMP_DATA[champ] = ChampArchetype(champ, cards_of_champ)
