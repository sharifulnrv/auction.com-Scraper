from details_scraper import AuctionDetailsScraper
import sys

def main():
    # Default location if none provided
    location = "New York, NY"
    
    # Check for command line argument
    if len(sys.argv) > 1:
        location = " ".join(sys.argv[1:])
    
    print(f"Starting detailed scraper for location: {location}")
    
    scraper = AuctionDetailsScraper()
    scraper.run(location)

if __name__ == "__main__":
    main()
# exmaple
# python .\run_details_scraper.py "Secaucus, NJ"