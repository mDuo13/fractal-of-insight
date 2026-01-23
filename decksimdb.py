import sqlite3

DECK_SIMILARITY_DB = "./data/decksim.db"

class DeckSimDB:
    def __init__(self):
        self.con = sqlite3.connect(DECK_SIMILARITY_DB, autocommit=True)
        # self.cur = con.cursor()
        self.setup_db()
        self.id_cache = {}
    
    def setup_db(self):
        self.con.execute("""CREATE TABLE IF NOT EXISTS decks(
            id INTEGER PRIMARY KEY,
            deck_hash TEXT UNIQUE NOT NULL
        )""")
        self.con.execute("""CREATE TABLE IF NOT EXISTS decksim(
            deck1 INTEGER NOT NULL,
            deck2 INTEGER NOT NULL,
            sim INTEGER NOT NULL,
            PRIMARY KEY(deck1, deck2),
            FOREIGN KEY(deck1) REFERENCES decks(id),
            FOREIGN KEY(deck2) REFERENCES decks(id)
        ) WITHOUT ROWID""")

    def _get_id(self, hash:str):
        if hash in self.id_cache.keys():
            return self.id_cache[hash]
        res = self.con.execute("SELECT id FROM decks WHERE deck_hash = ?", (hash,)).fetchone()
        if not res:
            #print("Unknown deck hash:", hash) #TODO: remove
            return None
        id = res[0]
        self.id_cache[hash] = id
        return id
    
    def get(self, hash1:str, hash2:str):
        lowhash, highhash = sorted( (hash1, hash2) )

        id1 = self._get_id(lowhash)
        id2 = self._get_id(highhash)
        if (id1 is None or id2 is None):
            # One of the decks isn't in the DB at all
            return None
        
        row = self.con.execute("""
            SELECT sim FROM decksim WHERE deck1 = ? AND deck2 = ? LIMIT 1
        """, (id1, id2)).fetchone()
        # row = self.con.execute(
        #     """SELECT ds.sim FROM decksim ds
        #         JOIN decks d1 ON ds.deck1 = d1.id
        #         JOIN decks d2 ON ds.deck2 = d2.id
        #         WHERE d1.deck_hash = ? AND d2.deck_hash = ?
        #         LIMIT 1""",
        #     (lowhash, highhash)
        # )
        if not row:
            #print(f"Similarity not in cache for {hash1}:{hash2}")
            return None
        return row[0] / 10
    
    def store(self, hash1:str, hash2:str, sim):
        lowhash, highhash = sorted( (hash1, hash2) )
        simint = sim * 10

        self.con.executemany("INSERT OR IGNORE INTO decks (deck_hash) VALUES (?)",
            ((lowhash,), (highhash,))
        )
        id1 = self._get_id(lowhash)
        id2 = self._get_id(highhash)
        if (id1 is None or id2 is None):
            print("Error! ID not found for deck hash despite just inserting it?!")
            return
        
        self.con.execute(
            "INSERT INTO decksim (deck1, deck2, sim) VALUES (?, ?, ?)",
            (id1, id2, simint)
        )

    def migrate_from_json(self):
        import json
        DECK_SIMILARITY_FILE = "./data/decksim.json"
        with open(DECK_SIMILARITY_FILE, encoding="utf-8") as f:
            jsoncache = json.load(f)

        data = ( (k,) for k in jsoncache.keys() )

        self.con.executemany("INSERT OR IGNORE INTO decks (deck_hash) VALUES (?)",
            data
        )
        
        for lowhash, v in jsoncache.items():
            for highhash, sim in v.items():
                self.store(lowhash, highhash, sim)
