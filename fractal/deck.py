from collections import defaultdict

from xxhash import xxh64

from .shared import slugify, fix_case, lineage, element_sortkey, ms_to_date, rank_card
from .datalayer import get_card_img, carddata, card_is_floating, get_card_references, pricedb, get_cached_similarity, store_similarity, is_material
from .cards import ELEMENTS, SPIRITTYPES, LINEAGE_BREAK, BANLIST, REMOVED_FROM_PRXY
from .archetypes import ARCHETYPES, SUBTYPES, NO_ARCHETYPE
from .cardstats import ALL_CARD_STATS
from .champs import CHAMP_DATA

SIDEBOARD_15PT_DATE = "2024-05-17" # Before MRC season, sideboard was any 8 cards

def rank_card_o(card_o):
    return rank_card(carddata[card_o["card"]])

def trim_similar(dlist, limit):
    """
    Given a list of (d,sim) tuples where d is a deck,
    return the limit most similar decks, ordered by date
    """
    dlist2 = [x for x in dlist]
    dlist2.sort(key=lambda x:x[1], reverse=True)
    if len(dlist) > limit:
        dlist2 = dlist2[:limit]
        dlist2.sort(key=lambda x:x[0].date)
        return dlist2
    return dlist2

class Deck:
    def __init__(self, dl, entrant, is_topcut_deck=False):
        self.dl = dl
        self.entrant = entrant
        self.date = ms_to_date(self.entrant.evt_time)
        self.similar_decks = []
        self.fix_dl()
        self.calc_hash()
        self.find_spirits()
        self.find_champs() # populates self.champs, self.lineages, self.classes
        self.find_elements() # populates self.els
        self.count_cards() # populates self.card_types and self.floating as well as total counts
        self.find_archetypes()
        self.cardlist_imgs()
        self.is_topcut_deck = is_topcut_deck
        self.calc_price()

        self.videos = [] # populated in OmniEvent.load_videos()

        ALL_CARD_STATS.add_deck(self)

    def find_spirits(self):
        self.spirits = []
        for card_o in self.mat:
            cardname = card_o["card"]
            card = carddata[cardname]
            if card.get("level") == 0:
                self.spirits.append(cardname)

    def find_champs(self):
        self.champs = []
        self.fatestones = []
        self.classes = set()
        lineages = []
        levels = set()
        self.is_hybrid = False
        for card_o in self.mat:
            cardname = card_o["card"]
            card = carddata[cardname]

            if "CHAMPION" in card.get("types", []):
                if card["level"] == 1 or cardname in LINEAGE_BREAK:
                    lineages.append(lineage(cardname))
                    if card["level"] in levels:
                        self.is_hybrid = True
                    self.champs.append(cardname)
                    levels.add(card["level"])
                elif lineage(cardname) in lineages:
                    self.champs.append(cardname)
                    levels.add(card["level"])
                for klass in card.get("classes", []):
                    if klass != "SPIRIT":
                        self.classes.add(klass)
            elif "FATESTONE" in card.get("subtypes", []):
                backside = card["editions"][0]["other_orientations"][0]["name"]
                self.fatestones.append(backside.split(",", 1)[0])

        self.lineages = list(dict.fromkeys(lineages)) # Uniquified

    def find_archetypes(self):
        self.archetypes = []
        self.subtypes = []

        # Special case to exclude "junk" decks from polluting stats,
        # lump them into Rogue Decks.
        if len(self.dl["material"]) > 12:
            NO_ARCHETYPE.add_match(self)
            #print(f"Too-large mat deck: {self.entrant} @ {self.entrant.event}")
            return

        for archetype in ARCHETYPES.values():
            if archetype.match(self):
                self.archetypes.append( archetype.name )
                for st in archetype.subtypes:
                    if st.match(self):
                        self.subtypes.append(st.name)

        if not self.archetypes:
            NO_ARCHETYPE.add_match(self)

        for champ in self.lineages:
            CHAMP_DATA[champ].add_match(self)

    def find_elements(self):
        """
        Set the list of basic elements provided by the deck's spirit(s) in
        self.els.

        Set the list of advanced elements in self.advanced_els
        """
        elset = set()
        for spirit in self.spirits:
            spiritcard = carddata[spirit]
            spirit_els = [e.title() for e in spiritcard.get("elements",[])]
            elset.update(spirit_els)
        if not elset:
            # probably a spiritless decklist error
            elset = {"Norm"}
        self.els = list(elset)
        self.els.sort() # Deterministic order avoids churn in old events

        # # Find advanced elements in maindeck
        # # Though, Looking Glass / Distortions makes this complicated
        # adv_elset = set()
        # for card_o in self.main:
        #     card = carddata[card_o["card"]]
        #     for el in card.get("elements",[]):
        #         if el.title() not in ELEMENTS:
        #             adv_elset.add(el.title())

        # # Find advanced elements enabled by champions
        # adv_elchamps = set()
        # for card_o in self.mat:
        #     card = carddata[card_o["card"]]
        #     if "CHAMPION" in card.get("types",[]):
        #         for el in card.get("elements", []):
        #             if el.title() not in ELEMENTS:
        #                 adv_elchamps.add(el.title())
        # # Add Exalted if the champ has any advanced element
        # if len(adv_elchamps):
        #     adv_elchamps.add("Exalted")

        # self.advanced_els = list(adv_elset & adv_elchamps)

    def fix_card_o(self, card_o):
        """
        Add appropriate metadata to a card object from a decklist,
        modifying the object in-place.
        """
        card_o["card"] = card_o["card"].strip()
        card_o["card"] = fix_case(card_o["card"])
        if card_o["card"] in BANLIST:
            card_o["banned"] = True
        if card_o["card"] in REMOVED_FROM_PRXY.keys():
            card_o["removed"] = True
        card_back = carddata[card_o["card"]].get("back")
        if card_back:
            card_o["back"] = card_back
        cardtypes = carddata[card_o["card"]].get("types", [])
        # if "TOKEN" in cardtypes or "MASTERY" in cardtypes:
        #     # Some people list tokens/masteries in their deck lists by accident.
        #     card_o["as_token"] = True

    def fix_dl(self):
        """
        Clean up the decklist and add some extra metadata such as
        card backs and ban status.
        """
        if not self.dl.get("main"):
            raise ValueError(f"Decklist has no maindeck? {self.dl}")

        # Special case for Yeti local 9/5/2024 which used Gate of Alterity as a placeholder for Polaris, Twinkling Cauldron
        if self.entrant.evt_time == 1725580800000:
            for card_o in self.dl["material"]:
                if card_o["card"] == "Gate of Alterity":
                    card_o["card"] = "Polaris, Twinkling Cauldron"

        for section in ("main", "material", "sideboard"):
            for card_o in self.dl[section]:
                self.fix_card_o(card_o)
            # Some people list tokens/masteries in their deck list by accident.
            # Remove those, after normalizing card names
            self.dl[section] = [card_o for card_o in self.dl[section]
                            if carddata.is_valid_in_decklists(card_o["card"])]
            self.dl[section].sort(key=rank_card_o)

        if len(self.dl["material"]) > 12:
            self.invalid_decklist = True
        else:
            # TODO: TBD what to do about decklists with accidentally no spirit
            self.invalid_decklist = False

    def count_cards(self):
        """
        Count various quantities of cards in the deck, such as the number
        of floating memory, allies, etc. Also counts how many total cards are
        in the material and main decks, and how many points the sideboard is.
        """
        card_types = defaultdict(int)
        self.floating = 0
        self.guns = 0 # used by "We Need Guns..." achievement
        m = 0
        for card_o in self.mat:
            m += card_o["quantity"] # should be 1 unless there's something weird going on
            card = carddata[card_o["card"]]
            if "GUN" in card.get("subtypes",[]):
                self.guns += 1
        self.mat_total = m
        el_counts = defaultdict(int)
        n = 0
        for card_o in self.main:
            n += card_o["quantity"]
            card = carddata[card_o["card"]]
            for cardtype in card["types"]:
                card_types[cardtype] += card_o["quantity"]
            if card_is_floating(card, self.champs):
                self.floating += card_o["quantity"]
            if "GUN" in card.get("subtypes",[]):
                self.guns += 1
            if len(card["elements"]) == 1:
                el_counts[card["elements"][0]] += card_o["quantity"]
            elif len(card["elements"]):
                # Count the combination of elements
                el_combo="/".join(sorted(card["elements"]))
                el_counts[el_combo] += card_o["quantity"]
        self.main_total = n
        if self.main_total < 60:
            self.invalid_decklist = True

        self.main_deck_els = []
        for el,quant in el_counts.items():
            pct = round(quant/n*100, 1)
            self.main_deck_els.append((el.title(), quant, pct))
        self.main_deck_els.sort(key=lambda x:element_sortkey(x[0]))

        card_types_sorted = [(k,v) for k,v in card_types.items()]
        card_types_sorted.sort(key=lambda x:x[0])
        self.card_types = {k:v for k,v in card_types_sorted}

        b = 0
        p = 0
        for card_o in self.side:
            card = carddata[card_o["card"]]
            b += card_o["quantity"]
            if is_material(card_o["card"]):
                p += 3 * card_o["quantity"]
            else:
                p += 1 * card_o["quantity"]
            if "GUN" in card.get("subtypes",[]):
                self.guns += 1
        self.side_total = b
        self.side_points = p
        if self.side_points > 15 and self.date >= SIDEBOARD_15PT_DATE:
            self.invalid_decklist = True

    def quantity_of(self, cardname, search_sections=("material","main")):
        """
        Count how many copies of a card are in the mainboard/materials for the deck.
        """
        n = 0
        for cat in search_sections:
            for card_o in self.dl[cat]:
                if card_o["card"] == cardname:
                    n += card_o["quantity"]
        return n

    def card_score(self, cardname):
        """
        Return a score based on how many copies of a card are in which parts of
        the deck. Cards score 1 point per copy, triple for material deck cards,
        1/3 points for copies in the sideboard.
        """
        if is_material(cardname):
            type_multiplier = 3
        else:
            type_multiplier = 1
        card_quant_mat_main = self.quantity_of(cardname)
        card_quant_side = self.quantity_of(cardname, search_sections=("sideboard",))
        card_score = type_multiplier * (
            card_quant_mat_main +
            (1/3 * card_quant_side)
        )
        return card_score

    def card_score_rate(self, cardname):
        """
        Return a rating, from 0 to 1.0, based on how many copies of the card are
        in which parts of the deck, where 1.0 is the maximum number of copies
        allowed.
        """
        if is_material(cardname):
            max_card_score = 3
        else:
            max_card_score = 4
        return self.card_score(cardname) / max_card_score


    def cardlist_imgs(self):
        """
        Add card image links to the decklist data
        """
        for cat in ("material", "main", "sideboard"):
            for card_o in self.dl[cat]:
                card_o["img"] = get_card_img(card_o["card"], at=self.entrant.evt_time)

    def calc_hash(self):
        """
        Calculate a fast hash of this deck's decklist, to aid similarity comparisons
        """
        dlstr = ""
        for cat in ("material", "main", "sideboard"):
            for card_o in self.dl[cat]:
                dlstr += f"{card_o['quantity']} {card_o['card']}\n"
        dlbytes = dlstr.encode("utf-8")
        self.hash = xxh64(dlbytes).hexdigest()

    def similarity_to(self, other_deck):
        """
        Calculate a similarity score between two decks, as S/T, where
        S = total points in common and
        T = total points in the larger deck.
        Points are calculated as follows:
        Material deck cards are 3 points
        Main deck cards are 1 point per copy of a card
        Sideboard cards are scored the same except at ⅔ value since
            they're available for 2 games in a best of 3.
        T=118 if a deck has 12 material, 60 maindeck, and a 15-point sideboard.
        Returned as a percentage rounded to 1 decimal point.
        """
        if self.hash == other_deck.hash:
            # print("Deck hashes match")
            return 100.0

        cached_sim = get_cached_similarity(self.hash, other_deck.hash)
        if cached_sim is not None:
            return cached_sim

        total_me = 3*self.mat_total + self.main_total + ((2/3)*self.side_points)
        total_them = 3*other_deck.mat_total + other_deck.main_total + ((2/3)*other_deck.side_points)
        t = max(total_me, total_them)

        s = 0
        for sect,mult in (("material", 3), ("main", 1), ("sideboard", 1)):
            # Optimization since comparing deck similarity is pretty slow:
            # iterate both lists in parallel (they should be sorted at this point)
            # which should cut down on the calls to quantity_of on maindeck
            i = 0
            j = 0
            imax = len(self.dl[sect])
            jmax = len(other_deck.dl[sect])
            while i < imax and j < jmax:
                # TODO: make prize spirits to count the same as basic spirits?
                card_o = self.dl[sect][i]
                them_o = other_deck.dl[sect][j]
                # Use rank_card instead of comparing names so sure prize spirits don't screw up the ordering
                if rank_card_o(card_o) < rank_card_o(them_o):
                    i += 1
                    continue
                elif rank_card_o(card_o) > rank_card_o(them_o):
                    j += 1
                    continue
                # Else the names match, compare quantities
                # TODO: look at sideboard in parallel for better matching
                q_me = card_o["quantity"]
                q_them = them_o["quantity"]
                if sect == "sideboard":
                    if is_material(card_o["card"]):
                        use_mult = 2 # ⅔ * 3
                    else:
                        use_mult = 2/3
                else:
                    use_mult = mult

                s += use_mult * min(q_me, q_them)

                i+=1
                j+=1

        similarity = round(100*s/t, 1)
        store_similarity(self.hash, other_deck.hash, similarity)
        return similarity

    def similar_decks_json(self, list_of_decks):
        l = []
        for od,sim in list_of_decks:
            j = {
                "evt_id": od.entrant.evt_id,
                "szn": od.entrant.event.season,
                "p_id": od.entrant.id,
                "p_name": od.entrant.username,
                "evt_name": od.entrant.event.name,
                "pct": sim,
            }
            if od.is_topcut_deck:
                j["topcut"] = 1
            l.append(j)
        return l

    def split_similar_decks(self, limit=10, as_json=False):
        decks_before = []
        decks_sameday = []
        decks_after = []
        for d,sim in self.similar_decks:
            if d.date < self.date:
                decks_before.append([d,sim])
            elif d.date == self.date:
                decks_sameday.append([d,sim])
            else:
                decks_after.append([d,sim])

        trimmed = (
            trim_similar(decks_before, limit), 
            trim_similar(decks_sameday, limit), 
            trim_similar(decks_after, limit)
        )
        
        if as_json:
            labels = ("before", "sameday", "after")
            return {
                labels[i]: self.similar_decks_json(trimmed[i])
                for i in range(len(trimmed))
            }
        return trimmed

    def rate_hipster(self, hdb):
        """
        Given a HipsterDB (for a given point in time), calculate this deck's
        hipster rating, which is based on how popular the cards in it are,
        normalized to a (12 card mat, 60 card main, 15 point side) deck size
        """
        self.hipster = 0
        mat_weight = 1 / (self.mat_total / 12)
        for card_o in self.mat:
            self.hipster += hdb.score(card_o["card"]) * mat_weight * 3
        main_weight = 1 / (self.main_total / 60)
        for card_o in self.main:
            self.hipster += hdb.score(card_o["card"]) * card_o["quantity"] * main_weight
        for card_o in self.side:
            if is_material(card_o["card"]):
                type_multiplier = 3
            else:
                type_multiplier = 1
            self.hipster += hdb.score(card_o["card"]) * card_o["quantity"] * type_multiplier
        # 111 is the total point score for a 12/60/15 size deck
        self.hipster = round(self.hipster / 111, 1)
        return self.hipster

    def calc_price(self):
        total_price = 0
        prices_unavailable = []
        for sect in ("material", "main", "sideboard"):
            for card_o in self.dl[sect]:
                price = pricedb.get_card_price(card_o["card"], sub_prizes=True)
                if price:
                    total_price += price * card_o["quantity"]
                else:
                    prices_unavailable.append(card_o["card"])
        self.price_num = total_price
        self.price = f"${total_price:.2f}"
        if prices_unavailable:
            self.price += f"* (*Price data could not be found for the following cards: {', '.join(prices_unavailable)})"

    def tts_json(self):
        """
        JSON decklist formatted for Tabletop Simulator import
        """
        j = {
            "cards": {
                "material": [],
                "main": [],
                "sideboard": [],
                "references": []
            }
        }
        raw_refs = []
        for section in ("main", "material", "sideboard"):
            for card_o in self.dl[section]:
                raw_refs += get_card_references(card_o["card"])
                j_card = {
                    "name": card_o["card"],
                    "image": card_o["img"],
                    "quantity": card_o["quantity"],
                    "types": carddata[card_o["card"]]["types"],
                }
                if card_o.get("banned"):
                    j_card["banned"] = 1
                if card_o.get("removed"):
                    j_card["removed"] = 1
                if card_o.get("back"):
                    j_card["orientation"] = "Front"
                    j_card["orientations"] = [{
                        "orientation": "Back",
                        "name": card_o["back"]["name"],
                        "image": card_o["back"]["img"]
                    }]
                j["cards"][section].append(j_card)
        for r in raw_refs:
            j["cards"]["references"].append({
                "name": r["name"],
                "image": r["img"]
            })
        return j

    def __str__(self):
        spiritstr = ""
        if self.invalid_decklist:
            return "(Invalid decklist)"
        if len(self.spirits) < 1:
            spiritstr = "(Spiritless???) "
        elif len(self.spirits) > 1:
            if len(self.els) == 1:
                # spirittypes = []
                # for spirit in self.spirits:
                #     for keyword in SPIRITTYPES:
                #         if keyword in spirit:
                #             spirittypes.append(keyword)
                #             break
                #     else:
                #         spirittypes.append("Regular")
                # spirittypes.sort(key=lambda x: "zzz" if x=="Regular" else x) #Sort "Regular" last
                # spiritstr = "/".join(spirittypes) + " " + self.els[0]
                spiritstr = self.els[0]
            else:
                spiritstr = "(Multi-Element) "
        else:
            spiritstr = self.els[0]
            # for keyword in SPIRITTYPES:
            #     if keyword in spirit:
            #         spiritstr += keyword + " "

            # spiritstr += "/".join(self.els)

        if len(self.lineages) == 1:
            champstr = list(self.lineages)[0]
        elif len(self.lineages) > 1:
            champset = {lineage(c):True for c in self.champs if lineage(c) in self.lineages}
            champstr = "/".join(champset.keys())
        else:
            champstr = ""
        if self.is_hybrid:
            champstr += " Hybrid"

        # if self.fatestones:
        #     champstr = " ".join(self.fatestones) + " " + champstr

        if not self.archetypes:
            archetypestr = ""
        else:
            archetype_list = []
            for st in self.subtypes:
                archetype_list.append(SUBTYPES[st].shortname)
            for arche in self.archetypes:
                archetype_list.append(ARCHETYPES[arche].shortname)
            archetypestr = " ".join(archetype_list)

        return " ".join((spiritstr, archetypestr, champstr)).replace("  "," ")

    @property
    def representative_champion(self):
        """
        Return a single champion that best represents the deck; includes variant
        champion names for some cases (e.g. Luxem vs Lv1 Zander)
        """
        if len(self.lineages) == 0:
            return ""
        elif len(self.lineages) > 0:
            if "Merlin, Kingslayer" in self.champs:
                # Typically Kingslayer is more important to a deck's identity
                # than their Lv1
                return "Merlin"
            if "Luxem Assassin" in self.archetypes:
                return "Luxem Zander"
            if "Shadowstrike" in self.archetypes:
                return "Shadowstrike Tristan"
            if "Diana, Aether Dilettante" in self.champs:
                return "Aether Diana"
            if "Merlin, Memorite Vassal" in self.champs:
                return "Sheen Merlin"
            if "Astra Cleric" in self.archetypes:
                return "Astra Arisanna"
            if "Alice, Distorted Queen" in self.champs:
                return "Distortion Alice"
            return self.lineages[-1] #TODO: handle hybrid lineages better

    def __iter__(self):
        """
        Iterate the material and main decks, returning card names
        """
        for card_o in self.dl["material"]:
            yield card_o["card"]
        for card_o in self.dl["main"]:
            yield card_o["card"]

    @property
    def mat(self):
        """
        Iterate the material deck, returning card objects
        """
        for card_o in self.dl["material"]:
            yield card_o

    @property
    def main(self):
        """
        Iterate main deck only, returning card objects
        """
        for card_o in self.dl["main"]:
            yield card_o

    @property
    def side(self):
        """
        Iterate the sideboard, returning card objects
        """
        for card_o in self.dl["sideboard"]:
            yield card_o

    @property
    def refs(self):
        """
        Iterator for tokens, masteries, etc.—cards referenced by the deck
        but not included in the deck.
        """
        unique_refs = {}
        for card_o in self.main:
            for section in ("main", "material", "sideboard"):
                for card_o in self.dl[section]:
                    for raw_ref in get_card_references(card_o["card"]):
                        unique_refs[raw_ref["name"]] = raw_ref

        for ref in unique_refs.values():
            yield {
                "card": ref["name"],
                "img": ref["img"],
                "as_token": True
            }

    @property
    def subtype_list(self):
        return self.els + self.lineages + self.subtypes
