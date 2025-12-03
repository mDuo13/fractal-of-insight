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
    "PTMEVP": ["PHME"],
    "PTM 1st": ["PTM"],
    "PTMLGS": ["PTM"],
    "ReC-HVF": ["HVNFV"],
    "ReC-IDY": ["IDLCRS"],
    "ReC-SHD": ["SHD", "SHDLTE"],
    "ReC-SLM": ["SLM", "SLMLTE"],
    "ReC-BRV": ["BRLVST"],
}

TCGP_CARDNAMES = {
    # For cases where the data on TCGPlayer is entered inconsistently.
    # May need to be updated if/when TCGP fixes their data
    "Fatestone of Unrelenting // Cheetah of Bound Fury": "Fatestone of Unrelenting",
    "Craggy Fatestone // Obstinate Cragback": "Craggy Fatestone",
    "Fatestone of Revelations // Young Wyrmling": "Fatestone of Revelations",
    "Fatestone of Heaven // Heavenly Drake": "Fatestone of Heaven",
    "Companion Fatestone // Fatebound Caracal": "Companion Fatestone",
    "Lavaplume Fatestone // Firebird Trailblazer": "Lavaplume Fatestone",
    "Wrathful Slime": "WrathfulSlime",
    "Fabled Azurite Fatestone // Seiryuu, Azure Dragon": "Fabled Azurite Fatestone", #tcgp has both, but the one with the // is the sapphire promo only
}
