import uuid
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    
    id = Column(String, primary_key=True, nullable=False, default=str(uuid.uuid4()))
    platform = Column(String, nullable=False)  # 'zepto', 'blinkit', 'instamart'
    search_query = Column(String)
    
    # Store details
    store_id = Column(String, index=True)
    
    # Product identifiers
    product_id = Column(String, index=True, nullable=False)
    variant_id = Column(String, index=True, nullable=False)
    
    # Product details
    name = Column(String, nullable=False)
    brand = Column(String)
    
    # Price information
    mrp = Column(Float)
    price = Column(Float, nullable=False)
    
    # Quantity and inventory
    quantity = Column(String)
    in_stock = Column(Boolean, default=False)
    inventory = Column(Integer)
    max_allowed_quantity = Column(Integer)
    
    # Categories
    category = Column(String)
    sub_category = Column(String)
    
    # Images
    images = Column(ARRAY(String))
    
    # Search and ranking
    organic_rank = Column(Integer)
    page = Column(Integer)

    # Rating
    rating = Column(Float)

    # Platform-specific details
    platform_specific_details = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<Product(variant_id={self.variant_id}, platform='{self.platform}', name='{self.name}')>"