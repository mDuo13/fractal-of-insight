from collections import defaultdict

from .cardstats import ALL_CARD_STATS

class HipsterDB:
    def __init__(self):
        self.cards = defaultdict(int)
        self.ratings = {}
        self.decks_pending_rating = []

    def add_deck(self, d):
        if d.invalid_decklist:
            # Don't count these
            d.hipster = None
            return
        for card_o in d.mat:
            card_points = d.card_score_rate(card_o["card"])
            # self.cards[card_o["card"]].append( (d.date, card_points) )
            self.cards[card_o["card"]] += card_points

        for card_o in d.main:
            card_points = d.card_score_rate(card_o["card"])
            self.cards[card_o["card"]] += card_points
        
        for card_o in d.side:
            if card_o["card"] in d:
                # Skip cards already counted for existing in main/mat decks
                continue
            card_points = d.card_score_rate(card_o["card"])
            self.cards[card_o["card"]] += card_points
        
        self.decks_pending_rating.append(d)
    
    def update_scores(self):
        """
        Calculate current card hipster ratings, then update the hipster scores
        of all decks pending a rating and return the floor (lowest hipster
        rating among the newly-rating decks)
        """
        mostpoints = [(k,v) for k,v in self.cards.items()]
        mostpoints.sort(key=lambda x:x[1], reverse=True)
        prevcardpoints = None
        use_i = None
        for i, (cardname,cardpoints) in enumerate(mostpoints):
            if cardpoints != prevcardpoints:
                # In case of ties, award all cards the same rating
                use_i = i
            prevcardpoints = cardpoints
            self.ratings[cardname] = round(100 * use_i / len(mostpoints), 1)

        # Now update pending decks based on current ratings
        hipster_floor = 99999
        for d in self.decks_pending_rating:
            rating = d.rate_hipster(self)
            if rating < hipster_floor:
                hipster_floor = rating
        self.decks_pending_rating = []
        return hipster_floor

    def score(self, cardname):
        """
        Return a hipster score for a card (given the current rolling data).
        """
        return self.ratings[cardname]
