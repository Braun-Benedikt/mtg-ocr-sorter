input_path = "cards/card_names_symspell.txt"
output_path = "cards/card_names_symspell_clean.txt"

with open(input_path, encoding="utf-8") as infile, open(output_path, "w", encoding="utf-8") as outfile:
    for line in infile:
        if not line.strip():
            continue
        try:
            term, count = line.strip().split("\t")
            cleaned_term = term.replace('"', '').strip()
            outfile.write(f"{cleaned_term}\t{count}\n")
        except ValueError:
            print(f"Überspringe ungültige Zeile: {line.strip()}")