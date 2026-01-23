import json

DECK_SIMILARITY_FILE = "./data/decksim.json"

class DeckSim:
    def __init__(self):
        self.cache = {}
        self.initialized = False

    def load(self):
        try:
            with open(DECK_SIMILARITY_FILE, encoding="utf-8") as f:
                self.cache = json.load(f)
        except FileNotFoundError:
            print("Couldn't load deck similarity cache file, starting fresh")
        self.initialized = True

    def get(self, hash1, hash2):
        """
        Instead of re-calculating deck similarity every run, save it using deck hashes.
        Since similarity is mutual, instead of storing it twice, store it once and look
        it up using whichever hash is numerically lower.
        Returns similarity as a float in the range 0-100 representing a %,
        or None if the similarity of the two decks isn't cached.
        """
        if not self.initialized:
            self.load()
        lowhash, highhash = sorted( (hash1, hash2) )

        if lowhash in self.cache.keys():
            if highhash in self.cache[lowhash].keys():
                return self.cache[lowhash][highhash]
        return None

    def store(self, hash1, hash2, sim):
        if not self.initialized:
            self.load()
        lowhash, highhash = sorted( (hash1, hash2) )
        
        if lowhash in self.cache.keys():
            self.cache[lowhash][highhash] = sim
        else:
            self.cache[lowhash] = {highhash: sim}

    def write(self):
        with open(DECK_SIMILARITY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.cache, f)
