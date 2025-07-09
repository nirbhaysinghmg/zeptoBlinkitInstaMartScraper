import os
import json
import logging
import gzip
import io
import asyncio
import pycurl
import pandas as pd
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from playwright.async_api import async_playwright
import subprocess
from app.db.models import Product
from app.db.utils import save_products_to_db
from app.utils.format_utils import model_to_dict
import requests

router = APIRouter()

CURL_DIR = "curls/zepto"
CSV_PATH = "stores_rows.csv"
STORE_ID_PLACEHOLDER = "REPLACE_ME_STORE_ID"


# ------------------ UTILITIES ------------------

def slugify(text):
    return text.lower().replace(" ", "-")


def get_curl_path(query):
    return os.path.join(CURL_DIR, f"{slugify(query)}.json")


def is_curl_fresh(query):
    path = get_curl_path(query)
    if not os.path.exists(path):
        return False
    with open(path) as f:
        data = json.load(f)
    ts = datetime.fromisoformat(data['timestamp']) 
    return datetime.utcnow() - ts <= timedelta(hours=1)


def save_curl_config(query, requests):
    os.makedirs(CURL_DIR, exist_ok=True)
    path = get_curl_path(query)
    with open(path, "w") as f:
        json.dump({
            "query": query,
            "timestamp": datetime.utcnow().isoformat(),
            "requests": requests
        }, f, indent=2)


def get_zepto_store_ids(csv_path=CSV_PATH):
    df = pd.read_csv(csv_path)
    return df[df['platform'] == 'zepto']['id'].dropna().unique().tolist()


def extract_page_number(body: str):
    try:
        data = json.loads(body)
        return int(data.get("pageNumber", 0))
    except Exception:
        return None


async def auto_scroll(page, max_scrolls=20):
    await page.evaluate(f"""
        async () => {{
            await new Promise((resolve) => {{
                let count = 0;
                const timer = setInterval(() => {{
                    window.scrollBy(0, 500);
                    count++;
                    if (count >= {max_scrolls}) {{
                        clearInterval(timer);
                        resolve();
                    }}
                }}, 500);
            }});
        }}
    """)


async def capture_curl_requests(query: str, max_pages: int = 20) -> list:
    captured_requests = {}

    TOKEN = "SGcRKOOtIgojygd93388f5e2dd930945e1ed50d152"
    BROWSERLESS_ENDPOINT = f"wss://production-sfo.browserless.io/firefox/playwright?token={TOKEN}&proxy=residential&proxyCountry=in"

    async with async_playwright() as p:
        # Use the browser_type.connect_over_cdp if it's a Chromium-based endpoint or connect() for WebSocket
        browser = await p.firefox.connect(BROWSERLESS_ENDPOINT)
        context = await browser.new_context()
        page = await context.new_page()

        search_url = f"https://www.zeptonow.com/search?query={query.replace(' ', '+')}"

        def handle_request(request):
            if (
                request.resource_type in ['fetch', 'xhr']
                and request.url.startswith("https://api.zeptonow.com/api/v3/search")
            ):
                post_data = request.post_data or ""
                page_number = extract_page_number(post_data)
                if page_number is not None and page_number not in captured_requests:
                    headers = request.headers
                    # Headers to exclude
                    headers_to_exclude = [
                        'host', 'accept-language', 'accept-encoding', 'sec-fetch-dest', 
                        'sec-fetch-mode', 'sec-fetch-site', 'connection', 'origin', 'content-length'
                    ]
                    
                    # Initial cleaning - replace store IDs and exclude specified headers
                    clean_headers = {
                        k: (STORE_ID_PLACEHOLDER if "store" in k.lower() else v)
                        for k, v in headers.items()
                        if k.lower() not in headers_to_exclude
                    }
                    
                    # Add required browser headers
                    required_headers = {
                        'sec-ch-ua': '"Not A(Brand";v="99", "HeadlessChrome";v="121", "Chromium";v="121"',
                        'sec-ch-ua-platform': '"macOS"',
                        'sec-ch-ua-mobile': '?0',
                        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/121.0.6167.57 Safari/537.36'
                    }
                    
                    # Add required headers
                    clean_headers.update(required_headers)
                    clean_body = post_data.replace("store_id", STORE_ID_PLACEHOLDER)

                    captured_requests[page_number] = {
                        "url": request.url,
                        "method": request.method,
                        "headers": clean_headers,
                        "body": clean_body
                    }

        page.on("request", handle_request)

        await page.goto(search_url)
        await auto_scroll(page, max_scrolls=max_pages)
        await asyncio.sleep(5)
        await browser.close()

    return [captured_requests[p] for p in sorted(captured_requests.keys())]


