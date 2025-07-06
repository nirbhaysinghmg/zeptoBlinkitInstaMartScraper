-- migrations.sql
-- Create products table for Supabase (PostgreSQL)

CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    search_query TEXT,
    
    -- Store details
    store_id TEXT,
    
    -- Product identifiers
    product_id TEXT NOT NULL,
    variant_id TEXT,
    
    -- Product details
    name TEXT NOT NULL,
    brand TEXT,
    
    -- Price information
    mrp DECIMAL,
    price DECIMAL NOT NULL,
    
    -- Quantity and inventory
    quantity TEXT,
    in_stock BOOLEAN DEFAULT FALSE,
    inventory INTEGER,
    max_allowed_quantity INTEGER,
    
    -- Categories
    category TEXT,
    sub_category TEXT,
    
    -- Images
    images TEXT[],  -- Array of image URLs
    
    -- Search and ranking
    organic_rank INTEGER,
    page INTEGER,
    
    -- Rating
    rating DECIMAL,
    
    -- Platform-specific details
    platform_specific_details JSONB,  -- Using JSONB for better performance with JSON data
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for faster querying
CREATE INDEX IF NOT EXISTS idx_products_platform ON products(platform);
CREATE INDEX IF NOT EXISTS idx_products_product_id ON products(product_id);
CREATE INDEX IF NOT EXISTS idx_products_store_id ON products(store_id);
CREATE INDEX IF NOT EXISTS idx_products_variant_id ON products(variant_id);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update the updated_at column
CREATE TRIGGER set_timestamp
BEFORE UPDATE ON products
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();
