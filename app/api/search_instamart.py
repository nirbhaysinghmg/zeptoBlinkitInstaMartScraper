from re import search
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import json
import subprocess
from urllib.parse import urlencode
from ..utils.token_utils import (
    generate_uuid, 
    generate_matcher_id, 
    get_cookie_suffixes
)
from ..core.constants import INSTAMART_USER_AGENT, INSTAMART_VERSION_CODE, INSTAMART_BUILD_VERSION, INSTAMART_IMAGE_PREFIX
from ..db.models import Product
from ..db.utils import save_products_to_db
from ..utils.format_utils import model_to_dict

router = APIRouter()

def extract_products(response_data: Dict) -> List[Product]:
    products = []
    
    try:
        items = response_data.get('data', {}).get('widgets', [])[0].get('data', [])
            
        for item in items:
            if not item:
                continue
                
            variations = item.get('variations', [])
            if not variations:
                continue

            # Process all variations
            for variation in variations:
                product = Product(
                    platform='instamart',
                    search_query=response_data.get('data', {}).get('query', ""),                    
                    store_id=variation.get('store_id', ''),
                    product_id=item.get('product_id', ''),
                    variant_id=variation.get('id', ''),
                    name=variation.get('display_name', ''),
                    brand=variation.get('brand', ''),
                    mrp=variation.get('price', {}).get('mrp', 0),
                    price=variation.get('price', {}).get('offer_price', 0),
                    quantity=variation.get('quantity', ''),
                    in_stock=variation.get('inventory', {}).get('in_stock', False),
                    inventory=variation.get('cart_allowed_quantity', {}).get('total', 0),
                    max_allowed_quantity=variation.get('max_allowed_quantity', 0),
                    category=variation.get('category', ''),
                    sub_category=variation.get('sub_category', ''),
                    images=[INSTAMART_IMAGE_PREFIX + image for image in variation.get('images', [])],
                    organic_rank=variation.get('sosAdsPositionData', {}).get('organic_rank', 0),
                    page=response_data.get('data', {}).get('pageNumber', 0),

                    platform_specific_details=json.dumps({
                        'ads_rank': variation.get('sosAdsPositionData', {}).get('ads_rank', 0),
                    }),
                )
                products.append(product)
                
        return products
        
    except Exception as e:
        raise Exception(f"Error extracting product details: {str(e)}")

async def fetch_instamart_data(query: str, store_id: str, page_num: int) -> Dict[str, Any]:
    device_id = generate_uuid()
    tid = generate_uuid()
    sid = generate_uuid()
    matcher_id = generate_matcher_id()
    
    suffixes = get_cookie_suffixes()
    
    if page_num == 0:
        search_results_offset = 0
    elif page_num == 1:
        search_results_offset = 20
    else:
        search_results_offset = 20 + ((page_num - 1) * 42)

    query_params = {
        'pageNumber': page_num,
        'searchResultsOffset': search_results_offset,
        'limit': 40,
        'query': query,
        'ageConsent': 'false',
        'pageType': 'INSTAMART_SEARCH_PAGE',
        'isPreSearchTag': 'false',
        'highConfidencePageNo': 0,
        'lowConfidencePageNo': 0,
        'voiceSearchTrackingId': '',
        'storeId': store_id,
        'primaryStoreId': store_id,
        'secondaryStoreId': ''  # Empty since we're not using secondary store
    }
    
    cookies = [
        f'deviceId=s%3A{device_id}.{suffixes["device_id"]}',
        f'tid=s%3A{tid}.{suffixes["tid"]}',
        f'sid=s%3A{sid}.{suffixes["sid"]}',
        f'versionCode={INSTAMART_VERSION_CODE}',
        'platform=web',
        'subplatform=dweb',
        'statusBarHeight=0',
        'bottomOffset=0',
        'genieTrackOn=false',
        'ally-on=false',
        'isNative=false',
        'strId=',
        'openIMHP=false'
    ]
    
    curl_command = [
        'curl',
        '--compressed',
        '-X', 'POST',
        f'https://www.swiggy.com/api/instamart/search?{urlencode(query_params)}',
        '-H', 'authority: www.swiggy.com',
        '-H', 'accept: */*',
        '-H', 'accept-encoding: gzip, deflate, br, zstd',
        '-H', 'accept-language: en-US,en;q=0.9',
        '-H', 'content-type: application/json',
        '-H', f'cookie: {"; ".join(cookies)}',
        '-H', 'dnt: 1',
        '-H', f'matcher: {matcher_id}',
        '-H', 'origin: https://www.swiggy.com',
        '-H', 'priority: u=1, i',
        '-H', 'referer: https://www.swiggy.com/instamart/search',
        '-H', 'sec-ch-ua: "Chromium";v="133", "Not(A:Brand";v="99"',
        '-H', 'sec-ch-ua-mobile: ?0',
        '-H', 'sec-ch-ua-platform: "macOS"',
        '-H', 'sec-fetch-dest: empty',
        '-H', 'sec-fetch-mode: cors',
        '-H', 'sec-fetch-site: same-origin',
        '-H', f'user-agent: {INSTAMART_USER_AGENT}',
        '-H', f'x-build-version: {INSTAMART_BUILD_VERSION}',
        '-d', '{"facets":{},"sortAttribute":""}'
    ]
    
    process = subprocess.Popen(
        curl_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()
    
    if process.returncode != 0:
        error_message = stderr.decode('utf-8')
        raise HTTPException(
            status_code=500,
            detail=f"Error from curl command: {error_message}"
        )
    
    response_text = stdout.decode('utf-8').strip()
    
    try:
        # Parse the JSON response
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse JSON response: {str(e)}"
        )


@router.get("/instamart/search")
async def search_instamart(query: str = "grapes", store_id: str = "1401254", save_to_db: bool = False):
    try:
        all_products = []
        page_num = 0
        has_more_pages = True
        
        while has_more_pages:
            response_data = await fetch_instamart_data(query, store_id, page_num)
            page_products = extract_products(response_data)
            all_products.extend(page_products)
            has_more_pages = response_data.get('data', {}).get('hasMorePages', False)
            page_num += 1
        
        if save_to_db and all_products:
            save_products_to_db(all_products, "products")
            
        exclude_fields = ["id", "created_at", "updated_at"]
        return [model_to_dict(product, exclude_fields=exclude_fields) for product in all_products]
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error executing Instamart search: {str(e)}"
        )