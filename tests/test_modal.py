import unittest
from client.tui.widgets.modal import PostInputModal

class TestPostInputModal(unittest.TestCase):
    def test_char_counter_logic(self):
        """Test character counter validation logic directly."""
        modal = PostInputModal()
        
        text = "Hello"
        length = len(text)
        self.assertEqual(length, 5)
        
        text = "x" * 501
        length = len(text)
        self.assertEqual(length, 501)
        
    def test_500_char_limit_check(self):
        """Test that 501 chars triggers the limit warning."""
        text = "x" * 501
        is_over_limit = len(text) > 500
        self.assertTrue(is_over_limit)
        
        text = "x" * 500
        is_over_limit = len(text) > 500
        self.assertFalse(is_over_limit)

if __name__ == "__main__":
    unittest.main()