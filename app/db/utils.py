import logging
import uuid
from typing import List, Dict, Any, Type, Optional, Union
from sqlalchemy.ext.declarative import DeclarativeMeta
from datetime import datetime
import json

from .client import supabase

def save_products_to_db(products: List[Any], table_name: str, exclude_fields: List[str] = None) -> bool:
    if not supabase:
        logging.warning(f"Supabase client not initialized. Products will not be saved to {table_name}.")
        return False
    
    if not products:
        logging.warning(f"No products to save to {table_name}.")
        return True
    
    exclude_fields = exclude_fields or []
    
    try:
        product_dicts = []
        
        for product in products:
            product_dict = {}
            for key, value in product.__dict__.items():
                if not key.startswith('_') and key not in exclude_fields:
                    if key == 'id' and (value is None or value == ''):
                        product_dict[key] = str(uuid.uuid4())
                    else:
                        product_dict[key] = value
            
            # If id wasn't in the dict at all, add it
            if 'id' not in product_dict:
                product_dict['id'] = str(uuid.uuid4())
            
            product_dicts.append(product_dict)
        
        logging.info(f"Attempting to save {len(product_dicts)} products to Supabase table '{table_name}'")
        logging.info(f"First product sample: {json.dumps(product_dicts[0], default=str)[:200]}...")
        
        result = supabase.table(table_name).insert(product_dicts).execute()
        
        if hasattr(result, 'error') and result.error:
            logging.error(f"Error saving products to {table_name}: {result.error}")
            return False
            
        if hasattr(result, 'data'):
            logging.info(f"Supabase response data: {json.dumps(result.data)[:200]}...")
        
        logging.info(f"Successfully saved {len(products)} products to {table_name}")
        return True
    except Exception as e:
        logging.error(f"Exception saving products to {table_name}: {str(e)}")
        logging.exception("Detailed error:")
        return False
