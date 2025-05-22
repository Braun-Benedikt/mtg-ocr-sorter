import requests
import os

def fetch_card_names_from_scryfall() -> list[str]:
    url = "https://api.scryfall.com/catalog/card-names"
    response = requests.get(url)
    if response.status_code != 200:
        raise RuntimeError("Scryfall API konnte nicht erreicht werden.")
    data = response.json()
    return list(set(data["data"])) # Duplikate entfernen

def clean_names(names: list[str]) -> list[str]: # Optional: Token, Unkarten, doppelte Namen, Basic Lands ausschließen?
    return sorted(name for name in names if name.strip() and not name.lower().startswith("token"))

def save_symspell_dictionary(names: list[str], out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for name in names: f.write(f"{name}\t1\n")

if __name__ == "__main__":
    print("📡 Lade Kartennamen von Scryfall...")
    all_names = fetch_card_names_from_scryfall()
    print(f"✅ {len(all_names)} Namen geladen.")

    cleaned_names = clean_names(all_names)
    print(f"✨ {len(cleaned_names)} gültige Namen nach Filter.")

    output_file = "cards/card_names_symspell.txt"
    save_symspell_dictionary(cleaned_names, output_file)
    print(f"📁 Gespeichert als: {output_file}")