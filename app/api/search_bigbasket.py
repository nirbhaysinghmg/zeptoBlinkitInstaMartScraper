from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
import json
import logging
import cloudscraper
import time
import re
import random

from ..db.models import Product
from ..db.utils import save_products_to_db
from ..utils.format_utils import model_to_dict

router = APIRouter()

# Configure logging
logger = logging.getLogger(__name__)

def extract_products_bigbasket(response_data: Dict, search_query: str) -> List[Product]:
    """Extract products from BigBasket API response"""
    products = []
    
    # Check if response has valid product data
    if not isinstance(response_data, dict) or not response_data.get('tabs'):
        logger.warning("No 'tabs' found in response data")
        return products
    
    for tab in response_data['tabs']:
        tab_info = tab.get('product_info', {})
        if not tab_info:
            continue
            
        tab_products = tab_info.get('products', [])
        if not tab_products:
            logger.debug(f"No products found in tab: {tab.get('tab_name', 'unknown')}")
            continue
            
        for product in tab_products:
            try:
                # Extract basic info
                product_id = str(product.get("id", ""))
                brand = product.get("brand", {}).get("name", "")
                
                # Handle pricing
                pricing = product.get("pricing", {}).get("discount", {})
                try:
                    mrp = float(pricing.get("mrp", "0"))
                except (ValueError, TypeError):
                    mrp = 0.0
                    
                try:
                    price = float(pricing.get("prim_price", {}).get("sp", "0"))
                except (ValueError, TypeError):
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
                    name=product.get("desc", "").strip(),
                    brand=brand.strip(),
                    mrp=mrp,
                    price=price,
                    quantity=product.get("w", ""),
                    in_stock=in_stock,
                    category=category.get("tlc_name", ""),
                    sub_category=category.get("mlc_name", ""),
                    images=images,
                    organic_rank=0,  # Will be set during pagination
                    rating=product.get("rating_info", {}).get("avg_rating", 0.0)
                ))
            except Exception as e:
                logger.error(f"Error processing product {product_id}: {str(e)}")
                continue
                
    return products

# Global storage for cookies and session
bb_session = None
last_request_time = 0

def init_bigbasket_session():
    """Initialize a session with BigBasket including cookies and headers"""
    global bb_session
    bb_session = cloudscraper.create_scraper()
    
    # First get request to establish session
    try:
        response = bb_session.get(
            "https://www.bigbasket.com/",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
            timeout=30
        )
        logger.debug(f"Session initialized with status: {response.status_code}")
    except Exception as e:
        logger.error(f"Error initializing BigBasket session: {str(e)}")
        bb_session = None

def fetch_bigbasket_data(query: str, page: int = 1) -> Dict[str, Any]:
    """Fetch data from BigBasket with proper session management"""
    global bb_session, last_request_time
    
    # Initialize session if needed
    if bb_session is None:
        init_bigbasket_session()
        if bb_session is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize BigBasket session"
            )
    
    # Respect rate limits - minimum 2 seconds between requests
    current_time = time.time()
    if current_time - last_request_time < 2:
        sleep_time = 2 - (current_time - last_request_time) + random.uniform(0.1, 0.5)
        time.sleep(sleep_time)
    
    url = "https://www.bigbasket.com/listing-svc/v2/products"
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
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    }
    
    try:
        response = bb_session.get(
            url, 
            params=params, 
            headers=headers,
            timeout=30
        )
        
        last_request_time = time.time()
        
        logger.debug(f"BigBasket API request: {response.url}")
        logger.debug(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"BigBasket API error: {response.status_code} - {response.text[:200]}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"BigBasket API returned status {response.status_code}"
            )
        
        return response.json()
    
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON response from BigBasket")
        raise HTTPException(
            status_code=500,
            detail="Failed to parse response from BigBasket API - not valid JSON"
        )
    except Exception as e:
        logger.error(f"Error while fetching BigBasket data: {str(e)}")
        # Reset session on error
        bb_session = None
        raise HTTPException(
            status_code=500,
            detail=f"Error while fetching data from BigBasket API: {str(e)}"
        )

@router.get("/bigbasket/search")
def search_bigbasket(
    query: str,
    save_to_db: bool = False,
    max_pages: int = 3
) -> List[Dict[str, Any]]:
    """Search BigBasket products with proper session handling"""
    all_products = []
    page = 1
    has_more = True
    max_retries = 3
    products_per_page = 30  # BigBasket returns 30 products per page

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
                        product.organic_rank = (page - 1) * products_per_page + idx + 1
                    
                    all_products.extend(products)
                    success = True
                    
                    # Check if more pages exist - BigBasket doesn't provide a has_next flag
                    has_more = len(products) >= products_per_page
                    
                except HTTPException as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Failed after {max_retries} retries for page {page}: {e.detail}")
                        has_more = False
                    else:
                        logger.warning(f"Retry {retries} for page {page}: {e.detail}")
                        time.sleep(2 ** retries)  # Exponential backoff
            
            # Move to next page
            if success:
                page += 1
                time.sleep(random.uniform(1.5, 3.0))  # Random delay between pages
        
        logger.info(f"Found {len(all_products)} products for query '{query}'")
        
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