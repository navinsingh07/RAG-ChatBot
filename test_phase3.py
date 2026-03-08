import unittest
import requests
import os
import time
from backend.main import classify_intent, QueryRequest, QueryResponse

class TestPhase3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # We need to run the server in the background for endpoint testing or test directly
        # For simplicity, we can mock or unit test the classification first
        pass

    def test_classify_intent_factual(self):
        """Test classifying factual queries."""
        self.assertEqual(classify_intent("What is the expense ratio?"), "FACTUAL")
        self.assertEqual(classify_intent("What is the lock-in period for ELSS?"), "FACTUAL")
        self.assertEqual(classify_intent("How can I download a statement?"), "FACTUAL")

    def test_classify_intent_advice(self):
        """Test classifying advice seeking queries."""
        self.assertEqual(classify_intent("Should I invest in HDFC Mid Cap?"), "ADVICE")
        self.assertEqual(classify_intent("Which is the best fund for retirement?"), "ADVICE")
        self.assertEqual(classify_intent("Suggest me some good stocks."), "ADVICE")

    def test_prompt_constraints(self):
        """Check if assistant refuses when context is empty or advice is asked."""
        # This will require Groq API Key and it actually calls the API
        # Only call if GROQ_API_KEY is present
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            self.skipTest("GROQ_API_KEY is missing")
        
        # Test directly with main.py logic or through local mock
        from backend.main import ask_question
        import asyncio
        
        request = QueryRequest(query="Which fund should I buy?")
        response = asyncio.run(ask_question(request))
        self.assertTrue(response.is_advice)
        self.assertIn("can't provide investment advice", response.answer)

    def test_source_citation_rule(self):
        """Check if source link is provided and official."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            self.skipTest("GROQ_API_KEY is missing")
            
        from backend.main import ask_question
        import asyncio
        
        request = QueryRequest(query="What is the expense ratio of HDFC Mid Cap?")
        response = asyncio.run(ask_question(request))
        # Ensure it's not a refusal
        if not response.is_advice:
            self.assertIsNotNone(response.source)
            self.assertIn("http", response.source)
            # Ensure Groww is not the cited source (Groww is for data provider)
            self.assertNotIn("groww.in", response.source)

if __name__ == "__main__":
    unittest.main()
