import unittest
import os
from processor.vector_store_manager import VectorStoreManager
from processor.scheme_service import SchemeService

class TestPhase2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vsm = VectorStoreManager()
        cls.ss = SchemeService()

    def test_vector_store_search(self):
        """Test if vector store can find relevant chunks for a common query."""
        results = self.vsm.search("What is the expense ratio?", n_results=3)
        self.assertGreater(len(results['documents'][0]), 0, "No results found in vector store")
        
        # Check if any result mentions 'expense ratio'
        all_text = " ".join(results['documents'][0]).lower()
        self.assertIn("expense", all_text, "Search results don't contain 'expense'")

    def test_scheme_fuzzy_lookup(self):
        """Test if scheme service can fuzzy match scheme names."""
        # Querying with partial name
        scheme = self.ss.get_scheme_by_name("HDFC Mid Cap")
        self.assertIsNotNone(scheme, "Fuzzy matching failed for 'HDFC Mid Cap'")
        self.assertIn("Mid Cap", scheme['scheme_name'])

    def test_deterministic_field_access(self):
        """Test getting specific structured fields."""
        val = self.ss.get_field("HDFC Mid Cap", "expense_ratio")
        self.assertIsNotNone(val, "Failed to retrieve expense_ratio field")
        self.assertIn("%", str(val), "Expense ratio format is unexpected")

    def test_vector_store_metadata(self):
        """Check if metadata is preserved in search results."""
        results = self.vsm.search("ELSS lock in")
        metadatas = results['metadatas'][0]
        self.assertGreater(len(metadatas), 0)
        # Check for a source_url in metadata
        self.assertTrue(any("source_url" in m for m in metadatas), "Metadata missing source_url")

if __name__ == "__main__":
    unittest.main()
