import asyncio
from typing import List, Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from .search_instamart import search_instamart
from .search_zepto import search_zepto
from .search_blinkit import search_blinkit

router = APIRouter()

class SearchParams(BaseModel):
    queries: List[str] = Field(..., description="List of search queries to execute")
    instamart_store_ids: List[str] = Field(..., description="List of Instamart store IDs to search in")
    zepto_store_ids: List[str] = Field(..., description="List of Zepto store IDs to search in")
    blinkit_coordinates: List[str] = Field(..., description="List of Blinkit coordinates as {lat, lon} objects")
    save_to_db: bool = Field(False, description="Whether to save search results to the database")

class SearchResult(BaseModel):
    platform: str
    query: str
    store: Optional[str] = None
    products: List[Dict[str, Any]]

async def create_platform_result(platform: str, query: str, store: str = None, save_to_db: bool = False) -> SearchResult:
    try:
        products = []
        
        if platform == "instamart":
            products = await search_instamart(query=query, store_id=store, save_to_db=save_to_db)
        elif platform == "zepto":
            products = await search_zepto(query=query, store_id=store, save_to_db=save_to_db)
        elif platform == "blinkit":
            products = await search_blinkit(query=query, coordinates=store, save_to_db=save_to_db)
        else:
            raise ValueError(f"Unknown platform: {platform}")
        
        return SearchResult(
            platform=platform,
            query=query,
            store=store,
            products=products
        )
            
    except Exception as e:
        print(f"Error in {platform} search for query '{query}', location '{store}': {str(e)}")
        
        return SearchResult(
            platform=platform,
            query=query,
            store=store,
            products=[]
        )

@router.post("/search/all", response_model=List[SearchResult])
async def search_all_platforms(search_params: SearchParams) -> List[SearchResult]:

    all_results = []
    tasks = []
    
    for query in search_params.queries:
        for store_id in search_params.instamart_store_ids:
            tasks.append(create_platform_result("instamart", query, store=store_id, save_to_db=search_params.save_to_db))
    
    for query in search_params.queries:
        for store_id in search_params.zepto_store_ids:
            tasks.append(create_platform_result("zepto", query, store=store_id, save_to_db=search_params.save_to_db))
    
    for query in search_params.queries:
        for coords in search_params.blinkit_coordinates:
            # Assuming coords is a string like "lat,lon"
            tasks.append(create_platform_result("blinkit", query, store=coords, save_to_db=search_params.save_to_db))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if not isinstance(result, Exception):
            all_results.append(result)
    
    return all_results