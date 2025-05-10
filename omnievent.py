from collections import defaultdict
from time import strftime, gmtime

from player import Entrant, JudgeEvt
from battlechart import BattleChart
from datalayer import get_event, get_event_videos, get_card_img
from archetypes import ARCHETYPES
from cards import ELEMENTS
from competition import EVENT_TYPES, TEAM_STANDARD
from season import SEASONS
from shared import ElementStats, ArcheStats, ChampStats, RegionStats
from config import TOP_CUTOFF

class IsTeamEvent(Exception):
    pass

def pct_with_archetype(players, arche):
    nom = 0
    for p in players:
        if p.deck and arche in p.deck.archetypes:
            nom += 1
    dec = nom / len(players)
    return round(dec*100, 1)

class OmniEvent:
    def __init__(self, evt_id, force_redownload=False):
        self.id = evt_id
        self.evt = get_event(self.id, force_redownload)
        if self.evt["format"] == TEAM_STANDARD and not isinstance(self, Team3v3Event):
            raise IsTeamEvent
        self.format = self.evt["format"]
        self.matchformat_swiss = self.evt["matchConfigSwiss"]
        self.matchformat_topcut = self.evt.get("matchConfigSingleElim")
        self.name = self.evt["name"]
        self.host = self.evt["store"]["name"]
        self.fix_generic_name()
        self.date = strftime(r"%Y-%m-%d", gmtime(self.evt["startAt"]/1000))
        if "season" in self.evt:
            self.season = SEASONS.get(self.evt["season"]["name"], "OTHER")
            self.track_elo = True
        else:
            self.season = "OFF"
            self.track_elo = False
        self.category = EVENT_TYPES.get(self.evt["category"], {"name": "Unknown"})
        self.country = self.evt.get("addressCountryCode", "")
        # At 3pts/win and 1pt/draw, anyone with over 1.5 points/rnd
        # has a theoretical "win rate" of > 50% of possible matches
        # (e.g. missing day 2 is like losing all your day 2 games)
        self.fiftypct_points = self.evt["rounds"] * 1.5

        self.judges = [JudgeEvt(jdata, self) for jdata in self.evt.get("judges", [])]

        
        self.winner = None
        self.load_players() # populates self.players, self.num_decklists, self.decklist_status
        self.load_videos()
        self.analyze() #populates self.elements, archedata, champdata, draw_pct, nat_draw_pct
        self.battlechart = self.calc_headtohead(track_elo=self.track_elo)
        self.bc_top = self.calc_headtohead(TOP_CUTOFF)
        if not isinstance(self, Team3v3Event):
            self.parse_top_cut() # populates self.top_cut
            # For Team3v3, this needs to happen after parse_teams()
        self.analyze_day2()
    
    def fix_generic_name(self):
        GENERIC_WORDS = [
            "Grand",
            "Archive",
            "TCG",
            "Storechamp",
            "Store",
            "Championships",
            "Championship",
            "Champion",
            "Champs",
            "Regionals",
            "Regional",
            "Event",
            "Mercurial Heart",
            "Mortal Ambition",
            "Standard",
            "Constructed",
            "DOA", "FTC", "ALC", "MRC", "AMB", "HVN",
        ]
        testname = self.name.lower()
        for word in GENERIC_WORDS:
            testname = testname.replace(word.lower(), "")
        testname = testname.strip()
        if not testname:
            #print(f"Fixing generic event name (remaining testname was '{testname}')")
            # it's a generic name, add the store name
            self.name = self.evt["store"]["name"] + " " + self.name
    
    def load_players(self):
        self.num_decklists = 0
        self.players = []
        for pdata in self.evt["players"]:
            p = Entrant(pdata, self.id, self)
            self.players.append(p)
            if p.deck:
                self.num_decklists += 1
        self.players.sort(key=lambda x:x.sortkey(), reverse=True)
        for i,p in enumerate(self.players):
            p.placement = i+1
        self.pdict = {p.id: p for p in self.players}
        if self.num_decklists == len(self.players):
            self.decklist_status = "full"
        elif self.num_decklists == 0:
            self.decklist_status = "none"
        else:
            self.decklist_status = "partial"
        if self.track_elo:
            self.average_elo = round(sum([p.elo for p in self.players]) / len(self.players), 1)
    
    def load_videos(self):
        self.videos = get_event_videos(self.id)
        for vid in self.videos:
            stage = vid.get("stage", 1)
            rnd = vid["round"]
            p1 = vid["p1"]
            p2 = vid["p2"]
            #print(f"adding match vid. stage {stage}, round {rnd}, #{p1} vs #{p2}")
            matches = self.evt["stages"][stage - 1]["rounds"][rnd - 1]["matches"]
            for m in matches:
                if m["pairing"][0]["id"] in (p1,p2) and m["pairing"][1]["id"] in (p1,p2):
                    m["video"] = vid["link"]

    
    def analyze(self):
        self.elements = ElementStats()
        self.archedata = ArcheStats()
        self.champdata = ChampStats()
        self.regiondata = RegionStats()
        for p in self.players:
            if p.deck:
                self.elements.add_deck(p.deck)
                self.archedata.add_deck(p.deck)
                self.champdata.add_deck(p.deck)
            else:
                self.elements.add_unknown()
                self.archedata.add_unknown()
                self.champdata.add_unknown()
            self.regiondata.add_player(p)
        self.calc_draw_pct()
        self.calc_sideboards()
    
    def analyze_day2(self):
        # TODO: maybe turn this into a list of stages?
        keepN = self.evt.get("keepN")
        if keepN:
            day2_start = keepN[0]['round']
            stage1 = self.evt['stages'][0]
            if len(stage1['rounds']) <= day2_start:
                print("Day 2 cutoff not ready yet")
                return
            d2r1pairings = stage1['rounds'][day2_start]["pairings"]
            day2players = [self.pdict[pid] for pid in d2r1pairings.values()]

            self.day2stats = {
                "elements": ElementStats(),
                "archedata": ArcheStats(),
                "champdata": ChampStats(),
                "regiondata": RegionStats(),
            }
            for p in day2players:
                if p.deck:
                    self.day2stats['elements'].add_deck(p.deck)
                    self.day2stats['archedata'].add_deck(p.deck)
                    self.day2stats['champdata'].add_deck(p.deck)
                else:
                    self.day2stats['elements'].add_unknown()
                    self.day2stats['archedata'].add_unknown()
                    self.day2stats['champdata'].add_unknown()
                self.day2stats['regiondata'].add_player(p)
        
        if self.top_cut:
            self.topcutstats = {
                "elements": ElementStats(),
                "archedata": ArcheStats(),
                "champdata": ChampStats(),
                "regiondata": RegionStats(),
            }
            for p in self.top_cut:
                if p.deck:
                    self.topcutstats['elements'].add_deck(p.deck)
                    self.topcutstats['archedata'].add_deck(p.deck)
                    self.topcutstats['champdata'].add_deck(p.deck)
                else:
                    self.topcutstats['elements'].add_unknown()
                    self.topcutstats['archedata'].add_unknown()
                    self.topcutstats['champdata'].add_unknown()
                self.topcutstats['regiondata'].add_player(p)

    def parse_top_cut(self):
        self.top_cut = []
        try:
            cutsize = int(self.evt.get("cutSize", "0"))
        except ValueError:
            print("Unknown cutSize value:", self.evt.get("cutSize"))
            cutsize = 0
        if not cutsize:
            if self.format != TEAM_STANDARD:
                self.winner = self.players[0]
            return
        
        finalstage = self.evt["stages"][-1]
        if finalstage["type"] != "single-elimination":
            print("Final stage isn't single elim??", finalstage)
            return
        
        for rnd in finalstage["rounds"]:
            if rnd == finalstage["rounds"][-1]:
                # Final stage of single elim needs special treatment
                tier = []
                matches = rnd["matches"]
                if len(matches) > 1:
                    if len(matches) > 2:
                        print("WARNING: 3+ matches in final stage of single-elim?")
                    
                    if self.format == TEAM_STANDARD:
                        bronze_contenders = [t.name.lower() for t in self.top_cut[-2:]]
                    else:
                        bronze_contenders = [p.id for p in self.top_cut[-2:]]

                    m0p0id = matches[0]["pairing"][0]["id"]
                    if self.format == TEAM_STANDARD:
                        # team standard IDs are inconsistently cased strings, so fix.
                        m0p0id = m0p0id.lower()
                    if m0p0id in bronze_contenders:
                        bronze_match = matches[0]
                        finals_match = matches[1]
                    else:
                        bronze_match = matches[1]
                        finals_match = matches[0]

                else:
                    bronze_match = None
                    finals_match = matches[0]
                
                if bronze_match:
                    if bronze_match["pairing"][0]["status"] == "loser":
                        place4_id = bronze_match["pairing"][0]["id"]
                        place3_id = bronze_match["pairing"][1]["id"]
                    else:
                        place3_id = bronze_match["pairing"][0]["id"]
                        place4_id = bronze_match["pairing"][1]["id"]
                    
                    if self.format == TEAM_STANDARD:
                        tier.append(self.teams[place4_id.lower()])
                        tier.append(self.teams[place3_id.lower()])
                    else:
                        tier.append(self.pdict[place4_id])
                        tier.append(self.pdict[place3_id])
                    # Remove 3rd/4th from top cut list so we can re-add them in
                    # the correct order below
                    self.top_cut = self.top_cut[:-2]
                
                if finals_match["pairing"][0]["status"] == "loser":
                    place2_id = finals_match["pairing"][0]["id"]
                    place1_id = finals_match["pairing"][1]["id"]
                else:
                    place1_id = finals_match["pairing"][0]["id"]
                    place2_id = finals_match["pairing"][1]["id"]
                if self.format == TEAM_STANDARD:
                    tier.append(self.teams[place2_id.lower()])
                    tier.append(self.teams[place1_id.lower()])
                else:
                    tier.append(self.pdict[place2_id])
                    tier.append(self.pdict[place1_id])
            
            else:
                tier = []
                for match in rnd["matches"]:
                    if match["pairing"][0]["status"] == "loser":
                        loser_id = match["pairing"][0]["id"]
                        if self.format == TEAM_STANDARD:
                            tier.append(self.teams[loser_id.lower()])
                        else:
                            tier.append(self.pdict[loser_id])
                    elif match["pairing"][1]["status"] == "loser":
                        loser_id = match["pairing"][1]["id"]
                        if self.format == TEAM_STANDARD:
                            tier.append(self.teams[loser_id.lower()])
                        else:
                            tier.append(self.pdict[loser_id])
                    else:
                        print("No loser in single-elim match?", match)
                tier.sort(key=lambda x:x.sortkey())

            self.top_cut += tier
            
        self.top_cut.reverse()
        # Correct placement for top cut
        for i,p in enumerate(self.top_cut):
            p.placement = i+1
        self.winner = self.top_cut[0]
        if self.format == TEAM_STANDARD:
            self.winner = None # use self.winning_team instead
    
    def calc_draw_pct(self):
        total_matches = 0
        ties = 0
        ties_not_00 = 0
        for stage in self.evt["stages"]:
            for rnd in stage["rounds"]:
                for match in rnd["matches"]:
                    if match["status"] == "started" or len(match["pairing"]) < 2:
                        # bye or ongoing match. Don't count it.
                        continue
                    total_matches += 1
                    if match["pairing"][0]["score"] == match["pairing"][1]["score"]:
                        ties += 1
                        if match["pairing"][0]["score"] != 0:
                            ties_not_00 += 1
        self.total_matches = total_matches
        self.draws = ties
        self.nat_draws = ties_not_00
        self.draw_pct = round(100*ties/total_matches, 1)
        self.nat_draw_pct = round(100*ties_not_00/total_matches, 1)
    
    def calc_sideboards(self):
        total_decks = 0
        sb_cards = defaultdict(int)
        
        for p in self.players:
            if p.deck:
                total_decks += 1
                for card_o in p.deck.dl["sideboard"]:
                    sb_cards[card_o["card"]] += 1
        sb_main_cards = defaultdict(int)
        for cardname in sb_cards.keys():
            for p in self.players:
                if p.deck:
                    if p.deck.quantity_of(cardname, search_sections=("sideboard",)):
                        # Skip decks that have the card boarded already
                        continue
                    if p.deck.quantity_of(cardname):
                        sb_main_cards[cardname] += 1

        sb_cards_sorted = []
        self.sideboard_stats = [{
                            "card": card, 
                            "pct": round(100*cc/total_decks,1),
                            "mb_pct": round(100*sb_main_cards[card]/total_decks,1),
                            "img": get_card_img(card),
                           } for card, cc in sb_cards.items()]
        self.sideboard_stats.sort(key=lambda x:x["pct"], reverse=True)
        

    def calc_headtohead(self, threshold=None, track_elo=False):
        return BattleChart.from_event(self, threshold=threshold, track_elo=track_elo)

    # def calc_conversion_rates(self):
    #     if len(self.evt['stages']) <= 1:
    #         return
        


    def __repr__(self):
        return f"Event#{self.id}"



