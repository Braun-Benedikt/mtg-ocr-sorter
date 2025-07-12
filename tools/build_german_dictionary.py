import requests
import os
import time

def fetch_german_card_names_from_scryfall() -> list[str]:
    """Fetch German card names from Scryfall API"""
    german_names = []
    
    # Get all cards with German printings
    url = "https://api.scryfall.com/cards/search"
    params = {
        "q": "lang:de",  # German language cards
        "unique": "cards"  # Get unique cards, not all printings
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Process all pages
        while True:
            for card in data.get('data', []):
                # Get the German name if available
                if 'printed_name' in card:
                    german_names.append(card['printed_name'])
                elif 'name' in card:
                    # Fallback to English name if no German name
                    german_names.append(card['name'])
            
            # Check if there are more pages
            if data.get('has_more', False):
                time.sleep(0.1)  # Rate limiting
                response = requests.get(data['next_page'])
                response.raise_for_status()
                data = response.json()
            else:
                break
                
    except requests.RequestException as e:
        print(f"Error fetching German cards: {e}")
        return []
    
    return list(set(german_names))  # Remove duplicates

def fetch_english_card_names_from_scryfall() -> list[str]:
    """Fetch English card names from Scryfall API"""
    url = "https://api.scryfall.com/catalog/card-names"
    response = requests.get(url)
    if response.status_code != 200:
        raise RuntimeError("Scryfall API could not be reached.")
    data = response.json()
    return list(set(data["data"]))

def clean_names(names: list[str]) -> list[str]:
    """Clean card names by removing tokens and invalid entries"""
    return sorted(name for name in names if name.strip() and not name.lower().startswith("token"))

def save_symspell_dictionary(names: list[str], out_path: str):
    """Save names to SymSpell dictionary format"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for name in names:
            f.write(f"{name}\t1\n")

def create_multilingual_dictionary(english_names: list[str], german_names: list[str], out_path: str):
    """Create a combined dictionary with both English and German names"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    # Combine names, giving priority to English names for duplicates
    combined_names = set()
    
    # Add English names first
    for name in english_names:
        combined_names.add(name)
    
    # Add German names (English names take priority for duplicates)
    for name in german_names:
        combined_names.add(name)
    
    # Save combined dictionary
    with open(out_path, "w", encoding="utf-8") as f:
        for name in sorted(combined_names):
            f.write(f"{name}\t1\n")

if __name__ == "__main__":
    print("📡 Loading German card names from Scryfall...")
    german_names = fetch_german_card_names_from_scryfall()
    print(f"✅ {len(german_names)} German names loaded.")
    
    print("📡 Loading English card names from Scryfall...")
    english_names = fetch_english_card_names_from_scryfall()
    print(f"✅ {len(english_names)} English names loaded.")
    
    # Clean names
    cleaned_german = clean_names(german_names)
    cleaned_english = clean_names(english_names)
    print(f"✨ {len(cleaned_german)} valid German names after filtering.")
    print(f"✨ {len(cleaned_english)} valid English names after filtering.")
    
    # Save individual dictionaries
    german_output = "cards/card_names_german_symspell.txt"
    save_symspell_dictionary(cleaned_german, german_output)
    print(f"📁 German dictionary saved as: {german_output}")
    
    english_output = "cards/card_names_english_symspell.txt"
    save_symspell_dictionary(cleaned_english, english_output)
    print(f"📁 English dictionary saved as: {english_output}")
    
    # Save combined multilingual dictionary
    combined_output = "cards/card_names_multilingual_symspell.txt"
    create_multilingual_dictionary(cleaned_english, cleaned_german, combined_output)
    print(f"📁 Multilingual dictionary saved as: {combined_output}")
    
    print("\n🎯 Dictionary creation complete!")
    print("Use the multilingual dictionary for best results with both English and German cards.") 