import pytest
import json
import os
import sqlite3
import sys
from pathlib import Path

# Add project root to sys.path to allow importing web_app modules
project_root_folder = Path(__file__).resolve().parent.parent
if str(project_root_folder) not in sys.path:
    sys.path.insert(0, str(project_root_folder))

from web_app.app import app as flask_app # Renamed to avoid conflict with fixture
# Import database functions that will be used.
# The DATABASE_PATH within database.py will be monkeypatched by the fixture.
from web_app.database import init_db, add_card, get_cards
import web_app.database # To allow monkeypatching web_app.database.DATABASE_PATH

# Use a different database for testing
TEST_DATABASE_NAME = 'test_magic_cards.db'
# Place it in the same directory as the original database for consistency
# This requires web_app.database.DATABASE_PATH to be known at this point.
# We assume the original DATABASE_PATH is like /path/to/web_app/magic_cards.db
# So, we get the parent directory of that.
ACTUAL_DATABASE_PATH_FROM_MODULE = web_app.database.DATABASE_PATH
TEST_DATABASE_PATH = os.path.join(os.path.dirname(ACTUAL_DATABASE_PATH_FROM_MODULE), TEST_DATABASE_NAME)


@pytest.fixture
def app_client():
    # Configure the app for testing
    flask_app.config['TESTING'] = True

    # Store original DB path from the imported module
    original_db_module_path = web_app.database.DATABASE_PATH

    # Monkeypatch database.py's DATABASE_PATH to use the test database path
    web_app.database.DATABASE_PATH = TEST_DATABASE_PATH

    # Ensure a clean database for each test run (before this specific test function)
    if os.path.exists(TEST_DATABASE_PATH):
        os.remove(TEST_DATABASE_PATH)

    # Initialize the database schema within an application context
    # init_db() will now use the monkeypatched TEST_DATABASE_PATH
    with flask_app.app_context():
        init_db()

    client = flask_app.test_client()
    yield client

    # Clean up: remove test database
    if os.path.exists(TEST_DATABASE_PATH):
        os.remove(TEST_DATABASE_PATH)

    # Restore original DB path in the module
    web_app.database.DATABASE_PATH = original_db_module_path


def test_add_and_get_card_with_new_fields(app_client):
    # Test adding a card with all new fields
    # app_client fixture ensures test DB is initialized and cleaned up.
    # Operations like add_card and get_cards need an app context if they rely on current_app
    # or if get_db_connection relies on app context implicitly.
    # Since our db functions get connection directly, app_context here is for good practice
    # and for flask_app.config['TESTING'] to be effective.
    with flask_app.app_context():
        card_id = add_card(
            name="Test Card",
            ocr_name_raw="Test Card Raw",
            price=1.99,
            color_identity="U",
            image_path="/path/to/local.jpg", # Still accepted
            cmc=2.0,
            type_line="Creature - Merfolk",
            image_uri="https://example.com/test_card.jpg"
        )
        assert card_id is not None

        cards = get_cards() # This should now use the test DB via patched DATABASE_PATH
        assert len(cards) == 1
        card = cards[0]
        assert card["name"] == "Test Card"
        assert card["price"] == 1.99
        assert card["cmc"] == 2.0
        assert card["type_line"] == "Creature - Merfolk"
        assert card["image_uri"] == "https://example.com/test_card.jpg"

def test_get_cards_endpoint(app_client):
    with flask_app.app_context():
        add_card("Card 1", price=5.0, cmc=3.0, type_line="Sorcery", image_uri="uri1", color_identity="R")
        add_card("Card 2", price=10.0, cmc=4.0, type_line="Instant", image_uri="uri2", color_identity="U")

    response = app_client.get('/cards')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    # Cards are ordered by timestamp DESC (most recent first)
    # Assuming Card 2 was added after Card 1, it should appear first.
    assert data[0]['name'] == 'Card 2'
    assert data[0]['cmc'] == 4.0
    assert data[0]['type_line'] == 'Instant'
    assert data[0]['image_uri'] == 'uri2'
    assert data[0]['color_identity'] == 'U'

    assert data[1]['name'] == 'Card 1'
    assert data[1]['cmc'] == 3.0
    assert data[1]['type_line'] == 'Sorcery'
    assert data[1]['image_uri'] == 'uri1'
    assert data[1]['color_identity'] == 'R'


def test_get_cards_filter_cmc(app_client):
    with flask_app.app_context():
        add_card("CMC3 Card", price=1.0, cmc=3.0, type_line="TypeA")
        add_card("CMC4 Card", price=2.0, cmc=4.0, type_line="TypeB")

    response = app_client.get('/cards?mana_cost=3')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['name'] == 'CMC3 Card'
    assert data[0]['cmc'] == 3.0

def test_get_cards_filter_max_price(app_client):
    with flask_app.app_context():
        add_card("Cheap Card", price=1.50, cmc=1.0)
        add_card("Mid Card", price=5.00, cmc=2.0)
        add_card("Expensive Card", price=10.00, cmc=3.0)
        add_card("Card No Price", price=None, cmc=4.0)


    response = app_client.get('/cards?max_price=5.00')
    assert response.status_code == 200
    data = json.loads(response.data)
    # Cards with price <= 5.00. Cards with NULL price are not included by `price <= ?`.
    assert len(data) == 2
    names = sorted([c['name'] for c in data])
    assert names == ["Cheap Card", "Mid Card"]

def test_get_cards_filter_cmc_and_max_price(app_client):
    with flask_app.app_context():
        add_card("Card A", price=1.0, cmc=2.0) # Match
        add_card("Card B", price=1.0, cmc=3.0) # No match (cmc)
        add_card("Card C", price=5.0, cmc=2.0) # No match (price)
        add_card("Card D", price=5.0, cmc=3.0) # No match

    response = app_client.get('/cards?mana_cost=2&max_price=1.50')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['name'] == 'Card A'

def test_get_cards_invalid_mana_cost(app_client):
    response = app_client.get('/cards?mana_cost=abc')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "Invalid mana_cost parameter" in data["error"]

def test_get_cards_invalid_max_price(app_client):
    response = app_client.get('/cards?max_price=xyz')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "Invalid max_price parameter" in data["error"]

def test_delete_card_endpoint(app_client):
    with flask_app.app_context():
        card_id = add_card("Deletable Card", price=1.0, cmc=1.0)
        assert card_id is not None

    response = app_client.delete(f'/cards/delete/{card_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == "Card deleted successfully"

    with flask_app.app_context():
        cards = get_cards()
        assert len(cards) == 0

def test_delete_card_not_found_endpoint(app_client):
    response = app_client.delete('/cards/delete/9999') # Assuming 9999 does not exist
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['error'] == "Card not found"

# It might be good to also test the /scan and /export/csv endpoints,
# but these are more complex due to camera interaction (mocking needed) and CSV content.
# The prompt focused on new fields and filtering, so these are covered.
# A test for / (index) could be added for completeness.
def test_index_route(app_client):
    response = app_client.get('/')
    assert response.status_code == 200
    assert b"Magic: The Gathering Card Scanner" in response.data # Check for a known string
    assert b"Filter by Max Price:" in response.data # Check for new UI element
    assert b"cardCountDisplay" in response.data # Check for new UI element
    assert b"totalPriceDisplay" in response.data # Check for new UI element
