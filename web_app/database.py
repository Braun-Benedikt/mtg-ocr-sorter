import sqlite3
import os
from datetime import datetime

DATABASE_NAME = 'magic_cards.db'
DATABASE_PATH = os.path.join(os.path.dirname(__file__), DATABASE_NAME)

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ocr_name_raw TEXT,
            price REAL,
            color_identity TEXT,
            image_path TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print(f"Database initialized at {DATABASE_PATH}")

def add_card(name: str, ocr_name_raw: str = None, price: float = None, color_identity: str = None, image_path: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.now()
    cursor.execute('''
        INSERT INTO cards (name, ocr_name_raw, price, color_identity, image_path, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, ocr_name_raw, price, color_identity, image_path, timestamp))
    card_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(f"Added card: {name}, ID: {card_id}")
    return card_id

def get_cards(color: str = None, mana_cost: int = None): # Mana cost filter to be implemented later if applicable
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT id, name, ocr_name_raw, price, color_identity, image_path, strftime('%Y-%m-%d %H:%M:%S', timestamp) as timestamp FROM cards"
    conditions = []
    params = []

    if color:
        # Assuming color_identity is stored like "WUBRG" and we search for any character match
        # For exact match or partial match, the query might need adjustment
        # For now, let's assume 'color' is a single character like 'W', 'U', etc.
        # and we want to find cards that include this color in their color_identity.
        conditions.append("color_identity LIKE ?")
        params.append(f"%{color}%")

    # Mana cost filtering is not directly supported by the current card data schema.
    # Scryfall API provides 'cmc' (converted mana cost) which is not currently stored.
    # This will be a placeholder or needs schema adjustment if 'mana_cost' is critical.
    # For now, the mana_cost parameter is ignored in the SQL query.
    if mana_cost is not None:
        # Placeholder: print("Mana cost filtering is not yet fully implemented for the current schema.")
        # If 'cmc' or similar was stored, it would be:
        # conditions.append("mana_cost = ?") # or cmc = ?
        # params.append(mana_cost)
        pass

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY timestamp DESC"

    cursor.execute(query, params)
    cards = cursor.fetchall()
    conn.close()

    # Convert sqlite3.Row objects to dictionaries for easier JSON serialization
    return [dict(card) for card in cards]

if __name__ == '__main__':
    # Example usage:
    print("Initializing database...")
    init_db()
    print("Adding sample cards...")
    add_card("Sol Ring", ocr_name_raw="Sol Ring", price=1.50, color_identity="C", image_path="path/to/sol_ring.jpg")
    add_card("Island", ocr_name_raw="Island", price=0.10, color_identity="U", image_path="path/to/island.jpg")
    add_card("Lightning Bolt", ocr_name_raw="Lightning Bolt", price=0.50, color_identity="R", image_path="path/to/lightning_bolt.jpg")

    print("\nAll cards:")
    all_c = get_cards()
    for c in all_c:
        print(dict(c))

    print("\nCards with color 'U':")
    blue_cards = get_cards(color="U")
    for c in blue_cards:
        print(dict(c))

    # Test DB initialization by running this script directly
    # To ensure the DB is created in the web_app directory as expected.
    # Check if the database file exists after running.
    if os.path.exists(DATABASE_PATH):
        print(f"Database file created successfully at {DATABASE_PATH}")
    else:
        print(f"Error: Database file not found at {DATABASE_PATH}")
