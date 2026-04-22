import re
from collections import defaultdict
from datetime import datetime
from time import strftime, gmtime

from .cards import ELEMENTS, SPECIAL_ELEMENTS

OVERALL = "__overall__"
SPIRIT_ONLY = "Spirit Only"

def slugify(s):
    unacceptable_chars = re.compile(r"[^A-Za-z0-9 -]+")
    whitespace_regex = re.compile(r"\s+")
    s = re.sub(unacceptable_chars, "", s)
    s = re.sub(whitespace_regex, "-", s)
    if not s:
        s = "_"
    return s.lower()

def lineage(champname):
    return champname.split(",",1)[0]

ISOFMT = r"%Y-%m-%d"

def ms_to_date(time_ms):
    return strftime(ISOFMT, gmtime(time_ms/1000))

def date_to_ms(date_string, weebs_time=False):
    if weebs_time: # Weebs' seasons are set by CST in the USA
        tz = "+0500"
    else:
        tz = "+0000"
    d = datetime.strptime(date_string+tz, ISOFMT+"%z")
    ts = d.timestamp()
    return int(ts*1000)

def fix_case(cardname):
    repls = {
        "'S":"'s",
        "’S":"'s",
        " And ": " and ",
        " At ":" at ",
        " By ": " by ",
        " De ": " de ",
        " For ": " for ",
        " From ":" from ",
        " In ":" in ",
        " Into ":" into ",
        " Of ": " of ",
        "Mk Iii": "Mk III",
        "Mk Ii": "Mk II",
        " The ":" the ",
        " To ":" to ",
        " With ":" with ",
        ", with ": ", With ", # "Silvie, With the Pack" vs "Smack with Flute"
        "\u2019S": "'s",
    }
    cardname = cardname.title()
    for k,v in repls.items():
        cardname = cardname.replace(k,v)

    # Exceptions to the typical title casing for prepositions
    if cardname == "Claimed from Beyond":
        return "Claimed From Beyond"
    if cardname == "Protect Her at All Costs":
        return "Protect Her At All Costs"
    if cardname == "Seep into the Mind":
        return "Seep Into the Mind"
    if cardname == "Pole-Armed Steed":
        return "Pole-armed Steed"
    return cardname

def element_sortkey(el, inverse=False):
    """
    Key for sorting element strings.
    Sort elements with Norm first, then other basic elements alphabetically,
    then advanced elements alphabetically, then special elements like Exalted.
    """
    el = el.title()
    if el == "Norm":
        return "0"+el
    elif el in ELEMENTS: # Basic elements
        return "1"+el
    elif el in SPECIAL_ELEMENTS: # Just Exalted at the moment
        return "3"+el
    else:
        return "2"+el

class keydefaultdict(defaultdict):
    # https://stackoverflow.com/questions/2912231/is-there-a-clever-way-to-pass-the-key-to-defaultdicts-default-factory
    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError( key )
        else:
            ret = self[key] = self.default_factory(key)
            return ret


def rank_card(card):
    # card: object from carddata
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
    return rank + el_rank + "-" + card["name"].lower()

TEAM_STANDARD = "team-standard-3v3"

EVENT_TYPES = {
    "worlds": {
        "name": "Worlds",
        "elo": "1.5x",
        "ep": "1.5x",
        "shortname": "worlds",
    },
    "nationals": {
        "name": "Nationals",
        "elo": "1.25x",
        "ep": "1.4x",
        "shortname": "nationals",
    },
    "ascent": {
        "name": "Ascent",
        "elo": "1.25x",
        "ep": "1.2x",
        "shortname": "ascent",
    },
    "regionals": {
        "name": "Regionals",
        "elo": "1.0x",
        "ep": "1.1x",
        "shortname": "regionals",
    },
    "store-championships": {
        "name": "Store Champs",
        "elo": "1.0x",
        "ep": "1.1x",
        "shortname": "store-champs",
    },
    "regular": {
        "name": "Regular",
        "elo": "0.2x",
        "ep": "1.0x",
        "shortname": "regular",
    }
}

REGIONS = {
    "":   {"name": "Online", "flag": "🌐"},
    "AE": {"name": "United Arab Emirates","flag": "🇦🇪"},
    "AT": {"name": "Austria", "flag": "🇦🇹"},
    "AU": {"name": "Australia","flag": "🇦🇺"},
    "BE": {"name": "Belgium","flag": "🇧🇪"},
    "BN": {"name": "Brunei","flag": "🇧🇳"},
    "CA": {"name": "Canada","flag": "🇨🇦"},
    "CH": {"name": "Switzerland","flag": "🇨🇭"},
    "CL": {"name": "Chile", "flag": "🇨🇱"},
    "CN": {"name": "China", "flag": "🇨🇳"},
    "CR": {"name": "Costa Rica", "flag": "🇨🇷"},
    "CZ": {"name": "Czech Republic","flag":"🇨🇿"},
    "DE": {"name": "Germany","flag": "🇩🇪"},
    "DK": {"name": "Denmark","flag": "🇩🇰"},
    "ES": {"name": "Spain","flag": "🇪🇸"},
    "FI": {"name": "Finland","flag":"🇫🇮"},
    "FR": {"name": "France", "flag": "🇫🇷"},
    "GB": {"name": "United Kingdom","flag": "🇬🇧"},
    "GR": {"name": "Greece","flag": "🇬🇷"},
    "HK": {"name": "Hong Kong","flag": "🇭🇰"},
    "HR": {"name": "Croatia","flag": "🇭🇷"},
    "HU": {"name": "Hungary","flag": "🇭🇺"},
    "ID": {"name": "Indonesia","flag": "🇮🇩"},
    "IT": {"name": "Italy","flag": "🇮🇹"},
    "JP": {"name": "Japan","flag": "🇯🇵"},
    "KR": {"name": "South Korea","flag": "🇰🇷"},
    "KW": {"name": "Kuwait","flag": "🇰🇼"},
    "LV": {"name": "Latvia","flag": "🇱🇻"},
    "MX": {"name": "Mexico","flag": "🇲🇽"},
    "MY": {"name": "Malaysia","flag": "🇲🇾"},
    "NL": {"name": "Netherlands","flag": "🇳🇱"},
    "NO": {"name": "Norway","flag": "🇳🇴"},
    "NZ": {"name": "New Zealand","flag": "🇳🇿"},
    "PH": {"name": "Philippines","flag": "🇵🇭"},
    "PL": {"name": "Poland","flag": "🇵🇱"},
    "PR": {"name": "Puerto Rico","flag": "🇵🇷"},
    "PT": {"name": "Portugal","flag":"🇵🇹"},
    "SE": {"name": "Sweden","flag": "🇸🇪"},
    "SG": {"name": "Singapore","flag": "🇸🇬"},
    "SI": {"name": "Slovenia","flag":"🇸🇮"},
    "SK": {"name": "Slovakia","flag":"🇸🇰"},
    "TH": {"name": "Thailand", "flag": "🇹🇭"},
    "TW": {"name": "Taiwan","flag": "🇹🇼"},
    "UM": {"name": "United States Minor Outlying Islands", "flag": "🇺🇸"},
    "US": {"name": "United States of America","flag": "🇺🇸"},
}
