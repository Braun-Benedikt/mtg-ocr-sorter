import unittest
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from web_app.database import init_db, add_card, add_sorting_rule, get_sorting_rules, delete_sorting_rule, evaluate_sorting_rules

class TestCustomSorting(unittest.TestCase):
    
    def setUp(self):
        """Set up test database"""
        # Use a test database
        import tempfile
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.original_db_path = None
        
        # Temporarily change the database path
        import web_app.database as db_module
        self.original_db_path = db_module.DATABASE_PATH
        db_module.DATABASE_PATH = self.temp_db.name
        
        # Initialize the test database
        init_db()
    
    def tearDown(self):
        """Clean up test database"""
        import web_app.database as db_module
        if self.original_db_path:
            db_module.DATABASE_PATH = self.original_db_path
        
        # Remove temporary database
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_add_sorting_rule(self):
        """Test adding a sorting rule"""
        rule_id = add_sorting_rule(
            name="High CMC Cards",
            attribute="cmc",
            operator=">",
            value="3",
            sort_direction="left"
        )
        
        self.assertIsNotNone(rule_id)
        if rule_id is not None:
            self.assertGreater(rule_id, 0)
    
    def test_get_sorting_rules(self):
        """Test retrieving sorting rules"""
        # Add a test rule
        add_sorting_rule(
            name="Test Rule",
            attribute="price",
            operator=">=",
            value="10.0",
            sort_direction="right"
        )
        
        rules = get_sorting_rules()
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]['name'], "Test Rule")
        self.assertEqual(rules[0]['attribute'], "price")
        self.assertEqual(rules[0]['operator'], ">=")
        self.assertEqual(rules[0]['value'], "10.0")
        self.assertEqual(rules[0]['sort_direction'], "right")
    
    def test_delete_sorting_rule(self):
        """Test deleting a sorting rule"""
        # Add a test rule
        rule_id = add_sorting_rule(
            name="Test Rule",
            attribute="cmc",
            operator="=",
            value="2",
            sort_direction="left"
        )
        
        # Verify it exists
        rules = get_sorting_rules()
        self.assertEqual(len(rules), 1)
        
        # Delete it
        if rule_id is not None:
            success = delete_sorting_rule(rule_id)
            self.assertTrue(success)
        
        # Verify it's gone
        rules = get_sorting_rules()
        self.assertEqual(len(rules), 0)
    
    def test_evaluate_sorting_rules_no_rules(self):
        """Test sorting evaluation when no rules exist"""
        # Add a test card
        card_data = {
            'name': 'Test Card',
            'cmc': 2.0,
            'price': 5.0,
            'color_identity': 'WU'
        }
        
        # Should default to right when no rules exist
        direction = evaluate_sorting_rules(card_data)
        self.assertEqual(direction, "right")
    
    def test_evaluate_sorting_rules_unrecognized_card(self):
        """Test sorting evaluation for unrecognized cards"""
        # Unrecognized card (no name)
        card_data = {
            'name': None,
            'cmc': 2.0
        }
        
        # Should always go left for unrecognized cards
        direction = evaluate_sorting_rules(card_data)
        self.assertEqual(direction, "left")
    
    def test_evaluate_sorting_rules_cmc_rule(self):
        """Test sorting evaluation with CMC rule"""
        # Add a rule for high CMC cards
        add_sorting_rule(
            name="High CMC Cards",
            attribute="cmc",
            operator=">",
            value="3",
            sort_direction="left"
        )
        
        # Test card with CMC > 3
        high_cmc_card = {
            'name': 'High CMC Card',
            'cmc': 5.0,
            'price': 10.0
        }
        direction = evaluate_sorting_rules(high_cmc_card)
        self.assertEqual(direction, "left")
        
        # Test card with CMC <= 3
        low_cmc_card = {
            'name': 'Low CMC Card',
            'cmc': 2.0,
            'price': 5.0
        }
        direction = evaluate_sorting_rules(low_cmc_card)
        self.assertEqual(direction, "right")  # Default when no rules match
    
    def test_evaluate_sorting_rules_price_rule(self):
        """Test sorting evaluation with price rule"""
        # Add a rule for expensive cards
        add_sorting_rule(
            name="Expensive Cards",
            attribute="price",
            operator=">=",
            value="20.0",
            sort_direction="right"
        )
        
        # Test expensive card
        expensive_card = {
            'name': 'Expensive Card',
            'cmc': 3.0,
            'price': 25.0
        }
        direction = evaluate_sorting_rules(expensive_card)
        self.assertEqual(direction, "right")
        
        # Test cheap card
        cheap_card = {
            'name': 'Cheap Card',
            'cmc': 1.0,
            'price': 5.0
        }
        direction = evaluate_sorting_rules(cheap_card)
        self.assertEqual(direction, "right")  # Default when no rules match
    
    def test_evaluate_sorting_rules_color_rule(self):
        """Test sorting evaluation with color rule"""
        # Add a rule for blue cards
        add_sorting_rule(
            name="Blue Cards",
            attribute="color_identity",
            operator="contains",
            value="U",
            sort_direction="left"
        )
        
        # Test blue card
        blue_card = {
            'name': 'Blue Card',
            'cmc': 2.0,
            'color_identity': 'U'
        }
        direction = evaluate_sorting_rules(blue_card)
        self.assertEqual(direction, "left")
        
        # Test non-blue card
        red_card = {
            'name': 'Red Card',
            'cmc': 2.0,
            'color_identity': 'R'
        }
        direction = evaluate_sorting_rules(red_card)
        self.assertEqual(direction, "right")  # Default when no rules match
    
    def test_evaluate_sorting_rules_multiple_rules(self):
        """Test sorting evaluation with multiple rules"""
        # Add multiple rules
        add_sorting_rule(
            name="High CMC Cards",
            attribute="cmc",
            operator=">",
            value="5",
            sort_direction="left"
        )
        
        add_sorting_rule(
            name="Expensive Cards",
            attribute="price",
            operator=">=",
            value="50.0",
            sort_direction="right"
        )
        
        # Test card that matches first rule (CMC > 5)
        high_cmc_card = {
            'name': 'High CMC Card',
            'cmc': 7.0,
            'price': 10.0
        }
        direction = evaluate_sorting_rules(high_cmc_card)
        self.assertEqual(direction, "left")  # Should match first rule
        
        # Test card that matches second rule (price >= 50)
        expensive_card = {
            'name': 'Expensive Card',
            'cmc': 3.0,
            'price': 60.0
        }
        direction = evaluate_sorting_rules(expensive_card)
        self.assertEqual(direction, "right")  # Should match second rule
        
        # Test card that matches no rules
        normal_card = {
            'name': 'Normal Card',
            'cmc': 3.0,
            'price': 10.0
        }
        direction = evaluate_sorting_rules(normal_card)
        self.assertEqual(direction, "right")  # Default when no rules match

if __name__ == '__main__':
    unittest.main() 