from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import json
import csv
import os
import random
from datetime import datetime

class AuctionDetailsScraper:
    def __init__(self, base_url="https://www.auction.com/"):
        self.base_url = base_url
        self.property_urls = []
        self.detailed_properties = []
        self.driver = None

    def setup_driver(self):
        """Initialize stable Selenium Chrome driver"""
        options = ChromeOptions()
        
        # # Stability and performance flags
        # options.add_argument('--no-sandbox')
        # options.add_argument('--disable-dev-shm-usage')
        # options.add_argument('--disable-gpu')
        # options.add_argument('--start-maximized')
        
        # # Disable images to save bandwidth
        # prefs = {"profile.managed_default_content_settings.images": 2}
        # options.add_experimental_option("prefs", prefs)

        # # Set explicit binary location for Windows
        # import os
        # chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        # if os.path.exists(chrome_path):
        #     options.binary_location = chrome_path

        self.driver = webdriver.Chrome(options=options)
        
        # Mask navigator.webdriver
        try:
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except:
            pass

    def get_scrollable_container(self):
        """Find the virtual scrollable container for properties"""
        try:
            container = self.driver.find_element(By.XPATH, '//div[@data-elm-id="asset-list_content_v2"]//div[contains(@style, "overflow: auto")]')
            return container
        except:
            return None

    def collect_urls(self, filter_text, max_scrolls=20):
        """Search and collect property URLs from the search results"""
        print(f"Searching for: {filter_text}")
        self.driver.get(self.base_url)
        wait = WebDriverWait(self.driver, 20)
        
        try:
            # Dismiss popup if exists
            try:
                pop_up = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-elm-id="onboarding_drawer_skip_button"]')))
                self.driver.execute_script("arguments[0].click();", pop_up)
            except:
                pass

            # Search
            search_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="Search"]')))
            search_input.clear()
            search_input.send_keys(filter_text)
            search_input.send_keys(Keys.ENTER)
            
            # Wait for results
            wait.until(EC.presence_of_element_located((By.XPATH, '//div[@data-elm-id="asset-list_content_v2"]')))
            time.sleep(5)
            
            print("Scrolling to collect URLs...")
            scroll_container = self.get_scrollable_container()
            
            scrolls = 0
            while scrolls < max_scrolls:
                # Extract URLs currently visible
                cards = self.driver.find_elements(By.CSS_SELECTOR, '.styles__card-link--pHDnC')
                for card in cards:
                    url = card.get_attribute('href')
                    if url and url not in self.property_urls:
                        self.property_urls.append(url)
                
                print(f"Collected {len(self.property_urls)} URLs so far...")
                
                # Scroll
                try:
                    self.driver.execute_script("arguments[0].scrollTop += 1200;", scroll_container)
                    time.sleep(2)
                except:
                    # Re-fetch container if stale
                    scroll_container = self.get_scrollable_container()
                    if not scroll_container: break
                
                scrolls += 1
                
        except Exception as e:
            print(f"[ERROR] URL collection failed: {e}")

    def scrape_property_details(self, url):
        """Scrape granular details from a single property page"""
        print(f"Scraping details for: {url}")
        self.driver.get(url)
        wait = WebDriverWait(self.driver, 15)
        
        data = {'property_url': url, 'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        try:
            # Wait for main content
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-elm-id="property_details_content"]')))
            
            # Helper function for text extraction
            def get_text(elm_id):
                try:
                    return self.driver.find_element(By.CSS_SELECTOR, f'[data-elm-id="{elm_id}"]').text.strip()
                except:
                    return "N/A"

            # Core details
            data['beds'] = get_text("total_bedrooms_value")
            data['baths'] = get_text("total_bathrooms_value")
            data['sqft'] = get_text("interior_square_footage_value")
            data['lot_size'] = get_text("exterior_acerage_value")
            data['property_type'] = get_text("property_type_value")
            data['year_built'] = get_text("year_built_value")
            data['apn'] = get_text("apn_value")
            
            # Occupancy & Liens
            try:
                data['occupancy'] = self.driver.find_element(By.CSS_SELECTOR, '[data-elm-id="occupancy_label"]').text.strip() + " " + \
                                    self.driver.find_element(By.CSS_SELECTOR, '[data-elm-id="occupancy_content"]').text.strip()
            except:
                data['occupancy'] = "N/A"
            
            try:
                data['liens'] = self.driver.find_element(By.CSS_SELECTOR, '[data-elm-id="title_and_liens_label"]').text.strip() + " " + \
                                 self.driver.find_element(By.CSS_SELECTOR, '[data-elm-id="title_and_liens_content"]').text.strip()
            except:
                data['liens'] = "N/A"
                
            # Badges (Buyer's Premium, Cash Only, Interior Access, Broker Co-op)
            badge_mappings = {
                "buyers_premium": "buyers_premium_summary",
                "cash_only": "cash_only_summary",
                "interior_access": "interior_access_summary",
                "broker_co_op": "broker_co_op_summary"
            }
            
            for key, val_id in badge_mappings.items():
                try:
                    data[key] = self.driver.find_element(By.CSS_SELECTOR, f'[data-elm-id="{val_id}"]').text.strip()
                except:
                    data[key] = "N/A"
            
            # Special Notes
            data['special_notes'] = get_text("mls_comment_value")

            # Price Insights
            data['est_market_value'] = get_text("arv_value")
            data['opening_bid'] = get_text("opening_bid_value")

            # Auction Details
            data['auction_status'] = get_text("auction-detail-box-status")
            
            try:
                data['bidding_ends_in'] = self.driver.find_element(By.CSS_SELECTOR, '[data-elm-id="countdown_timer_value"] [data-elm-id="value"]').text.strip()
            except:
                data['bidding_ends_in'] = get_text("countdown_timer_value")
            
            data['duration_date_range'] = get_text("auction_duration_date_range")
            data['duration_time_zone'] = get_text("auction_duration_time_zone")
            data['current_bid'] = get_text("current_bid_value")
            data['bid_increment'] = get_text("bid_increment_value")
            data['reserve_status'] = get_text("reserve_value")
            
            return data
            
        except Exception as e:
            print(f"[ERROR] Failed to scrape {url}: {e}")
            return None

    def save_data(self):
        """Save data to JSON and CSV in real-time"""
        if not self.detailed_properties:
            return

        # Save to JSON
        with open('properties_detailed.json', 'w', encoding='utf-8') as f:
            json.dump(self.detailed_properties, f, indent=2, ensure_ascii=False)
        
        # Save to CSV
        keys = self.detailed_properties[0].keys()
        with open('properties_detailed.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(self.detailed_properties)
            
        print(f"[OK] Real-time save: {len(self.detailed_properties)} properties saved to JSON and CSV.")

    def run(self, filter_text):
        try:
            self.setup_driver()
            self.collect_urls(filter_text)
            
            print(f"\nCollected {len(self.property_urls)} properties. Starting deep scrape...\n")
            
            for i, url in enumerate(self.property_urls):
                details = self.scrape_property_details(url)
                if details:
                    self.detailed_properties.append(details)
                    print(f"[{i+1}/{len(self.property_urls)}] Success")
                    # Real-time save after each property
                    self.save_data()
                
                # Random delay to be polite
                time.sleep(random.uniform(2, 4))
            
            self.save_data()
            print("\nDeep scraping completed successfully!")
            
        except Exception as e:
            print(f"[ERROR] Main process failed: {e}")
        finally:
            if self.driver:
                self.driver.quit()

if __name__ == "__main__":
    scraper = AuctionDetailsScraper()
    scraper.run("Secaucus, NJ")
