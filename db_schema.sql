-- Table creation for Blinkit products
CREATE TABLE IF NOT EXISTS blinkit_products (
    id VARCHAR PRIMARY KEY,
    search_query VARCHAR,
    product_id VARCHAR NOT NULL,
    product_name VARCHAR NOT NULL,
    display_name VARCHAR,
    price FLOAT NOT NULL,
    mrp FLOAT,
    unit VARCHAR,
    quantity FLOAT,
    inventory INTEGER,
    brand VARCHAR,
    merchant_id VARCHAR,
    merchant_type VARCHAR,
    group_id VARCHAR,
    is_sold_out BOOLEAN DEFAULT FALSE,
    product_state VARCHAR,
    is_variant BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index on product_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_blinkit_products_product_id ON blinkit_products(product_id);

-- Create a trigger to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_blinkit_products_updated_at
BEFORE UPDATE ON blinkit_products
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Function to automatically set UUID for new records if not provided
CREATE OR REPLACE FUNCTION set_uuid_if_not_provided()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.id IS NULL THEN
        NEW.id = uuid_generate_v4()::text;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_set_blinkit_products_uuid
BEFORE INSERT ON blinkit_products
FOR EACH ROW
EXECUTE FUNCTION set_uuid_if_not_provided();

-- Make sure the uuid-ossp extension is enabled for uuid_generate_v4()
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
