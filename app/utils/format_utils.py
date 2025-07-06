from typing import Any, Dict, List
from datetime import datetime

def model_to_dict(model: Any, exclude_fields: List[str] = None) -> Dict[str, Any]:
    if model is None:
        return {}
        
    exclude_fields = exclude_fields or []
    
    result = {}
    for key, value in model.__dict__.items():
        if not key.startswith('_') and key not in exclude_fields:
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            else:
                result[key] = value
                
    return result
