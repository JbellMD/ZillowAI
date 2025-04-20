"""
Database utilities for the ZillowAI apartment finder agent
"""

import os
import json
import logging
from typing import List, Dict, Any
from pathlib import Path
from .models import SearchCriteria, SavedSearch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define database file path
DB_DIR = Path("data")
SAVED_SEARCHES_FILE = DB_DIR / "saved_searches.json"

def _ensure_db_initialized():
    """Ensure the database directory and files exist"""
    if not DB_DIR.exists():
        DB_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created database directory at {DB_DIR}")
    
    if not SAVED_SEARCHES_FILE.exists():
        with open(SAVED_SEARCHES_FILE, 'w') as f:
            json.dump([], f)
        logger.info(f"Created saved searches file at {SAVED_SEARCHES_FILE}")

def get_saved_searches() -> List[SavedSearch]:
    """Get all saved searches"""
    _ensure_db_initialized()
    
    try:
        with open(SAVED_SEARCHES_FILE, 'r') as f:
            data = json.load(f)
            
        # Convert to SavedSearch objects
        saved_searches = []
        for item in data:
            criteria_dict = item.get("criteria", {})
            criteria = SearchCriteria(**criteria_dict)
            
            saved_search = SavedSearch(
                id=item.get("id"),
                name=item.get("name"),
                criteria=criteria,
                created_at=item.get("created_at")
            )
            saved_searches.append(saved_search)
            
        return saved_searches
    except Exception as e:
        logger.error(f"Error getting saved searches: {e}")
        return []

def save_search(name: str, criteria: SearchCriteria) -> SavedSearch:
    """Save a search for later use"""
    _ensure_db_initialized()
    
    try:
        # Create new saved search
        saved_search = SavedSearch(name=name, criteria=criteria)
        
        # Get existing saved searches
        saved_searches = get_saved_searches()
        
        # Check if a search with this name already exists
        for i, search in enumerate(saved_searches):
            if search.name == name:
                # Update existing search
                saved_searches[i] = saved_search
                break
        else:
            # Add new search
            saved_searches.append(saved_search)
        
        # Save to file
        _save_searches_to_file(saved_searches)
        
        logger.info(f"Saved search '{name}'")
        return saved_search
    except Exception as e:
        logger.error(f"Error saving search: {e}")
        raise

def delete_search(search_id: str) -> bool:
    """Delete a saved search by ID"""
    _ensure_db_initialized()
    
    try:
        # Get existing saved searches
        saved_searches = get_saved_searches()
        
        # Find and remove the search with the given ID
        for i, search in enumerate(saved_searches):
            if search.id == search_id:
                del saved_searches[i]
                _save_searches_to_file(saved_searches)
                logger.info(f"Deleted search with ID {search_id}")
                return True
        
        logger.warning(f"Search with ID {search_id} not found")
        return False
    except Exception as e:
        logger.error(f"Error deleting search: {e}")
        return False

def _save_searches_to_file(saved_searches: List[SavedSearch]):
    """Save searches to file"""
    try:
        # Convert to dicts
        data = []
        for search in saved_searches:
            search_dict = {
                "id": search.id,
                "name": search.name,
                "criteria": search.criteria.dict(),
                "created_at": search.created_at.isoformat()
            }
            data.append(search_dict)
        
        # Save to file
        with open(SAVED_SEARCHES_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving searches to file: {e}")
        raise
