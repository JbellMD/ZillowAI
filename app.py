#!/usr/bin/env python3
"""
ZillowAI - Apartment Finder Agent
Main application entry point
"""

import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional, List

from zillow_ai.agent import ApartmentFinderAgent
from zillow_ai.models import SearchCriteria, SavedSearch
from zillow_ai.db import get_saved_searches, save_search, delete_search

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="ZillowAI Apartment Finder")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Initialize agent
agent = ApartmentFinderAgent()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main page"""
    return templates.TemplateResponse(
        "index.html", 
        {"request": request}
    )

@app.get("/search", response_class=HTMLResponse)
async def search_form(request: Request):
    """Render the search form"""
    default_location = os.getenv("DEFAULT_LOCATION", "New York, NY")
    default_min_price = int(os.getenv("DEFAULT_MIN_PRICE", "1500"))
    default_max_price = int(os.getenv("DEFAULT_MAX_PRICE", "3000"))
    default_bedrooms = int(os.getenv("DEFAULT_BEDROOMS", "2"))
    
    return templates.TemplateResponse(
        "search.html", 
        {
            "request": request,
            "default_location": default_location,
            "default_min_price": default_min_price,
            "default_max_price": default_max_price,
            "default_bedrooms": default_bedrooms
        }
    )

@app.post("/search", response_class=HTMLResponse)
async def perform_search(
    request: Request,
    location: str = Form(...),
    min_price: int = Form(...),
    max_price: int = Form(...),
    bedrooms: int = Form(2),
    bathrooms: Optional[str] = Form(None),
    pets_allowed: bool = Form(False),
    has_parking: bool = Form(False)
):
    """Perform apartment search based on form input"""
    # Convert bathrooms from string to float if provided
    bathrooms_float = None
    if bathrooms and bathrooms.strip():
        try:
            bathrooms_float = float(bathrooms)
        except ValueError:
            bathrooms_float = None
    
    criteria = SearchCriteria(
        location=location,
        min_price=min_price,
        max_price=max_price,
        bedrooms=bedrooms,
        bathrooms=bathrooms_float,
        pets_allowed=pets_allowed,
        has_parking=has_parking
    )
    
    try:
        results = await agent.search_apartments(criteria)
        return templates.TemplateResponse(
            "results.html", 
            {
                "request": request,
                "results": results,
                "criteria": criteria
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "error.html", 
            {
                "request": request,
                "error": str(e)
            }
        )

@app.get("/saved", response_class=HTMLResponse)
async def view_saved_searches(request: Request):
    """View all saved searches"""
    saved_searches = get_saved_searches()
    return templates.TemplateResponse(
        "saved.html", 
        {
            "request": request,
            "saved_searches": saved_searches
        }
    )

@app.post("/save")
async def save_search_route(
    search_name: str = Form(...),
    location: str = Form(...),
    min_price: int = Form(...),
    max_price: int = Form(...),
    bedrooms: int = Form(2)
):
    """Save a search for later use"""
    criteria = SearchCriteria(
        location=location,
        min_price=min_price,
        max_price=max_price,
        bedrooms=bedrooms
    )
    
    save_search(search_name, criteria)
    return RedirectResponse(url="/saved", status_code=303)

@app.post("/delete/{search_id}")
async def delete_search_route(search_id: str):
    """Delete a saved search"""
    delete_search(search_id)
    return RedirectResponse(url="/saved", status_code=303)

@app.get("/details/{property_id}", response_class=HTMLResponse)
async def property_details(request: Request, property_id: str):
    """View detailed information about a specific property"""
    try:
        details = await agent.get_property_details(property_id)
        return templates.TemplateResponse(
            "details.html", 
            {
                "request": request,
                "property": details
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "error.html", 
            {
                "request": request,
                "error": str(e)
            }
        )

@app.get("/chat", response_class=HTMLResponse)
async def chat_interface(request: Request):
    """Interactive chat interface with the apartment finder agent"""
    return templates.TemplateResponse(
        "chat.html", 
        {"request": request}
    )

@app.post("/api/chat")
async def chat_with_agent(message: str = Form(...)):
    """API endpoint for chatting with the agent"""
    response = await agent.chat(message)
    return {"response": response}

if __name__ == "__main__":
    # Run the FastAPI app with Uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