async def ensure_fresh_curls(query: str) -> list:
    if is_curl_fresh(query):
        with open(get_curl_path(query)) as f:
            return json.load(f)["requests"]

    captured_requests = await capture_curl_requests(query)
    save_curl_config(query, captured_requests)
    return captured_requests


def replace_store_placeholders(req: dict, store_id: str) -> dict:
    store_etas = json.dumps({store_id: 10})

    updated_headers = {
        k: v.replace(STORE_ID_PLACEHOLDER, store_id)
        if isinstance(v, str) else v
        for k, v in req["headers"].items()
    }
    updated_headers.update({
        "store_id": store_id,
        "storeId": store_id,
        "store_ids": store_id,
        "store_etas": store_etas
    })

    updated_body = req["body"].replace(STORE_ID_PLACEHOLDER, store_id)

    return {
        "url": req["url"],
        "method": req["method"],
        "headers": updated_headers,
        "body": updated_body
    }



def run_curl_request(req: dict) -> dict:
    url = req["url"]
    headers = req.get("headers", {})
    body = req.get("body", "")

    try:
        response = requests.post(
            url,
            headers=headers,
            data=body,
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"[HTTP ERROR] Request failed: {e}")
    except json.JSONDecodeError as e:
        print("[DEBUG] Response was not valid JSON:")
        raise RuntimeError(f"Failed to parse JSON: {e}")


def extract_products(response_data: dict, query: str):
    products = []
    layouts = response_data.get("layout", [])

    for layout in layouts:
        if layout.get("widgetId") == "PRODUCT_GRID":
            items = layout.get("data", {}).get("resolver", {}).get("data", {}).get("items", [])
            
            for item in items:
                try:
                    product_resp = item.get("productResponse", {})
                    product = product_resp.get("product", {}) or {}
                    product_variant = product_resp.get("productVariant", {}) or {}

                    images = product_variant.get("images", []) or product.get("images", []) or []
                    image_urls = [img.get("path") for img in images if img.get("path")]

                    product_model = Product(
                        platform='zepto',
                        search_query=query,
                        store_id=product_resp.get("storeId"),
                        product_id=product.get("id"),
                        variant_id=product_variant.get("id"),
                        name=product.get("name"),
                        brand=product.get("brand"),
                        mrp=product_resp.get("mrp"),
                        price=product_resp.get("sellingPrice"),
                        quantity=product_variant.get("formattedPacksize") or "",
                        in_stock=not product_resp.get("outOfStock", False),
                        inventory=product_resp.get("availableQuantity"),
                        max_allowed_quantity=product_variant.get("maxAllowedQuantity"),
                        category=product_resp.get("primaryCategoryName"),
                        sub_category=product_resp.get("primarySubcategoryName"),
                        images=image_urls,
                        organic_rank=item.get("position"),
                        page=response_data.get("currentPage", 0),
                        rating=(product_variant.get("ratingSummary") or {}).get("averageRating"),
                        platform_specific_details=json.dumps({
                            "ratings_count": (product_variant.get("ratingSummary") or {}).get("totalRatings"),
                        }),
                    )

                    products.append(product_model)

                except Exception as e:
                    print(f"[ERROR] Skipped product due to exception: {e}")
                    continue

    return products

# ------------------ FASTAPI ROUTER -----------------

@router.get("/zepto/search")
async def search_zepto(
    query: str = "milk",
    store_id: str = None,
    save_to_db: bool = False
):
    if not store_id:
        raise HTTPException(status_code=400, detail="store_id is required")

    try:
        all_products = []
        curls = await ensure_fresh_curls(query)

        for base_req in curls:
            try:
                req = replace_store_placeholders(base_req, store_id)
                print("printing request")
                print(req)
                response_data = run_curl_request(req)
                print("printing response")
                print(response_data)
                page_products = extract_products(response_data, query) or []
                all_products.extend(page_products)
            except Exception as e:
                logging.error(f"Store {store_id} request failed: {e}")
                continue

        if save_to_db and all_products:
            save_products_to_db(all_products, "products")
        exclude_fields = ["id", "created_at", "updated_at"]
        return [model_to_dict(p, exclude_fields) for p in all_products]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
