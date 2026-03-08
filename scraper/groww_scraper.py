import json
import os
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

class GrowwScraper:
    BASE_URL = "https://groww.in"
    AMC_URL = "https://groww.in/mutual-funds/amc/hdfc-mutual-funds"
    DATA_DIR = "data/schemes"

    def __init__(self):
        if not os.path.exists(self.DATA_DIR):
            os.makedirs(self.DATA_DIR)

    def crawl_amc_page(self, page):
        print(f"Loading AMC page: {self.AMC_URL}")
        page.goto(self.AMC_URL, wait_until="networkidle")
        
        # Groww AMC page lists schemes in anchor tags.
        # We target links containing '/mutual-funds/' and 'direct-growth' for factual consistency.
        # We need to extract them from the page.
        scheme_links = page.locator("a[href*='/mutual-funds/']").all()
        urls = []
        for link in scheme_links:
            href = link.get_attribute("href")
            if href and ("direct-growth" in href or "direct-idcw" in href):
                full_url = self.BASE_URL + href if href.startswith('/') else href
                if full_url not in urls:
                    urls.append(full_url)
        
        # Limit to 3-5 schemes for initial Phase 1 proper collection as requested
        # (Though we can collect more if found)
        print(f"Discovered {len(urls)} scheme URLs.")
        return urls[:5] # Target 5 schemes

    def scrape_scheme_details(self, page, url):
        print(f"Scraping: {url}")
        page.goto(url, wait_until="load")
        time.sleep(2) # Give a bit of extra time for JS
        
        # Scroll to bottom to ensure all detail sections are rendered
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)

        details = {}
        
        # Field 1: scheme_name
        try:
            details["scheme_name"] = page.locator("h1").inner_text().strip()
        except:
            details["scheme_name"] = None

        # Field 2: amc_name
        details["amc_name"] = "HDFC Mutual Fund"

        # Field 3, 4, 10: category, sub_category, risk_level
        try:
            # Look for common MF categories and risk labels in any div/span
            categories = ["Equity", "Debt", "Hybrid", "Solution Oriented", "Other"]
            details["category"] = next((c for c in categories if page.get_by_text(c, exact=True).count() > 0), None)
            
            risk_labels = ["Very High", "High", "Moderate", "Low", "Low to Moderate", "Moderately High"]
            details["risk_level"] = next((r + " Risk" for r in risk_labels if page.get_by_text(r + " Risk", exact=True).count() > 0), None)

            # Sub-category is harder, usually near category. 
            # Let's try to find badges near h1
            all_badges = page.locator("h1 ~ div span, h1 ~ div div").all_inner_texts()
            # Filter out non-category stuff
            if len(all_badges) > 0:
                # Sub-category is usually the one after category in the visual flow
                # But let's just take all and pick
                details["sub_category"] = next((b.strip() for b in all_badges if b.strip() and b.strip() not in categories and "Risk" not in b), None)
        except:
            pass

        def get_stat_value(label):
            try:
                # Direct sibling or adjacent in text flow
                locator = page.get_by_text(label, exact=False).first
                if locator:
                    # Look for the value in the next element or same container
                    parent = locator.locator("xpath=..")
                    # If label is in its own div, get the next div
                    if len(parent.inner_text().split("\n")) < 2:
                        parent = parent.locator("xpath=following-sibling::*").first
                    
                    text = parent.inner_text().split("\n")
                    # The value is usually the first line that isn't the label
                    for t in text:
                        if t.strip() and label.lower() not in t.lower():
                            return t.strip()
                return None
            except:
                return None

        # Field 5, 7, 12: expense_ratio, sip, fund_size
        details["expense_ratio"] = get_stat_value("Expense ratio")
        details["minimum_sip"] = get_stat_value("Min. for SIP")
        details["fund_size_aum"] = get_stat_value("Fund size")

        # Field 13 & 14: nav & nav_date
        try:
            nav_label = page.locator("div:has-text('NAV:')").first
            if nav_label:
                label_text = nav_label.inner_text()
                match_date = re.search(r'\d{2}\s[A-Za-z]{3}\s\'\d{2}', label_text)
                details["nav_date"] = match_date.group(0) if match_date else None
                
                # Value is usually in the next sibling div
                nav_val_elem = nav_label.locator("xpath=../following-sibling::div").first
                if nav_val_elem:
                    nav_text = nav_val_elem.inner_text()
                    num_only = re.sub(r'[^0-9.]', '', nav_text)
                    details["nav"] = float(num_only) if num_only else None
        except:
            pass
        
        # Field 6, 8, 9, 11: exit_load, lumpsum, lock-in, benchmark
        def get_detail_value(label):
            try:
                # These are usually in rows with direct text siblings
                row = page.locator(f"div:has-text('{label}')").last
                if row:
                    text = row.inner_text().split("\n")
                    for i, t in enumerate(text):
                        if label.lower() in t.lower() and i+1 < len(text):
                             return text[i+1].strip()
                return None
            except:
                return None

        details["exit_load"] = get_detail_value("Exit load") or get_detail_value("Exit Load")
        
        lumpsum_val = get_detail_value("Min. Investment") or get_detail_value("Min. investment")
        if lumpsum_val:
            num_only = re.sub(r'[^0-9.]', '', lumpsum_val)
            details["minimum_lumpsum"] = float(num_only) if num_only else lumpsum_val
        else:
            details["minimum_lumpsum"] = None

        details["lock_in_period"] = get_detail_value("Lock-in") or "No lock-in"
        details["benchmark"] = get_detail_value("Benchmark")

        # Field 15: groww_scheme_url
        details["groww_scheme_url"] = url
        details["last_scraped_at"] = datetime.now().strftime("%Y-%m-%d")

        return details

    def save_json(self, data):
        if not data or not data["scheme_name"]:
            return
        
        # Create a safe filename
        filename = data["scheme_name"].lower().replace(" ", "_").replace("-", "_")
        filename = re.sub(r'[^a-z0-9_]', '', filename) + ".json"
        
        path = os.path.join(self.DATA_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Saved: {path}")

    def run(self):
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            page = context.new_page()
            
            # Step 1: Discover URLs
            urls = self.crawl_amc_page(page)
            
            # Step 2: Scrape each
            successful_scrapes = 0
            for url in urls:
                try:
                    data = self.scrape_scheme_details(page, url)
                    if data:
                        self.save_json(data)
                        successful_scrapes += 1
                except Exception as e:
                    print(f"Failed to scrape {url}: {e}")
                
            browser.close()
            
            print("---")
            print(f"Total schemes discovered: {len(urls)}")
            print(f"Total JSON files created: {successful_scrapes}")
            print("Phase 1 – Groww Data Collection complete.")

if __name__ == "__main__":
    scraper = GrowwScraper()
    scraper.run()
