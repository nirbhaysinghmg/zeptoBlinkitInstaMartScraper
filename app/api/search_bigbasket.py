from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import json
import logging
import cloudscraper
import time
import re

from ..db.models import Product
from ..db.utils import save_products_to_db
from ..utils.format_utils import model_to_dict

router = APIRouter()

def extract_products_bigbasket(response_data: Dict, search_query: str) -> List[Product]:
    """Extract products from BigBasket API response"""
    products = []
    
    # Check if response has valid product data
    if not isinstance(response_data, dict) or not response_data.get('tabs'):
        return products
    
    for tab in response_data['tabs']:
        tab_products = tab.get('product_info', {}).get('products', [])
        for product in tab_products:
            # Extract basic info
            product_id = str(product.get("id", ""))
            brand = product.get("brand", {}).get("name", "")
            
            # Handle pricing
            pricing = product.get("pricing", {}).get("discount", {})
            try:
                mrp = float(pricing.get("mrp", "0"))
            except:
                mrp = 0.0
                
            try:
                price = float(pricing.get("prim_price", {}).get("sp", "0"))
            except:
                price = 0.0
            
            # Determine stock status
            availability = product.get("availability", {})
            in_stock = availability.get("button") == "Add" and availability.get("avail_status") == "001"
            
            # Extract category info
            category = product.get("category", {})
            
            # Extract images
            images = []
            for img in product.get("images", []):
                if img.get("l"):
                    images.append(img["l"])
                elif img.get("m"):
                    images.append(img["m"])
            
            # Create product object
            products.append(Product(
                platform="bigbasket",
                search_query=search_query,
                store_id=str(product.get("visibility", {}).get("fc_id", "")),  # Fulfillment center ID
                product_id=product_id,
                variant_id=product_id,  # BigBasket treats each SKU as unique product
                name=product.get("desc", ""),
                brand=brand,
                mrp=mrp,
                price=price,
                quantity=product.get("w", ""),
                in_stock=in_stock,
                inventory=product.get("inv_info", {}).get("skus", [{}])[0].get("qty", 0),
                max_allowed_quantity=product.get("sku_max_quantity", 10),
                category=category.get("tlc_name", ""),
                sub_category=category.get("mlc_name", ""),
                images=images,
                organic_rank=0,  # Will be set during pagination
                rating=product.get("rating_info", {}).get("avg_rating", 0.0)
            ))
    return products

# Global storage for cookies
bb_cookies = {}

def fetch_bigbasket_data(query: str, page: int = 1) -> Dict[str, Any]:
    """Fetch data from BigBasket with Cloudflare bypass"""
    global bb_cookies
    
    url = f"https://www.bigbasket.com/listing-svc/v2/products"
    params = {
        "type": "ps",
        "slug": query,
        "page": page,
        "bucket_id": 40
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"https://www.bigbasket.com/ps/?q={query}",
        "X-Requested-With": "XMLHttpRequest",
        "DNT": "1",
    }
    
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(
            url, 
            params=params, 
            headers=headers,
            cookies=bb_cookies,
            timeout=30
        )
        
        # Update cookies for subsequent requests
        bb_cookies = response.cookies.get_dict()
        
        # Log response details for debugging
        logger = logging.getLogger(__name__)
        logger.debug(f"BigBasket API status: {response.status_code}")
        logger.debug(f"Response URL: {response.url}")
        
        if response.status_code != 200:
            logger.error(f"BigBasket API error: {response.status_code} - {response.text[:200]}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"BigBasket API returned status {response.status_code}"
            )
        
        return response.json()
    
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Failed to parse response from BigBasket API - not valid JSON"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error while fetching data from BigBasket API: {str(e)}"
        )

@router.get("/bigbasket/search")
def search_bigbasket(
    query: str,
    save_to_db: bool = False,
    max_pages: int = 5
) -> List[Dict[str, Any]]:
    """Search BigBasket products with pagination and Cloudflare bypass"""
    all_products = []
    page = 1
    has_more = True
    max_retries = 3
    logger = logging.getLogger(__name__)

    try:
        while has_more and page <= max_pages:
            retries = 0
            success = False
            response_data = None
            
            while retries < max_retries and not success:
                try:
                    response_data = fetch_bigbasket_data(query, page)
                    products = extract_products_bigbasket(response_data, query)
                    
                    # Set organic rank based on position
                    for idx, product in enumerate(products):
                        product.organic_rank = (page - 1) * 30 + idx + 1  # Assuming 30 products/page
                    
                    all_products.extend(products)
                    success = True
                    
                    # Check if more pages exist
                    has_more = page < max_pages and bool(products)
                    
                except HTTPException as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Failed after {max_retries} retries for page {page}: {e.detail}")
                        has_more = False
                    else:
                        logger.warning(f"Retry {retries} for page {page}: {e.detail}")
                        time.sleep(2 ** retries)  # Exponential backoff
            
            # Move to next page
            page += 1
            time.sleep(1.5)  # Respectful delay between pages
        
        # Save to database if requested
        if save_to_db and all_products:
            save_products_to_db(all_products, "products")
        
        # Return standardized response
        exclude_fields = ["id", "created_at", "updated_at"]
        return [model_to_dict(product, exclude_fields=exclude_fields) for product in all_products]
        
    except Exception as e:
        logger.exception("BigBasket search failed")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing BigBasket search: {str(e)}"
        )