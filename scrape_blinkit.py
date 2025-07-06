import requests
import csv
import json
from typing import List, Dict, Any
import time
from datetime import datetime

class BlinkitScraper:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def search_products(self, query: str, coordinates: str = "28.451,77.096", save_to_db: bool = False) -> List[Dict[str, Any]]:
        """Search products using the FastAPI endpoint"""
        url = f"{self.base_url}/blinkit/search"
        params = {
            "query": query,
            "coordinates": coordinates,
            "save_to_db": save_to_db
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making request: {e}")
            return []
    
    def save_to_csv(self, products: List[Dict[str, Any]], filename: str = None) -> str:
        """Save products data to CSV file"""
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

def main():
    scraper = BlinkitScraper()
    
    # Example usage
    queries = ["chocolate", "milk", "bread"]
    coordinates = "28.451,77.096"
    
    all_products = []
    
    for query in queries:
        print(f"Searching for: {query}")
        products = scraper.search_products(query, coordinates, save_to_db=False)
        print(f"Found {len(products)} products for '{query}'")
        all_products.extend(products)
        time.sleep(2)  # Rate limiting
    
    if all_products:
        filename = scraper.save_to_csv(all_products)
        print(f"Total products saved: {len(all_products)}")
        print(f"CSV file: {filename}")
    else:
        print("No products found")

if __name__ == "__main__":
    main() 