import unittest
import os
import sys
import shutil

# Add project root to sys.path to allow importing from recognition
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from recognition.fuzzy_match import CardNameCorrector

class TestCardNameCorrector(unittest.TestCase):

    def setUp(self):
        """Set up for test methods."""
        self.temp_dir = os.path.join(os.path.dirname(__file__), "temp_test_data")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        self.test_dict_path = os.path.join(self.temp_dir, "test_dictionary.txt")
        self.sample_dict_content = {
            "Lightning Bolt": 1,
            "Counterspell": 1,
            "Dark Ritual": 1,
            "Swords to Plowshares": 1,
            "Sol Ring": 1, # Added for more variety
            "Brainstorm": 1
        }
        
        with open(self.test_dict_path, 'w', encoding='utf-8') as f:
            for term, count in self.sample_dict_content.items():
                f.write(f"{term}\t{count}\n")
        
        self.corrector = CardNameCorrector(self.test_dict_path)

    def tearDown(self):
        """Tear down after test methods."""
        if os.path.exists(self.test_dict_path):
            os.remove(self.test_dict_path)
        if os.path.exists(self.temp_dir) and not os.listdir(self.temp_dir):
            os.rmdir(self.temp_dir)
        elif os.path.exists(self.temp_dir) and os.listdir(self.temp_dir): # If other files somehow end up there
             shutil.rmtree(self.temp_dir)


    def test_initialization_success(self):
        """Test successful initialization of CardNameCorrector."""
        self.assertIsNotNone(self.corrector)
        self.assertTrue(os.path.exists(self.test_dict_path)) # Ensure dict was created

    def test_initialization_file_not_found(self):
        """Test FileNotFoundError for an invalid dictionary path."""
        invalid_path = os.path.join(self.temp_dir, "non_existent_dictionary.txt")
        with self.assertRaises(FileNotFoundError):
            CardNameCorrector(invalid_path)

    def test_correct_exact_match(self):
        """Test correction with an exact match."""
        result = self.corrector.correct("Lightning Bolt")
        self.assertEqual(result, "Lightning Bolt")

    def test_correct_minor_typo(self):
        """Test correction with a minor typo."""
        result = self.corrector.correct("Lighning Bolt") # One 't' missing
        self.assertEqual(result, "Lightning Bolt")
        
        result_case_insensitive = self.corrector.correct("lighTning bOLT")
        self.assertEqual(result_case_insensitive, "Lightning Bolt")

    def test_correct_significant_typo(self):
        """Test correction with a more significant typo."""
        result = self.corrector.correct("Countrspel") # Missing 'e', 'l' transposed
        self.assertEqual(result, "Counterspell")
        
        result_swords = self.corrector.correct("Sords to Plowshare") # Missing 'w', 's'
        self.assertEqual(result_swords, "Swords to Plowshares")

    def test_correct_no_match(self):
        """Test correction with an input that has no close match."""
        # SymSpell's default behavior for no match (or below threshold) is to return the original term
        # if max_edit_distance is reasonably set during lookup.
        # The CardNameCorrector class uses default lookup parameters.
        original_term = "ThisIsNotACardNameEver"
        result = self.corrector.correct(original_term)
        self.assertEqual(result, original_term)

        original_term_2 = "XyzAbc123"
        result_2 = self.corrector.correct(original_term_2)
        self.assertEqual(result_2, original_term_2)

if __name__ == '__main__':
    unittest.main()
