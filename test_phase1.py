import json
import os
import unittest
from scraper.groww_scraper import GrowwScraper

class TestPhase1(unittest.TestCase):
    def setUp(self):
        self.scraper = GrowwScraper()
        self.test_url = "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
        self.data_file = "data/schemes/hdfc_mid_cap_direct_growth.json"

    def test_scraping_existence(self):
        """Test if scraping returns data and keys are present."""
        data = self.scraper.scrape_scheme_details(self.test_url)
        self.assertIsNotNone(data, "Scraping failed to return data")
        
        required_keys = [
            "scheme_name", "groww_scheme_url", "scraped_at", 
            "expense_ratio", "min_sip", "risk_level", "nav_value"
        ]
        for key in required_keys:
            self.assertIn(key, data, f"Key '{key}' missing from scraped data")
            self.assertIsNotNone(data[key], f"Value for '{key}' is None")

    def test_data_format(self):
        """Verify data formats (percentages, currency symbols)."""
        data = self.scraper.scrape_scheme_details(self.test_url)
        
        # Expense Ratio should contain %
        self.assertIn("%", data["expense_ratio"], f"Expense ratio {data['expense_ratio']} lacks '%'")
        
        # NAV and SIP should contain ₹ symbol (or unicode \u20b9)
        self.assertTrue("\u20b9" in data["nav_value"] or "₹" in data["nav_value"], 
                        f"NAV {data['nav_value']} lacks currency symbol")
        self.assertTrue("\u20b9" in data["min_sip"] or "₹" in data["min_sip"], 
                        f"Min SIP {data['min_sip']} lacks currency symbol")

    def test_sources_csv_exists(self):
        """Check if sources.csv was created and has content."""
        self.assertTrue(os.path.exists("data/sources.csv"), "sources.csv not found")
        with open("data/sources.csv", "r") as f:
            lines = f.readlines()
            self.assertGreater(len(lines), 1, "sources.csv is empty or missing headers")

if __name__ == "__main__":
    unittest.main()