class Team:
    def __init__(self, data):
        self.data = data
        self.name = data["name"]
        self.members = []

        self.wins = data["statsWins"]
        self.losses = data["statsLosses"]
        self.ties = data["statsTies"]
        self.byes = data["statsByes"]
        self.score = data["statsScore"]
        self.omw = data["statsPercentOMW"]
        self.gwp = data["statsPercentGW"]
        self.ogw = data["statsPercentOGW"]
        self.record = f"{self.wins + self.byes}-{self.losses}-{self.ties}"
    
    def sortkey(self):
        return self.score + (self.omw/100) + (self.gwp / 100000) + (self.ogw / 10000000)


class Team3v3Event(OmniEvent):
    def __init__(self, evt_id, force_redownload=False):
        super().__init__(evt_id, force_redownload)
        self.parse_teams()
        self.fix_placement()
        self.parse_top_cut()

    def parse_teams(self):
        teams = []
        for teamdata in self.evt["teams"]:
            team = Team(teamdata)
            teamplayers = []
            for p in self.players:
                if p.team == team.name:
                    teamplayers.append(p)
            teamplayers.sort(key=lambda x:x.seat)
            team.members = teamplayers
            teams.append(team)

        teams.sort(key=lambda x:x.sortkey(), reverse=True)
        self.teams = {t.name.lower(): t for t in teams}
        self.winning_team = teams[0]
    
    def fix_placement(self):
        for i, team in enumerate(self.teams.values()):
            team.placement = i+1
            for p in team.members:
                p.placement = i+1

    def calc_headtohead(self, threshold=None, track_elo=False):
        # Nah, it's just team standard.
        return {}
    
    def analyze_day2(self):
        # Maybe someday.
        pass
