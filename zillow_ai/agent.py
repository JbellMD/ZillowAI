"""
ApartmentFinderAgent - Core agent for searching apartments using Zillow API
"""

import os
import json
import aiohttp
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import SearchCriteria, Property, Conversation

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ApartmentFinderAgent:
    """Agent for finding apartments using Zillow API"""
    
    def __init__(self):
        """Initialize the apartment finder agent"""
        self.api_key = os.getenv("ZILLOW_API_KEY")
        if not self.api_key:
            logger.warning("ZILLOW_API_KEY not found in environment variables")
            
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables")
            
        self.conversation = Conversation()
        self.last_search_results = []
        self.base_url = "https://api.bridgedataoutput.com/api/v2/zestimates/zestimates"
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _make_api_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to the Zillow API with retry logic"""
        if not self.api_key:
            raise ValueError("Zillow API key is not set. Please set the ZILLOW_API_KEY environment variable.")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"API request failed: {error_text}")
                    raise Exception(f"API request failed with status {response.status}: {error_text}")
                
                data = await response.json()
                return data
    
    async def search_apartments(self, criteria: SearchCriteria) -> List[Property]:
        """Search for apartments based on the given criteria"""
        logger.info(f"Searching for apartments with criteria: {criteria}")
        
        # Convert criteria to API parameters
        params = criteria.to_api_params()
        
        try:
            # Make the API request
            response_data = await self._make_api_request("search", params)
            
            # Parse the results
            properties = []
            for item in response_data.get("bundle", []):
                try:
                    prop = Property(
                        id=item.get("id", ""),
                        address=item.get("address", {}).get("line", ""),
                        city=item.get("address", {}).get("city", ""),
                        state=item.get("address", {}).get("state", ""),
                        zipcode=item.get("address", {}).get("postalCode", ""),
                        price=int(item.get("price", 0)),
                        bedrooms=int(item.get("bedrooms", 0)),
                        bathrooms=float(item.get("bathrooms", 0)),
                        square_feet=item.get("livingArea"),
                        description=item.get("description", ""),
                        year_built=item.get("yearBuilt"),
                        url=item.get("detailUrl", ""),
                        image_urls=[img.get("url", "") for img in item.get("media", []) if img.get("mediaType") == "image"],
                        latitude=item.get("geo", {}).get("latitude"),
                        longitude=item.get("geo", {}).get("longitude"),
                        property_type=item.get("propertyType"),
                        pets_allowed=self._extract_pet_policy(item),
                        has_parking=self._extract_parking_info(item)
                    )
                    properties.append(prop)
                except Exception as e:
                    logger.error(f"Error parsing property data: {e}")
            
            # Store results for later use
            self.last_search_results = properties
            
            # Apply client-side filtering for pets and parking if needed
            if criteria.pets_allowed:
                properties = [p for p in properties if p.pets_allowed == True]
                
            if criteria.has_parking:
                properties = [p for p in properties if p.has_parking == True]
            
            logger.info(f"Found {len(properties)} matching properties")
            return properties
            
        except Exception as e:
            logger.error(f"Error searching for apartments: {e}")
            raise
    
    def _extract_pet_policy(self, property_data: Dict[str, Any]) -> Optional[bool]:
        """Extract pet policy from property data"""
        # This is a simplified implementation - real implementation would need to parse
        # description or amenities based on the actual Zillow API response structure
        description = property_data.get("description", "").lower()
        amenities = property_data.get("amenities", [])
        
        # Look for pet-friendly indicators
        pet_keywords_positive = ["pet friendly", "pets allowed", "pet-friendly", "dogs allowed", "cats allowed"]
        pet_keywords_negative = ["no pets", "pets not allowed", "no dogs", "no cats"]
        
        # Check amenities
        for amenity in amenities:
            if amenity == "Pets Allowed":
                return True
                
        # Check description
        for keyword in pet_keywords_positive:
            if keyword in description:
                return True
                
        for keyword in pet_keywords_negative:
            if keyword in description:
                return False
                
        return None  # Unknown
    
    def _extract_parking_info(self, property_data: Dict[str, Any]) -> Optional[bool]:
        """Extract parking information from property data"""
        # This is a simplified implementation - real implementation would need to parse
        # description or amenities based on the actual Zillow API response structure
        description = property_data.get("description", "").lower()
        amenities = property_data.get("amenities", [])
        
        # Look for parking indicators
        parking_keywords = ["parking", "garage", "carport", "covered parking", "parking spot", "parking space"]
        
        # Check amenities
        for amenity in amenities:
            if "parking" in amenity.lower() or "garage" in amenity.lower():
                return True
                
        # Check description
        for keyword in parking_keywords:
            if keyword in description:
                return True
                
        return None  # Unknown
    
    async def get_property_details(self, property_id: str) -> Property:
        """Get detailed information about a specific property"""
        logger.info(f"Getting details for property {property_id}")
        
        # First check if we have this property in our last search results
        for prop in self.last_search_results:
            if prop.id == property_id:
                return prop
        
        # If not found in cache, fetch from API
        try:
            response_data = await self._make_api_request(f"property/{property_id}", {})
            
            property_data = response_data.get("property", {})
            
            prop = Property(
                id=property_id,
                address=property_data.get("address", {}).get("line", ""),
                city=property_data.get("address", {}).get("city", ""),
                state=property_data.get("address", {}).get("state", ""),
                zipcode=property_data.get("address", {}).get("postalCode", ""),
                price=int(property_data.get("price", 0)),
                bedrooms=int(property_data.get("bedrooms", 0)),
                bathrooms=float(property_data.get("bathrooms", 0)),
                square_feet=property_data.get("livingArea"),
                description=property_data.get("description", ""),
                year_built=property_data.get("yearBuilt"),
                url=property_data.get("detailUrl", ""),
                image_urls=[img.get("url", "") for img in property_data.get("media", []) if img.get("mediaType") == "image"],
                latitude=property_data.get("geo", {}).get("latitude"),
                longitude=property_data.get("geo", {}).get("longitude"),
                property_type=property_data.get("propertyType"),
                pets_allowed=self._extract_pet_policy(property_data),
                has_parking=self._extract_parking_info(property_data)
            )
            
            return prop
            
        except Exception as e:
            logger.error(f"Error fetching property details: {e}")
            raise
    
    async def chat(self, message: str) -> str:
        """Chat with the apartment finder agent"""
        import openai
        
        # Add user message to conversation
        self.conversation.add_message("user", message)
        
        if not self.openai_api_key:
            return "OpenAI API key is not set. Please set the OPENAI_API_KEY environment variable."
        
        try:
            openai.api_key = self.openai_api_key
            
            # Get the conversation history
            messages = self.conversation.get_history()
            
            # Add system message
            system_message = {
                "role": "system", 
                "content": "You are ZillowAI, an apartment finder assistant. You help users find 2-bedroom apartments based on their preferences. You can provide information about apartment features, prices, locations, and amenities."
            }
            messages.insert(0, system_message)
            
            # Get response from OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-4-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            # Extract response content
            assistant_response = response.choices[0].message.content
            
            # Add assistant response to conversation
            self.conversation.add_message("assistant", assistant_response)
            
            return assistant_response
            
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return f"I'm sorry, I encountered an error: {str(e)}"
