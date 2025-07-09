from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import json
import subprocess
from urllib.parse import urlencode, urlparse, parse_qs
import logging
import cloudscraper
import time
# import brotli
from fastapi.responses import StreamingResponse
import io
import csv

from ..utils.token_utils import (
    generate_uuid, 
    generate_auth_key
)
from ..core.constants import (
    BLINKIT_USER_AGENT, 
    BLINKIT_APP_VERSION
)
from ..db.models import Product
from ..db.utils import save_products_to_db
from ..utils.format_utils import model_to_dict

router = APIRouter()

def extract_products(response_data: Dict) -> List[Product]:
    products = []
    
    if not isinstance(response_data, dict) or not response_data.get('response', {}).get('snippets'):
        return []
    
    snippets = response_data.get('response', {}).get('snippets', [])
    
    def create_product(snippet, is_variant):
        data_obj = snippet.get('data', {})
        tracking_obj = snippet.get('tracking', {})
        
        product_id = data_obj.get('product_id', '')
        
        return Product(
            platform='blinkit',
            search_query=response_data.get('postback_params', {}).get('previous_search_query', ''),
            store_id=data_obj.get('merchant_id', ''),
            product_id=product_id,
            variant_id=data_obj.get('identity', {}).get('id', '') if is_variant else product_id,
            name=data_obj.get('name', {}).get('text', ''),
            brand=data_obj.get('brand_name', {}).get('text', ''),
            mrp=tracking_obj.get('common_attributes', {}).get('mrp', 0),
            price=tracking_obj.get('common_attributes', {}).get('price', 0),
            quantity=data_obj.get('variant', {}).get('text', ''),
            in_stock=not data_obj.get('is_sold_out', False),
            inventory=data_obj.get('inventory', 0),
            max_allowed_quantity=data_obj.get('inventory', 0),
            category=tracking_obj.get('common_attributes', {}).get('l2_category', ''),
            sub_category=tracking_obj.get('common_attributes', {}).get('ptype', ''),
            images=[item.get('image', {}).get('url', '') for item in data_obj.get('media_container', {}).get('items', [])],
            organic_rank=tracking_obj.get('common_attributes', {}).get('product_position', 0),
            rating=tracking_obj.get('common_attributes', {}).get('rating', 0),            
        )
    
    for snippet in snippets:
        if 'product_card_snippet' not in snippet.get('widget_type', ''):
            continue
            
        data = snippet.get('data', {})
        if not data:
            continue
        
        variant_list = data.get('variant_list', [])
        
        if variant_list:
            for variant in variant_list:
                if not variant.get('data', {}):
                    continue
                variant_product = create_product(variant, is_variant=True)
                products.append(variant_product)
        else:
            product = create_product(snippet, is_variant=False)
            products.append(product)
    
    return products

cookie_temp = {}
def fetch_blinkit_data(query: str = None, lat: str = "28.4511202", lon: str = "77.0965147", next_url: str = None) -> Dict[str, Any]:
    global cookie_temp
    base_url = "https://blinkit.com"
    if next_url:
        url = base_url + next_url if next_url.startswith('/') else next_url
    else:
        url = f"{base_url}/v1/layout/search?q={query}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "Lat": lat,
        "Lon": lon,
        }

    
    try:
        scraper = cloudscraper.create_scraper()  # returns a requests-like session
        response = scraper.post(url, headers=headers)
        print("Content-Type:", response.headers.get("Content-Type"))
        if response.status_code != 200:
            print("error in response with code",response.status_code)
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch data from Blinkit API: {response.text}"
            )

        
        cookie_temp = response.cookies.get_dict()

        response_text = response.text
        response_data = json.loads(response_text)
        return response_data
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Failed to parse response from Blinkit API - not valid JSON"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error while fetching data from Blinkit API: {str(e)}"
        )


def search_blinkit_generator(query: str = "chocolate", coordinates: str = "28.451,77.096"):
    lat, lon = coordinates.split(',')
    page_count = 0
    has_next_url = True
    next_url = None
    max_pages = 10
    max_retries = 3
    try:
        while has_next_url and page_count < max_pages:
            retries = 0
            success = False
            while retries < max_retries and not success:
                try:
                    if next_url:
                        response_data = fetch_blinkit_data(query, lat, lon, next_url)
                    else:
                        response_data = fetch_blinkit_data(query, lat, lon)
                    next_url = response_data.get('response', {}).get('pagination', {}).get('next_url')
                    has_next_url = bool(next_url)
                    page_products = extract_products(response_data)
                    for product in page_products:
                        yield model_to_dict(product, exclude_fields=["id", "created_at", "updated_at"])
                    page_count += 1
                    time.sleep(1)
                    success = True
                except Exception as page_err:
                    retries += 1
                    if retries == max_retries:
                        logging.error(f"Error processing page {page_count} after {max_retries} retries: {str(page_err)}")
                        has_next_url = False
                    else:
                        logging.warning(f"Retry {retries} for page {page_count}: {str(page_err)}")
                        time.sleep(5)
    except Exception as e:
        logging.error(f"Error in generator: {str(e)}")

@router.get("/blinkit/download")
def download_blinkit_csv(query: str, coordinates: str):
    def generate():
        header = [
            'platform', 'search_query', 'store_id', 'product_id', 'variant_id',
            'name', 'brand', 'mrp', 'price', 'quantity', 'in_stock', 'inventory',
            'max_allowed_quantity', 'category', 'sub_category', 'images',
            'organic_rank', 'rating'
        ]
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(header)
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)
        for product in search_blinkit_generator(query, coordinates):
            row = [product.get(field, '') for field in header]
            writer.writerow(row)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
    return StreamingResponse(generate(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=blinkit_products.csv"})


@router.get("/blinkit/search")
def search_blinkit(query: str = "chocolate", coordinates: str = "28.451,77.096", save_to_db: bool = False) -> List[Dict[str, Any]]:
    lat, lon = coordinates.split(',')
    all_products = []
    page_count = 0
    has_next_url = True
    next_url = None
    max_pages = 10
    max_retries = 3

    try:
        while has_next_url and page_count < max_pages:
            retries = 0
            success = False
            while retries < max_retries and not success:
                try:
                    if next_url:
                        response_data = fetch_blinkit_data(query, lat, lon, next_url)
                    else:
                        response_data = fetch_blinkit_data(query, lat, lon)
                    
                    next_url = response_data.get('response', {}).get('pagination', {}).get('next_url')
                    has_next_url = bool(next_url)
                    page_products = extract_products(response_data)
                    all_products.extend(page_products)
                    page_count += 1
                    time.sleep(1)
                    success = True
                    
                except Exception as page_err:
                    retries += 1
                    if retries == max_retries:
                        logging.error(f"Error processing page {page_count} after {max_retries} retries: {str(page_err)}")
                        has_next_url = False
                    else:
                        logging.warning(f"Retry {retries} for page {page_count}: {str(page_err)}")
                        time.sleep(5)
        
        if save_to_db and all_products:
            save_products_to_db(all_products, "products")
        
        exclude_fields = ["id", "created_at", "updated_at"]
        return [model_to_dict(product, exclude_fields=exclude_fields) for product in all_products]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing Blinkit search: {str(e)}"
        )
