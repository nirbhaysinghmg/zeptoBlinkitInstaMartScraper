import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Print Supabase environment variables
print(f"SUPABASE_URL: {os.environ.get('SUPABASE_URL')}")
print(f"SUPABASE_KEY: {os.environ.get('SUPABASE_KEY')}")
