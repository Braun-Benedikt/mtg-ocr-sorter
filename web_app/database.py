import sqlite3
import os
from datetime import datetime
from typing import Optional

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
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            cmc REAL,
            type_line TEXT,
            image_uri TEXT
        )
    ''')
    
    # Add custom sorting rules table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sorting_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            attribute TEXT NOT NULL,
            operator TEXT NOT NULL,
            value TEXT NOT NULL,
            sort_direction TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DATABASE_PATH}")

def add_card(name: str, ocr_name_raw: Optional[str] = None, price: Optional[float] = None, color_identity: Optional[str] = None, image_path: Optional[str] = None, cmc: float = 0.0, type_line: str = '', image_uri: str = ''):
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.now()
    cursor.execute('''
        INSERT INTO cards (name, ocr_name_raw, price, color_identity, image_path, timestamp, cmc, type_line, image_uri)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, ocr_name_raw, price, color_identity, image_path, timestamp, cmc, type_line, image_uri))
    card_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(f"Added card: {name}, ID: {card_id}")
    return card_id

def add_sorting_rule(name: str, attribute: str, operator: str, value: str, sort_direction: str):
    """Add a new custom sorting rule"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sorting_rules (name, attribute, operator, value, sort_direction)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, attribute, operator, value, sort_direction))
    rule_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(f"Added sorting rule: {name}, ID: {rule_id}")
    return rule_id

def get_sorting_rules():
    """Get all active sorting rules"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, name, attribute, operator, value, sort_direction, is_active, 
               strftime('%Y-%m-%d %H:%M:%S', created_at) as created_at
        FROM sorting_rules 
        WHERE is_active = 1
        ORDER BY created_at DESC
    ''')
    rules = cursor.fetchall()
    conn.close()
    return [dict(rule) for rule in rules]

def delete_sorting_rule(rule_id: int):
    """Delete a sorting rule by setting is_active to 0"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE sorting_rules SET is_active = 0 WHERE id = ?", (rule_id,))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    print(f"Attempted to delete sorting rule with ID: {rule_id}. Rows affected: {rows_affected}")
    return rows_affected > 0

def evaluate_sorting_rules(card_data):
    """Evaluate all active sorting rules against a card and return the sort direction"""
    if not card_data or not card_data.get('name'):
        return 'left'  # Default: unrecognized cards go left
    
    rules = get_sorting_rules()
    if not rules:
        return 'right'  # Default: recognized cards go right if no rules
    
    for rule in rules:
        if rule['is_active']:
            card_value = card_data.get(rule['attribute'])
            rule_value = rule['value']
            
            # Convert values for comparison
            try:
                if rule['attribute'] in ['cmc', 'price']:
                    card_value = float(card_value) if card_value is not None else 0.0
                    rule_value = float(rule_value)
                else:
                    card_value = str(card_value).lower() if card_value is not None else ''
                    rule_value = str(rule_value).lower()
            except (ValueError, TypeError):
                continue
            
            # Evaluate the condition
            condition_met = False
            if rule['operator'] == '>':
                if isinstance(card_value, (int, float)) and isinstance(rule_value, (int, float)):
                    condition_met = card_value > rule_value
            elif rule['operator'] == '>=':
                if isinstance(card_value, (int, float)) and isinstance(rule_value, (int, float)):
                    condition_met = card_value >= rule_value
            elif rule['operator'] == '<':
                if isinstance(card_value, (int, float)) and isinstance(rule_value, (int, float)):
                    condition_met = card_value < rule_value
            elif rule['operator'] == '<=':
                if isinstance(card_value, (int, float)) and isinstance(rule_value, (int, float)):
                    condition_met = card_value <= rule_value
            elif rule['operator'] == '=':
                condition_met = card_value == rule_value
            elif rule['operator'] == '!=':
                condition_met = card_value != rule_value
            elif rule['operator'] == 'contains':
                if isinstance(card_value, str) and isinstance(rule_value, str):
                    condition_met = rule_value in card_value
            elif rule['operator'] == 'starts_with':
                if isinstance(card_value, str) and isinstance(rule_value, str):
                    condition_met = card_value.startswith(rule_value)
            elif rule['operator'] == 'ends_with':
                if isinstance(card_value, str) and isinstance(rule_value, str):
                    condition_met = card_value.endswith(rule_value)
            
            if condition_met:
                return rule['sort_direction']
    
    # If no rules match, use default behavior
    return 'right'

def get_cards(color: Optional[str] = None, mana_cost: Optional[float] = None, max_price: Optional[float] = None):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT id, name, ocr_name_raw, price, color_identity, image_path, strftime('%Y-%m-%d %H:%M:%S', timestamp) as timestamp, cmc, type_line, image_uri FROM cards"
    conditions = []
    params = []

    if color:
        # Assuming color_identity is stored like "WUBRG" and we search for any character match
        # For exact match or partial match, the query might need adjustment
        # For now, let's assume 'color' is a single character like 'W', 'U', etc.
        # and we want to find cards that include this color in their color_identity.
        conditions.append("color_identity LIKE ?")
        params.append(f"%{color}%")

    if mana_cost is not None:
        conditions.append("cmc = ?")
        params.append(mana_cost)

    if max_price is not None:
        conditions.append("price <= ?")
        params.append(max_price)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY timestamp DESC"

    cursor.execute(query, params)
    cards = cursor.fetchall()
    conn.close()

    # Convert sqlite3.Row objects to dictionaries for easier JSON serialization
    return [dict(card) for card in cards]

def get_legendary_creatures():
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT id, name, ocr_name_raw, price, color_identity, image_path, strftime('%Y-%m-%d %H:%M:%S', timestamp) as timestamp, cmc, type_line, image_uri FROM cards WHERE type_line LIKE 'Legendary Creature%'"

    cursor.execute(query)
    cards = cursor.fetchall()
    conn.close()

    # Convert sqlite3.Row objects to dictionaries for easier JSON serialization
    return [dict(card) for card in cards]

def delete_card(card_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    conn.commit()
    rows_deleted = cursor.rowcount
    conn.close()
    print(f"Attempted to delete card with ID: {card_id}. Rows affected: {rows_deleted}")
    return rows_deleted > 0

if __name__ == '__main__':
    # Example usage:
    print("Initializing database...")
    init_db()
    print("Adding sample cards...")
    add_card("Sol Ring", ocr_name_raw="Sol Ring", price=1.50, color_identity="C", image_path="path/to/sol_ring.jpg", cmc=1.0, type_line="Artifact", image_uri="http://example.com/sol_ring.png")
    add_card("Island", ocr_name_raw="Island", price=0.10, color_identity="U", image_path="path/to/island.jpg", cmc=0.0, type_line="Basic Land — Island", image_uri="http://example.com/island.png")
    add_card("Lightning Bolt", ocr_name_raw="Lightning Bolt", price=0.50, color_identity="R", image_path="path/to/lightning_bolt.jpg", cmc=1.0, type_line="Instant", image_uri="http://example.com/lightning_bolt.png")

    print("\nAll cards:")
    all_c = get_cards()
    for c in all_c:
        print(f"ID: {c['id']}, Name: {c['name']}, OCR: {c['ocr_name_raw']}, Price: {c['price']}, Colors: {c['color_identity']}, Path: {c['image_path']}, Timestamp: {c['timestamp']}, CMC: {c['cmc']}, Type: {c['type_line']}, Scryfall URI: {c['image_uri']}")

    print("\nCards with color 'U':")
    blue_cards = get_cards(color="U")
    for c in blue_cards:
        print(f"ID: {c['id']}, Name: {c['name']}, Price: {c['price']}, CMC: {c['cmc']}, Type: {c['type_line']}")

    print("\nCards with CMC = 1.0:")
    cmc_1_cards = get_cards(mana_cost=1.0)
    for c in cmc_1_cards:
        print(f"ID: {c['id']}, Name: {c['name']}, Price: {c['price']}, CMC: {c['cmc']}, Type: {c['type_line']}")

    print("\nCards with Price <= 0.50:")
    cheap_cards = get_cards(max_price=0.50)
    for c in cheap_cards:
        print(f"ID: {c['id']}, Name: {c['name']}, Price: {c['price']}, CMC: {c['cmc']}, Type: {c['type_line']}")

    # Test DB initialization by running this script directly
    # To ensure the DB is created in the web_app directory as expected.
    # Check if the database file exists after running.
    if os.path.exists(DATABASE_PATH):
        print(f"Database file created successfully at {DATABASE_PATH}")
    else:
        print(f"Error: Database file not found at {DATABASE_PATH}")

    print("\nTesting delete_card function...")
    # Assuming card with ID 1 exists from previous sample data
    # First, let's add a card to ensure it exists
    test_card_id = add_card("Test Card for Deletion", ocr_name_raw="Test Del", price=0.10, color_identity="B", cmc=3.0, type_line="Creature", image_uri="http://example.com/test_card.png")
    if test_card_id:
        print(f"Added card with ID: {test_card_id} for deletion test.")
        cards_before_delete = get_cards()
        # print(f"Cards before delete (test card ID {test_card_id}): {[dict(c) for c in cards_before_delete]}") # Optional: very verbose

        delete_success = delete_card(test_card_id)
        print(f"Deletion of card ID {test_card_id} was {'successful' if delete_success else 'unsuccessful'}.")

        cards_after_delete = get_cards()
        # print(f"Cards after delete (test card ID {test_card_id}): {[dict(c) for c in cards_after_delete]}") # Optional: very verbose

        # Verify it's gone
        found_after_delete = any(c['id'] == test_card_id for c in cards_after_delete)
        if not found_after_delete:
            print(f"Card ID {test_card_id} successfully removed from database.")
        else:
            print(f"ERROR: Card ID {test_card_id} still found in database after deletion attempt.")
    else:
        print("Failed to add a card for deletion test.")

    # Example of trying to delete a non-existent card
    non_existent_id = 9999
    print(f"\nAttempting to delete non-existent card ID: {non_existent_id}")
    delete_non_existent_success = delete_card(non_existent_id)
    print(f"Deletion of non-existent card ID {non_existent_id} was {'successful' if delete_non_existent_success else 'unsuccessful (expected)'}.")

    print("\nLegendary Creatures:")
    legendary_cards = get_legendary_creatures()
    if legendary_cards:
        for lc in legendary_cards:
            print(f"ID: {lc['id']}, Name: {lc['name']}, Type: {lc['type_line']}")
    else:
        print("No legendary creatures found.")
