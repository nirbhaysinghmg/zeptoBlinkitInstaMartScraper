import requests
import csv
import json
from typing import List, Dict, Any
import time
from datetime import datetime
import os

# ===== CONFIGURATION - MODIFY THESE PARAMETERS =====
QUERIES = ["Fruits", "Vegetables"]  # Add your search queries here
COORDINATES_CSV = "BangaloreCords1.csv"  # CSV file containing coordinates
BASE_URL = "http://localhost:8001"  # FastAPI server URL
DELAY_BETWEEN_REQUESTS = 1  # Seconds to wait between requests
OUTPUT_DIR = "Testing2"  # Directory to save output files
# =================================================

class BlinkitScraper:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def search_products(self, query: str, coordinates: str = "28.451,77.096", save_to_db: bool = False, use_proxy: bool = True) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/blinkit/search"
        params = {
            "query": query,
            "coordinates": coordinates,
            "save_to_db": save_to_db,
            "use_proxy": use_proxy
        }
        
        try:
            print(f"Requesting: {url} with params: {params}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making request: {e}")
            return []
    
    def save_to_csv(self, products: List[Dict[str, Any]], filename: str = None) -> str:
        if not products:
            print("No products to save")
            return ""
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"blinkit_products_{timestamp}.csv"
        
        fieldnames = [
            'platform', 'search_query', 'store_id', 'product_id', 'variant_id',
            'name', 'brand', 'mrp', 'price', 'quantity', 'in_stock', 'inventory',
            'max_allowed_quantity', 'category', 'sub_category', 'images',
            'organic_rank', 'rating'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for product in products:
                row = {}
                for field in fieldnames:
                    value = product.get(field, '')
                    if field == 'images' and isinstance(value, list):
                        value = ';'.join(value)
                    row[field] = value
                writer.writerow(row)
        
        print(f"Saved {len(products)} products to {filename}")
        return filename

def read_coordinates_from_csv(csv_file: str) -> List[Dict[str, str]]:
    coordinates_data = []
    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row.get('centroid') and row['centroid'].strip():
                    coordinates_data.append({
                        'id': row.get('id', ''),
                        'centroid': row['centroid'].strip(),
                        'city': row.get('city', ''),
                        'locality': row.get('locality', '')
                    })
        print(f"Loaded {len(coordinates_data)} coordinates from {csv_file}")
        return coordinates_data
    except Exception as e:
        print(f"Error reading coordinates CSV: {e}")
        return []

def scrape_products_for_all_coordinates(queries: List[str], coordinates_data: List[Dict[str, str]], 
                                       base_url: str = "http://localhost:8001", 
                                       delay: int = 2, output_dir: str = "scraped_data"):
    scraper = BlinkitScraper(base_url)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")
    
    total_products = 0
    successful_coordinates = 0
    
    for i, coord_data in enumerate(coordinates_data, 1):
        centroid = coord_data['centroid']
        city = coord_data.get('city', 'Unknown')
        locality = coord_data.get('locality', 'Unknown')
        
        print(f"\n[{i}/{len(coordinates_data)}] Processing coordinates: {centroid}")
        print(f"Location: {locality}, {city}")
        
        safe_centroid = centroid.replace(',', '_').replace('"', '').replace(' ', '')
        
        for j, query in enumerate(queries, 1):
            print(f"  [{j}/{len(queries)}] Searching for: {query}")
            products = scraper.search_products(query, centroid, save_to_db=False, use_proxy=True)
            print(f"  Found {len(products)} products for '{query}'")
            
            if products:
                filename = os.path.join(output_dir, f"blinkit_{query.lower()}_{safe_centroid}.csv")
                scraper.save_to_csv(products, filename)
                total_products += len(products)
                if j == 1:  # Count successful coordinates only once per coordinate
                    successful_coordinates += 1
            else:
                print(f"  No products found for '{query}' at coordinates: {centroid}")
            
            if j < len(queries):
                print(f"  Waiting {delay} seconds before next query...")
                time.sleep(delay)
        
        if i < len(coordinates_data):
            print(f"Waiting {delay} seconds before next coordinates...")
            time.sleep(delay)
    
    print(f"\n{'='*50}")
    print(f"SCRAPING COMPLETED")
    print(f"{'='*50}")
    print(f"Total coordinates processed: {len(coordinates_data)}")
    print(f"Successful coordinates: {successful_coordinates}")
    print(f"Total products scraped: {total_products}")
    print(f"Output directory: {output_dir}")
    print(f"Average products per coordinate: {total_products/successful_coordinates if successful_coordinates > 0 else 0:.1f}")

def main():
    print("Blinkit Product Scraper - Multi-Coordinate Version")
    print("=" * 60)
    print(f"Queries: {QUERIES}")
    print(f"Coordinates CSV: {COORDINATES_CSV}")
    print(f"Base URL: {BASE_URL}")
    print(f"Delay: {DELAY_BETWEEN_REQUESTS}s")
    print(f"Output Directory: {OUTPUT_DIR}")
    print("=" * 60)
    
    coordinates_data = read_coordinates_from_csv(COORDINATES_CSV)
    
    if not coordinates_data:
        print("No coordinates found. Please check your CSV file.")
        return
    
    scrape_products_for_all_coordinates(
        queries=QUERIES,
        coordinates_data=coordinates_data,
        base_url=BASE_URL,
        delay=DELAY_BETWEEN_REQUESTS,
        output_dir=OUTPUT_DIR
    )

if __name__ == "__main__":
    main() 



