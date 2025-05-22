import os
from symspellpy import SymSpell, Verbosity

class CardNameCorrector:
    def __init__(self, dictionary_path: str):
        if not os.path.exists(dictionary_path):
            raise FileNotFoundError(f"Wörterbuchdatei nicht gefunden: {dictionary_path}")

        self.symspell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
        loaded = self.symspell.load_dictionary(dictionary_path, term_index=0, count_index=1, separator="\t")
        print("SymSpell geladen:", loaded)

        # Zusätzlich: Liste aller erlaubten Kartennamen als Set (für Verifikation)
        self.valid_names = set()
        with open(dictionary_path, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if parts:
                    self.valid_names.add(parts[0])


    def correct(self, text: str) -> str:
        suggestions = self.symspell.lookup(text, Verbosity.CLOSEST, max_edit_distance=2)
        if suggestions:
            return suggestions[0].term
        return text