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
        self.base_url = "https://zillow-com1.p.rapidapi.com"
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _make_api_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to the Zillow API with retry logic"""
        if not self.api_key:
            raise ValueError("Zillow API key is not set. Please set the ZILLOW_API_KEY environment variable.")
        
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com"
        }
        
        url = f"{self.base_url}/{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"API request failed: {error_text}")
                    
                    # Better error messages for common issues
                    if "not subscribed" in error_text.lower():
                        raise Exception("You are not subscribed to the Zillow API on RapidAPI. Please visit RapidAPI and subscribe to the Zillow API endpoint.")
                    elif "too many requests" in error_text.lower():
                        raise Exception("Rate limit exceeded. Your subscription plan may have limits on the number of requests.")
                    else:
                        raise Exception(f"API request failed with status {response.status}: {error_text}")
                
                data = await response.json()
                return data
    
    async def search_apartments(self, criteria: SearchCriteria) -> List[Property]:
        """Search for apartments based on the given criteria"""
        logger.info(f"Searching for apartments with criteria: {criteria}")
        
        # Convert criteria to API parameters for RapidAPI Zillow endpoint
        params = {
            "location": criteria.location,
            "page": "1",
            "status_type": "ForRent",
            "home_type": "Apartments",
            "beds": str(criteria.bedrooms),
            "test": "true"  # Enable test mode
        }
        
        try:
            # Make the API request to the property search endpoint
            response_data = await self._make_api_request("propertyExtendedSearch", params)
            
            # Parse the results from RapidAPI Zillow format
            properties = []
            
            if "props" in response_data and isinstance(response_data["props"], list):
                for item in response_data["props"]:
                    try:
                        # Extract price as integer (remove non-numeric characters)
                        price_str = item.get("price", "0")
                        price_str = str(price_str) if price_str is not None else "0"
                        price = int(''.join(filter(str.isdigit, price_str))) if price_str else 0
                        
                        # Skip if price is outside the criteria range
                        if price < criteria.min_price or (criteria.max_price > 0 and price > criteria.max_price):
                            continue
                        
                        # Extract bedrooms as integer
                        bedrooms_str = item.get("bedrooms", "0")
                        bedrooms_str = str(bedrooms_str) if bedrooms_str is not None else "0"
                        bedrooms = int(bedrooms_str) if bedrooms_str and bedrooms_str.isdigit() else 0
                        
                        # Extract bathrooms as float
                        bathrooms_str = item.get("bathrooms", "0")
                        bathrooms_str = str(bathrooms_str) if bathrooms_str is not None else "0"
                        bathrooms = float(bathrooms_str) if bathrooms_str and bathrooms_str.replace('.', '').isdigit() else 0
                        
                        # Parse square feet
                        sqft_str = item.get("livingArea", "")
                        sqft_str = str(sqft_str) if sqft_str is not None else ""
                        square_feet = int(''.join(filter(str.isdigit, sqft_str))) if sqft_str else None
                        
                        # Create Property object
                        prop = Property(
                            id=str(item.get("zpid", "")),
                            address=item.get("address", {}).get("streetAddress", ""),
                            city=item.get("address", {}).get("city", ""),
                            state=item.get("address", {}).get("state", ""),
                            zipcode=item.get("address", {}).get("zipcode", ""),
                            price=price,
                            bedrooms=bedrooms,
                            bathrooms=bathrooms,
                            square_feet=square_feet,
                            description=item.get("description", ""),
                            year_built=item.get("yearBuilt"),
                            url=f"https://www.zillow.com/homedetails/{item.get('zpid', '')}_zpid/",
                            image_urls=[item.get("imgSrc", "")] if item.get("imgSrc") else [],
                            latitude=item.get("latitude"),
                            longitude=item.get("longitude"),
                            property_type=item.get("propertyType", "Apartment"),
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
    
    async def get_property_details(self, property_id: str) -> Property:
        """Get detailed information about a specific property"""
        logger.info(f"Getting details for property {property_id}")
        
        # First check if we have this property in our last search results
        for prop in self.last_search_results:
            if prop.id == property_id:
                return prop
        
        # If not found in cache, fetch from API
        try:
            # Set up parameters for the property details endpoint
            params = {
                "zpid": property_id,
                "test": "true"  # Enable test mode
            }
            
            # Make the API request to the property details endpoint
            response_data = await self._make_api_request("property", params)
            
            if not response_data:
                raise ValueError(f"No data returned for property ID {property_id}")
            
            # Extract price as integer (remove non-numeric characters)
            price_str = response_data.get("price", "0")
            price_str = str(price_str) if price_str is not None else "0"
            price = int(''.join(filter(str.isdigit, price_str))) if price_str else 0
            
            # Extract address components
            address = response_data.get("address", {})
            
            # Create Property object from the detailed data
            prop = Property(
                id=property_id,
                address=address.get("streetAddress", ""),
                city=address.get("city", ""),
                state=address.get("state", ""),
                zipcode=address.get("zipcode", ""),
                price=price,
                bedrooms=int(response_data.get("bedrooms", 0)),
                bathrooms=float(response_data.get("bathrooms", 0)),
                square_feet=response_data.get("livingArea"),
                description=response_data.get("description", ""),
                year_built=response_data.get("yearBuilt"),
                url=f"https://www.zillow.com/homedetails/{property_id}_zpid/",
                image_urls=response_data.get("images", []) if response_data.get("images") else [response_data.get("imgSrc", "")],
                latitude=response_data.get("latitude"),
                longitude=response_data.get("longitude"),
                property_type=response_data.get("propertyType", "Apartment"),
                pets_allowed=self._extract_pet_policy(response_data),
                has_parking=self._extract_parking_info(response_data)
            )
            
            return prop
            
        except Exception as e:
            logger.error(f"Error fetching property details: {e}")
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
