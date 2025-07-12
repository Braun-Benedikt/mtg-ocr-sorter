import re
import os

def clean_german_card_names(input_file: str, output_file: str):
    """Clean German card names for SymSpell dictionary"""
    
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found.")
        return
    
    cleaned_names = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            # Split by tab to get name and count
            parts = line.split('\t')
            if len(parts) < 1:
                continue
                
            name = parts[0]
            
            # Skip empty names
            if not name:
                continue
            
            # Clean the name
            cleaned_name = clean_single_name(name)
            
            if cleaned_name:
                cleaned_names.append(cleaned_name)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_names = []
    for name in cleaned_names:
        if name not in seen:
            seen.add(name)
            unique_names.append(name)
    
    # Sort alphabetically
    unique_names.sort()
    
    # Save cleaned names
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        for name in unique_names:
            f.write(f"{name}\t1\n")
    
    print(f"Cleaned {len(cleaned_names)} names to {len(unique_names)} unique names.")
    print(f"Saved to: {output_file}")

def clean_single_name(name: str) -> str:
    """Clean a single card name"""
    
    # Remove extra whitespace
    name = name.strip()
    
    # Skip if empty after cleaning
    if not name:
        return ""
    
    # Remove special characters that might cause issues
    # Keep German umlauts (ä, ö, ü) and ß
    # Remove other special characters that might interfere with OCR
    name = re.sub(r'[^\w\säöüßÄÖÜ\-]', '', name)
    
    # Normalize whitespace
    name = re.sub(r'\s+', ' ', name)
    
    # Skip names that are too short or too long
    if len(name) < 2 or len(name) > 100:
        return ""
    
    # Skip names that are just numbers or special characters
    if re.match(r'^[\d\s\-]+$', name):
        return ""
    
    return name

if __name__ == "__main__":
    input_file = "cards/card_names_german_symspell.txt"
    output_file = "cards/card_names_german_symspell_clean.txt"
    
    print("🧹 Cleaning German card names...")
    clean_german_card_names(input_file, output_file)
    print("✅ German card names cleaned successfully!") 