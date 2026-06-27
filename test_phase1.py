import json
import os
import unittest
from playwright.sync_api import sync_playwright
from scraper.groww_scraper import GrowwScraper

class TestPhase1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)
        cls.context = cls.browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        cls.page = cls.context.new_page()
        cls.scraper = GrowwScraper()
        cls.test_url = "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def test_scraping_existence(self):
        """Test if scraping returns data and keys are present."""
        data = self.scraper.scrape_scheme_details(self.page, self.test_url)
        self.assertIsNotNone(data, "Scraping failed to return data")
        
        required_keys = [
            "scheme_name", "groww_scheme_url", "last_scraped_at", 
            "expense_ratio", "minimum_sip", "risk_level", "nav"
        ]
        for key in required_keys:
            self.assertIn(key, data, f"Key '{key}' missing from scraped data")
            self.assertIsNotNone(data[key], f"Value for '{key}' is None")

    def test_data_format(self):
        """Verify data formats (percentages, currency symbols)."""
        data = self.scraper.scrape_scheme_details(self.page, self.test_url)
        
        # Expense Ratio should contain %
        self.assertIn("%", data["expense_ratio"], f"Expense ratio {data['expense_ratio']} lacks '%'")
        
        # NAV and SIP should contain ₹ symbol (or unicode \u20b9)
        self.assertTrue(isinstance(data["nav"], (int, float)), "NAV should be a number")
        self.assertTrue("\u20b9" in data["minimum_sip"] or "₹" in data["minimum_sip"], 
                        f"Min SIP {data['minimum_sip']} lacks currency symbol")

    def test_sources_csv_exists(self):
        """Check if sources.csv was created and has content."""
        self.assertTrue(os.path.exists("data/sources.csv"), "sources.csv not found")
        with open("data/sources.csv", "r") as f:
            lines = f.readlines()
            self.assertGreater(len(lines), 1, "sources.csv is empty or missing headers")

if __name__ == "__main__":
    unittest.main()

