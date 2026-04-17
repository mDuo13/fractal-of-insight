TCG_ABBR = {
    # Mapping of official prefixes from Index : [list of abbreviations used by tcgcsv that may contain those cards]
    # not including cases where they match exactly
    "ALC 1st": ["ALC"],
    "AMB 1st": ["AMB1E"],
    "AMB": ["AMB1E"],
    "DTR 1st": ["DTR1E"],
    "DTR": ["DTR1E"],
    "EVP": ["EVP","EVP2","EVP3","EVP4"],
    "FTCA": ["FTC"],
    "HVN 1st": ["HVN"],
    "MRC 1st": ["MRC"],
    "MRC Alter": ["MH Alter"],
    "P22": ["P"],
    "P23": ["P"],
    "P24": ["P"],
    "P25": ["P"],
    "P26": ["P"],
    "PTMEVP": ["PHME"],
    "PTM 1st": ["PTM"],
    "PTMLGS": ["PTM"],
    "RDO 1st": ["RDO"],
    "RDOA": ["RDO"],
    "ReC-AUR": ["AURR"],
    "ReC-HVF": ["HVNFV"],
    "ReC-IDY": ["IDLCRS"],
    "ReC-SHD": ["SHD", "SHDLTE"],
    "ReC-SLM": ["SLM", "SLMLTE"],
    "ReC-BRV": ["BRLVST"],
}

TCGP_CARDNAMES = {
    # For cases where the data on TCGPlayer is entered inconsistently or has
    # additional info like variant number added to the card name.
    # May need to be updated if/when TCGP fixes their data.
    # Many DFCs incorrectly have separate listings per face.
    # Technically I could add curio foil and CSR entries here too for
    # completeness, but something is very weird if those are cheaper than the
    # regular versions.
    "Fatestone of Unrelenting // Cheetah of Bound Fury": [
        "Fatestone of Unrelenting",
        "Cheetah of Bound Fury",
    ],
    "Craggy Fatestone // Obstinate Cragback": [
        "Craggy Fatestone",
        "Obstinate Cragback",
    ],
    "Fatestone of Revelations // Young Wyrmling": [
        "Fatestone of Revelations",
        "Young Wyrmling",
    ],
    "Fatestone of Heaven // Heavenly Drake": [
        "Fatestone of Heaven",
        "Heavenly Drake",
    ],
    "Companion Fatestone // Fatebound Caracal": [
        "Companion Fatestone",
        "Fatebound Caracal",
    ],
    "Lavaplume Fatestone // Firebird Trailblazer": [
        "Lavaplume Fatestone",
        "Firebird Trailblazer",
    ],
    "Wrathful Slime": "WrathfulSlime",
    "Fabled Azurite Fatestone // Seiryuu, Azure Dragon": [
        #tcgp has both, but the one with the // is the sapphire promo only
        "Fabled Azurite Fatestone",
        "Fabled Azurite Fatestone // Seiryuu, Azure Dragon",
    ],
    "Overlapping Visages": [
        "Overlapping Visages (025A)",
        "Overlapping Visages (025B)",
    ],
    "Gemini Starbearer": "Gemini StarBearer",
    "Angelic Channeling": [
        "Angelic Channeling (044A)",
        "Angelic Channeling (044B)",
    ],
    "Seraphic Legion's Descent": [
        "Seraphic Legion's Descent (139A)",
        "Seraphic Legion's Descent (139B)",
    ],
}
