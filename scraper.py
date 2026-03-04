from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import csv
from datetime import datetime
from selenium.webdriver.common.keys import Keys

class AuctionScraper:
    def __init__(self, url):
        self.url = url
        self.properties = []
        self.driver = None
        
    def setup_driver(self):
        """Initialize stable Selenium Chrome driver"""
        options = ChromeOptions()
        
        # # Stability and performance flags from successful test script
        # # options.add_argument('--headless=new') # Uncomment to run in background
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

        # Initialize standard driver
        self.driver = webdriver.Chrome(options=options)
        
        # Optional: Mask navigator.webdriver for better evasion
        try:
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except:
            pass
        
    def get_scrollable_container(self):
        """Find the virtual scrollable container for properties"""
        try:
            # Look for the specific virtual scroll container
            # Look for the specific virtual scroll container (the inner div with overflow: auto)
            # The structure is: wrapper(asset-list_content_v2) -> div -> div(scrollable)
            container = self.driver.find_element(By.XPATH, '//div[@data-elm-id="asset-list_content_v2"]//div[contains(@style, "overflow: auto")]')
            if container:
                print(f"Found container: {container.get_attribute('class')}")
                return container
        except Exception as e:
            print(f"Could not find scroll container: {e}")
        return None
    
    def extract_visible_properties(self):
        """Extract properties currently visible in the DOM and add to list"""
        try:
            property_cards = self.driver.find_elements(By.CSS_SELECTOR, '[data-elm-id*="asset_"][data-elm-id*="_root"]')
            
            for card in property_cards:
                try:
                    asset_id = card.get_attribute('data-elm-id').replace('asset_', '').replace('_root', '')
                    if asset_id == "inject_placeholder":    
                        continue
                    
                    # Skip if already extracted
                    if any(p['asset_id'] == asset_id for p in self.properties):
                        continue
                    
                    # Extract all property data
                    try:
                        address = card.find_element(By.CSS_SELECTOR, f'[data-elm-id="address_line_asset_{asset_id}"]').text.strip()
                    except:
                        address = "N/A"
                    
                    try:
                        beds = card.find_element(By.CSS_SELECTOR, f'[data-elm-id="card_auction_beds_asset_{asset_id}"]').text.strip()
                    except:
                        beds = "N/A"
                    
                    try:
                        baths = card.find_element(By.CSS_SELECTOR, f'[data-elm-id="card_auction_baths_asset_{asset_id}"]').text.strip()
                    except:
                        baths = "N/A"
                    
                    try:
                        sqft = card.find_element(By.CSS_SELECTOR, f'[data-elm-id="card_auction_sqft_asset_{asset_id}"]').text.strip()
                    except:
                        sqft = "N/A"
                    
                    try:
                        price_element = card.find_element(By.CSS_SELECTOR, '.cardPartsStyles__property-value-amount--ZR0qK')
                        price = price_element.text.strip()
                        price_label = card.find_element(By.CSS_SELECTOR, '.cardPartsStyles__amount-label--uJ5QE').text.strip()
                    except:
                        price = "N/A"
                        price_label = "N/A"
                    
                    try:
                        status = card.find_element(By.CSS_SELECTOR, '[data-elm-id="info-pill"] .text').text.strip()
                    except:
                        status = "N/A"
                    
                    try:
                        property_type = card.find_element(By.CSS_SELECTOR, '.listing-card-asset-info div').text.strip()
                    except:
                        property_type = "N/A"
                    
                    try:
                        image_style = card.find_element(By.CSS_SELECTOR, '.cardPartsStyles__property-card-image-background--vUvwD').get_attribute('style')
                        image_url = image_style.split('url("')[1].split('")')[0] if 'url("' in image_style else "N/A"
                    except:
                        image_url = "N/A"
                    
                    try:
                        property_url = card.find_element(By.CSS_SELECTOR, '.styles__card-link--pHDnC').get_attribute('href')
                    except:
                        property_url = "N/A"
                    
                    property_data = {
                        'asset_id': asset_id,
                        'address': address,
                        'beds': beds,
                        'baths': baths,
                        'sqft': sqft,
                        'price': price,
                        'price_label': price_label,
                        'status': status,
                        'property_type': property_type,
                        'image_url': image_url,
                        'property_url': property_url,
                        'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    self.properties.append(property_data)
                    
                except Exception as e:
                    # Ignore errors for specific cards that might have become stale
                    continue
                    
        except Exception as e:
            print(f"Error extracting visible properties: {e}")
    
    def scroll_to_load_more(self, max_scrolls=1000):
        """Scroll the virtual scroll container and extract properties continuously"""
        import random
        
        print("\nStarting to scroll and extract properties...")
        print("Detecting virtual scroll container...")
        
        scroll_container = self.get_scrollable_container()
        if not scroll_container:
            print("[ERROR] Could not find scroll container!")
            return
        
        print("[OK] Found virtual scroll container\n")
        
        scrolls = 0
        no_new_properties_count = 0
        max_no_change = 15  # Stop after 15 scrolls with no new properties
        
        # Initial extraction
        self.extract_visible_properties()
        print(f"Initial extraction: {len(self.properties)} properties")
        
        while scrolls < max_scrolls:
            properties_before = len(self.properties)
            
            # Get current scroll position and max scroll height
            try:
                scroll_info = self.driver.execute_script("""
                    var elem = arguments[0];
                    return {
                        scrollTop: elem.scrollTop,
                        scrollHeight: elem.scrollHeight,
                        clientHeight: elem.clientHeight
                    };
                """, scroll_container)
                
                # Scroll the container
                scroll_amount = random.randint(800, 1500)
                self.driver.execute_script(f"""
                    arguments[0].scrollTop += {scroll_amount};
                """, scroll_container)
            except Exception as e:
                # If the container became stale, re-fetch it
                print(f"[NOTE] Re-fetching scroll container (stale or not found: {e})")
                scroll_container = self.get_scrollable_container()
                if not scroll_container:
                    break
                continue

            # Optimized wait: Wait for new properties to load or timeout
            time.sleep(random.uniform(1.0, 2.0)) 
            
            # Extract visible properties
            self.extract_visible_properties()
            
            properties_after = len(self.properties)
            new_properties = properties_after - properties_before
            
            # Check if we found new properties
            if new_properties > 0:
                print(f"Scroll {scrolls + 1}: [OK] Found {new_properties} new properties! (Total: {properties_after})")
                no_new_properties_count = 0
            else:
                no_new_properties_count += 1
                print(f"Scroll {scrolls + 1}: No new properties (Total: {properties_after}) - Attempt {no_new_properties_count}/{max_no_change}")
            
            scrolls += 1
            
            # Check if we've reached the end
            if no_new_properties_count >= max_no_change:
                # Check scroll position
                current_scroll = scroll_info['scrollTop']
                max_scroll = scroll_info['scrollHeight'] - scroll_info['clientHeight']
                
                print(f"\n{'='*60}")
                print(f"[OK] No new properties after {max_no_change} scrolls")
                print(f"[OK] Scroll position: {current_scroll}/{max_scroll}")
                print(f"[OK] Total properties extracted: {properties_after}")
                print(f"{'='*60}\n")
                break
            
            if properties_after > 0 and properties_after % 50 == 0 and new_properties > 0:
                print(f"\n[Milestone]: {properties_after} properties extracted!\n")
            
    def extract_property_data(self):
        """Extract all property information from the page"""
        print("\nExtracting property data...")
        
        # Find all property cards
        property_cards = self.driver.find_elements(By.CSS_SELECTOR, '[data-elm-id*="asset_"][data-elm-id*="_root"]')
        print(f"Found {len(property_cards)} property cards")
        
        for card in property_cards:
            try:
                # Get asset ID
                asset_id = card.get_attribute('data-elm-id').replace('asset_', '').replace('_root', '')
                
                # Extract address
                try:
                    address = card.find_element(By.CSS_SELECTOR, f'[data-elm-id="address_line_asset_{asset_id}"]').text.strip()
                except:
                    address = "N/A"
                
                # Extract beds
                try:
                    beds = card.find_element(By.CSS_SELECTOR, f'[data-elm-id="card_auction_beds_asset_{asset_id}"]').text.strip()
                except:
                    beds = "N/A"
                
                # Extract baths
                try:
                    baths = card.find_element(By.CSS_SELECTOR, f'[data-elm-id="card_auction_baths_asset_{asset_id}"]').text.strip()
                except:
                    baths = "N/A"
                
                # Extract square feet
                try:
                    sqft = card.find_element(By.CSS_SELECTOR, f'[data-elm-id="card_auction_sqft_asset_{asset_id}"]').text.strip()
                except:
                    sqft = "N/A"
                
                # Extract price/bid information
                try:
                    price_element = card.find_element(By.CSS_SELECTOR, '.cardPartsStyles__property-value-amount--ZR0qK')
                    price = price_element.text.strip()
                    price_label = card.find_element(By.CSS_SELECTOR, '.cardPartsStyles__amount-label--uJ5QE').text.strip()
                except:
                    price = "N/A"
                    price_label = "N/A"
                
                # Extract status (Auction Today, Ended yesterday, etc.)
                try:
                    status = card.find_element(By.CSS_SELECTOR, '[data-elm-id="info-pill"] .text').text.strip()
                except:
                    status = "N/A"
                
                # Extract property type (Foreclosure Sale, etc.)
                try:
                    property_type = card.find_element(By.CSS_SELECTOR, '.listing-card-asset-info div').text.strip()
                except:
                    property_type = "N/A"
                
                # Extract image URL
                try:
                    image_style = card.find_element(By.CSS_SELECTOR, '.cardPartsStyles__property-card-image-background--vUvwD').get_attribute('style')
                    image_url = image_style.split('url("')[1].split('")')[0] if 'url("' in image_style else "N/A"
                except:
                    image_url = "N/A"
                
                # Extract property URL
                try:
                    property_url = card.find_element(By.CSS_SELECTOR, '.styles__card-link--pHDnC').get_attribute('href')
                except:
                    property_url = "N/A"
                
                property_data = {
                    'asset_id': asset_id,
                    'address': address,
                    'beds': beds,
                    'baths': baths,
                    'sqft': sqft,
                    'price': price,
                    'price_label': price_label,
                    'status': status,
                    'property_type': property_type,
                    'image_url': image_url,
                    'property_url': property_url,
                    'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Check for duplicates
                if not any(p['asset_id'] == asset_id for p in self.properties):
                    self.properties.append(property_data)
                    print(f"[OK] Extracted: {address} (Asset ID: {asset_id})")
                
            except Exception as e:
                print(f"[ERROR] Error extracting property: {e}")
                continue
    
    def save_data(self):
        """Save extracted data to JSON and CSV files"""
        print(f"\nSaving {len(self.properties)} properties...")
        
        # Save to JSON
        with open('properties_data.json', 'w', encoding='utf-8') as f:
            json.dump(self.properties, f, indent=2, ensure_ascii=False)
        print("[OK] Saved to properties_data.json")
        
        # Save to CSV
        if self.properties:
            keys = self.properties[0].keys()
            with open('properties_data.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(self.properties)
            print("[OK] Saved to properties_data.csv")
    
    def run(self, filter_text):
        """Main scraping process"""
        try:
            print(f"Starting scraper for: {self.url}\n")
            self.setup_driver()
            
            # Load the page
            print("Loading the page...")
            self.driver.get(self.url)
            
            # Use WebDriverWait instead of static sleep
            wait = WebDriverWait(self.driver, 20)
            
            try: 
                # Wait for potential popup skip button
                popUp = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-elm-id="onboarding_drawer_skip_button"]')))
                self.driver.execute_script("arguments[0].click();", popUp)
                print("[OK] Dismissed onboarding popup")
            except:
                pass




            
            # Search for location
            try:
                search_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="Search"]')))
                search_input.clear()
                search_input.send_keys(filter_text)
                search_input.send_keys(Keys.ENTER)
                print(f"[OK] Searching for: {filter_text}")
                
                # Wait for results to start loading (container appears)
                wait.until(EC.presence_of_element_located((By.XPATH, '//div[@data-elm-id="asset-list_content_v2"]')))
            except Exception as e:
                print(f"[ERROR] Search failed: {e}")

            
            # Scroll to load more properties
            self.scroll_to_load_more(max_scrolls=1000)
            
            # Extract property data
            self.extract_property_data()
            
            # Save the data
            self.save_data()
            
            print(f"\n{'='*60}")
            print(f"Scraping completed successfully!")
            print(f"Total properties extracted: {len(self.properties)}")
            print(f"{'='*60}")
            
        except Exception as e:
            print(f"X Error during scraping: {e}")
        finally:
            if self.driver:
                print("\nClosing browser...")
                self.driver.quit()

def scrape_data(filter_text):
    url = "https://www.auction.com/"    
    scraper = AuctionScraper(url)
    scraper.run(filter_text)

if __name__ == "__main__":
    # Replace with the actual URL of the auction website
    # url = input("Enter the auction website URL: ").strip()
    
    scrape_data("Secaucus, NJ")
