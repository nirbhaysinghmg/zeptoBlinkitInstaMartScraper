import os
import json
from datetime import datetime
from typing import Any, Dict, List, Union

def write_to_output_file(data: Union[Dict, List, str], filename: str = None, prefix: str = None) -> str:
    # Get project root directory (two levels up from this file)
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    outputs_dir = os.path.join(current_dir, "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    
    # Generate filename if not provided
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix + '_' if prefix else ''}{timestamp}.json" if isinstance(data, (dict, list)) else f"{prefix + '_' if prefix else ''}{timestamp}.txt"
    
    if isinstance(data, (dict, list)) and not filename.endswith('.json'):
        filename += '.json'
    elif isinstance(data, str) and not filename.endswith('.txt'):
        filename += '.txt'
    
    file_path = os.path.join(outputs_dir, filename)
    
    try:
        if isinstance(data, (dict, list)):
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(str(data))
        
        print(f"Data written to {file_path}")
        return file_path
    except Exception as e:
        print(f"Error writing to output file: {str(e)}")
        return None