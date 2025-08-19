from time import strftime, gmtime
from collections import defaultdict

from xxhash import xxh64

from shared import slugify, fix_case, lineage, element_sortkey
from datalayer import get_card_img, carddata, card_is_floating, get_card_references, get_card_price, get_cached_similarity, store_similarity
from cards import ELEMENTS, SPIRITTYPES, LINEAGE_BREAK, BANLIST
from archetypes import ARCHETYPES, SUBTYPES, NO_ARCHETYPE
from cardstats import ALL_CARD_STATS

def rank_card(card_o):
    return rank_cardname(card_o["card"])
def rank_cardname(cardname):
    card = carddata[cardname]
    # First sort: Champs by level, Regalia, Maindeck
    if card["level"] is not None:
        rank = str(card["level"])
    elif "REGALIA" in card["types"]:
        rank = "B"
    else:
        rank = "C"
    # Second sort: Norm, Basic Element, Advanced Element
    # with multi-element cards ranked based on primary element, then secondary
    el_keys = [element_sortkey(e) for e in card["elements"]]
    el_keys.sort()
    el_rank = "/".join(el_keys)
    # Third sort: alphabetical, case-insensitive
    return rank + el_rank + "-" + cardname.lower()

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
        self.date = strftime(r"%Y-%m-%d", gmtime(self.entrant.evt_time/1000))
        self.similar_decks = []
        self.fix_dl()
        self.calc_hash()
        self.find_spirits()
        self.find_champs()
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


    def find_elements(self):
        """
        Set the list of basic elements provided by the deck's spirit(s).
        Doesn't count main deck, Lv1+ champs, or sideboard.
        """
        els = []
        for spirit in self.spirits:
            for element in ELEMENTS:
                if element in spirit:
                    if element not in els:
                        els.append(element)
                    break
        if not els:
            els.append("Norm")
        self.els = els

    def fix_dl(self):
        """
        Clean up the decklist and add some extra metadata such as
        card backs and ban status.
        """
        if not self.dl.get("main"):
            raise ValueError(f"Decklist has no maindeck? {self.dl}")
        for card_o in self.dl["main"]:
            card_o["card"] = card_o["card"].strip()
            card_o["card"] = fix_case(card_o["card"])
            if card_o["card"] in BANLIST:
                card_o["banned"] = True
            card_back = carddata[card_o["card"]].get("back")
            if card_back:
                card_o["back"] = card_back
        for card_o in self.dl["material"]:
            card_o["card"] = card_o["card"].strip()
            card_o["card"] = fix_case(card_o["card"])
            if card_o["card"] in BANLIST:
                card_o["banned"] = True
            card_back = carddata[card_o["card"]].get("back")
            if card_back:
                card_o["back"] = card_back
        for card_o in self.dl["sideboard"]:
            card_o["card"] = card_o["card"].strip()
            card_o["card"] = fix_case(card_o["card"])
            if card_o["card"] in BANLIST:
                card_o["banned"] = True
            card_back = carddata[card_o["card"]].get("back")
            if card_back:
                card_o["back"] = card_back

        # Special case for Yeti local 9/5/2024 which used Gate of Alterity as a placeholder for Polaris, Twinkling Cauldron
        if self.entrant.evt_time == 1725580800000:
            for card_o in self.dl["material"]:
                if card_o["card"] == "Gate of Alterity":
                    card_o["card"] = "Polaris, Twinkling Cauldron"


        self.dl["main"].sort(key=rank_card)
        self.dl["sideboard"].sort(key=rank_card)
        self.dl["material"].sort(key=rank_card)

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

        self.main_deck_els = []
        for el,quant in el_counts.items():
            pct = round(quant/n*100, 1)
            self.main_deck_els.append((el.title(), quant, pct))
        self.main_deck_els.sort(key=lambda x:element_sortkey(x[0]))

        self.main_total = n
        card_types_sorted = [(k,v) for k,v in card_types.items()]
        card_types_sorted.sort(key=lambda x:x[0])
        self.card_types = {k:v for k,v in card_types_sorted}

        b = 0
        p = 0
        for card_o in self.side:
            card = carddata[card_o["card"]]
            b += card_o["quantity"]
            if "CHAMPION" in card["types"] or "REGALIA" in card["types"]:
                p += 3 * card_o["quantity"]
            else:
                p += 1 * card_o["quantity"]
            if "GUN" in card.get("subtypes",[]):
                self.guns += 1
        self.side_total = b
        self.side_points = p

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


    def cardlist_imgs(self):
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
                if rank_card(card_o) < rank_card(them_o):
                    i += 1
                    continue
                elif rank_card(card_o) > rank_card(them_o):
                    j += 1
                    continue
                # Else the names match, compare quantities
                # TODO: look at sideboard in parallel for better matching
                q_me = card_o["quantity"]
                q_them = them_o["quantity"]
                if sect == "sideboard":
                    card = carddata[card_o["card"]]
                    if "CHAMPION" in card["types"] or "REGALIA" in card["types"]:
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

    def split_similar_decks(self, limit=10):
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

        return trim_similar(decks_before, limit), trim_similar(decks_sameday, limit), trim_similar(decks_after, limit)

    def rate_hipster(self, ALL_CARD_STATS):
        self.hipster = 0
        for card_o in self.mat:
            if card_o["card"] not in ALL_CARD_STATS.items.keys():
                # Skip things without stats, like tokens that shouldn't be in decklists
                continue
            self.hipster += (ALL_CARD_STATS[card_o["card"]].hipster)
        for card_o in self.main:
            if card_o["card"] not in ALL_CARD_STATS.items.keys():
                # Skip things without stats, like tokens that shouldn't be in decklists
                continue
            self.hipster += (ALL_CARD_STATS[card_o["card"]].hipster) * card_o["quantity"]
        for card_o in self.side:
            if card_o["card"] not in ALL_CARD_STATS.items.keys():
                # Skip things without stats, like tokens that shouldn't be in decklists
                continue
            self.hipster += (ALL_CARD_STATS[card_o["card"]].hipster) * card_o["quantity"]
        self.hipster = round(self.hipster / 100, 1)

    def calc_price(self):
        total_price = 0
        prices_unavailable = []
        for sect in ("material", "main", "sideboard"):
            for card_o in self.dl[sect]:
                price = get_card_price(card_o["card"], sub_prizes=True)
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
                spirittypes = []
                for spirit in self.spirits:
                    for keyword in SPIRITTYPES:
                        if keyword in spirit:
                            spirittypes.append(keyword)
                            break
                    else:
                        spirittypes.append("Regular")
                spirittypes.sort(key=lambda x: "zzz" if x=="Regular" else x) #Sort "Regular" last
                spiritstr = "/".join(spirittypes) + " " + self.els[0]
            else:
                spiritstr = "(Multi-Element) "
        else:
            spirit = self.spirits[0]
            for keyword in SPIRITTYPES:
                if keyword in spirit:
                    spiritstr += keyword + " "

            spiritstr += "/".join(self.els)

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

    def __iter__(self):
        for card_o in self.dl["material"]:
            yield card_o["card"]
        for card_o in self.dl["main"]:
            yield card_o["card"]

    @property
    def mat(self):
        for card_o in self.dl["material"]:
            yield card_o

    @property
    def main(self):
        """
        Iterate main deck only
        """
        for card_o in self.dl["main"]:
            yield card_o

    @property
    def side(self):
        for card_o in self.dl["sideboard"]:
            yield card_o

    @property
    def refs(self):
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
