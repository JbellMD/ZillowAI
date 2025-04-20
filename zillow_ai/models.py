"""
Data models for the ZillowAI apartment finder agent
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import uuid4

class SearchCriteria(BaseModel):
    """Model for apartment search criteria"""
    location: str
    min_price: int
    max_price: int
    bedrooms: int = 2
    bathrooms: Optional[float] = None
    pets_allowed: bool = False
    has_parking: bool = False
    min_square_feet: Optional[int] = None
    max_square_feet: Optional[int] = None
    keywords: Optional[List[str]] = None
    home_types: Optional[List[str]] = None
    
    def to_api_params(self) -> Dict[str, Any]:
        """Convert search criteria to Zillow API parameters"""
        params = {
            "location": self.location,
            "minPrice": self.min_price,
            "maxPrice": self.max_price,
            "beds": self.bedrooms,
        }
        
        if self.bathrooms:
            params["baths"] = self.bathrooms
        
        if self.min_square_feet:
            params["minSquareFeet"] = self.min_square_feet
        
        if self.max_square_feet:
            params["maxSquareFeet"] = self.max_square_feet
        
        if self.home_types:
            params["homeTypes"] = ",".join(self.home_types)
        
        # Pets and parking will need to be filtered client-side as not all APIs expose these directly
        
        return params

class Property(BaseModel):
    """Model for property data"""
    id: str
    address: str
    city: str
    state: str
    zipcode: str
    price: int
    bedrooms: int
    bathrooms: float
    square_feet: Optional[int] = None
    description: Optional[str] = None
    year_built: Optional[int] = None
    url: str
    image_urls: List[str] = []
    pets_allowed: Optional[bool] = None
    has_parking: Optional[bool] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    listing_date: Optional[datetime] = None
    property_type: Optional[str] = None
    tags: List[str] = []
    
class SavedSearch(BaseModel):
    """Model for saved searches"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    criteria: SearchCriteria
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class AgentMessage(BaseModel):
    """Model for agent-user chat messages"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
class Conversation(BaseModel):
    """Model for conversation history"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    messages: List[AgentMessage] = []
    
    def add_message(self, role: str, content: str):
        """Add a message to the conversation"""
        self.messages.append(AgentMessage(role=role, content=content))
        
    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history in a format suitable for the OpenAI API"""
        return [{"role": msg.role, "content": msg.content} for msg in self.messages]
