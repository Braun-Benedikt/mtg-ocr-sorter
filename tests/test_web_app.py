import os
import sys
import unittest
import tempfile
from pathlib import Path

# Add project root to sys.path to allow importing web_app modules
project_root_folder = Path(__file__).resolve().parent.parent
if str(project_root_folder) not in sys.path:
    sys.path.insert(0, str(project_root_folder))

from web_app.app import app as flask_app
# The following imports assume that web_app.database can be reconfigured
# to use a different DATABASE_PATH for testing.
from web_app.database import init_db as actual_init_db
from web_app.database import add_card as actual_add_card
from web_app.database import get_cards as actual_get_cards
from web_app.database import delete_card as actual_delete_card
from web_app.database import get_db_connection as actual_get_db_connection
import web_app.database # To modify its DATABASE_PATH

class WebAppTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.test_db_path = tempfile.mkstemp(suffix='.db')
        os.close(cls.db_fd) # Close file descriptor, tempfile.mkstemp opens it

        cls.original_db_path = web_app.database.DATABASE_PATH
        web_app.database.DATABASE_PATH = cls.test_db_path

        flask_app.config['TESTING'] = True
        flask_app.config['DATABASE'] = cls.test_db_path # For Flask app, if it uses this config
        cls.client = flask_app.test_client()

        # Ensure the schema is created in the new test_db_path
        # This init_db call should now use the overridden web_app.database.DATABASE_PATH
        actual_init_db()

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.test_db_path)
        web_app.database.DATABASE_PATH = cls.original_db_path

    def setUp(self):
        # Clean all data from tables before each test
        conn = actual_get_db_connection() # Uses the overridden path
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cards")
        # Add other tables here if they exist and need cleaning
        conn.commit()
        conn.close()

    def tearDown(self):
        # Optional: could also clean tables here instead of setUp if preferred
        pass

    # --- Database Function Tests ---
    def test_db_add_and_delete_card(self):
        # Use actual_add_card, actual_delete_card, actual_get_cards
        card_id = actual_add_card(name="Test Card", ocr_name_raw="Test", price=1.0, color_identity="W")
        self.assertIsNotNone(card_id, "Card should be added and return an ID.")

        retrieved_card_before_delete = actual_get_cards()
        self.assertEqual(len(retrieved_card_before_delete), 1)
        self.assertEqual(retrieved_card_before_delete[0]['id'], card_id)

        success = actual_delete_card(card_id)
        self.assertTrue(success, "delete_card should return True for a successful deletion.")

        retrieved_cards_after_delete = actual_get_cards()
        self.assertEqual(len(retrieved_cards_after_delete), 0, "Card should be deleted from the database.")

    def test_db_delete_non_existent_card(self):
        success = actual_delete_card(99999) # Assuming this ID doesn't exist
        self.assertFalse(success, "delete_card should return False for a non-existent card.")

    # --- API Endpoint Tests ---
    def test_api_delete_card_success(self):
        card_id = actual_add_card(name="API Test Card", ocr_name_raw="API Test", price=2.0, color_identity="B")
        self.assertIsNotNone(card_id)

        response = self.client.delete(f'/cards/delete/{card_id}')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data['message'], "Card deleted successfully")

        cards_in_db = actual_get_cards()
        self.assertEqual(len(cards_in_db), 0)

    def test_api_delete_card_not_found(self):
        response = self.client.delete('/cards/delete/99999') # Non-existent ID
        self.assertEqual(response.status_code, 404)
        json_data = response.get_json()
        self.assertEqual(json_data['error'], "Card not found")

if __name__ == '__main__':
    unittest.main()
