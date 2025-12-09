"""FastAPI application for NPIDB home health agency scraper."""

import logging
import csv
from typing import List, Optional
from pathlib import Path
import os
import json

from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .models import HomeHealthAgency, BatchScrapeResult, CreateListRequest
from .scraper import scrape_home_health_agencies
from .storage import get_storage, SupabaseStorage

# Load environment variables
load_dotenv()

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Try to import alternative scrapers
try:
    from .scraper_curl_cffi import scrape_home_health_agencies_curl_cffi
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False
    logger.warning("curl_cffi not available")

try:
    from .scraper_selenium import scrape_home_health_agencies_selenium
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Initialize storage (will be None if Supabase not configured)
storage: Optional[SupabaseStorage] = get_storage()

app = FastAPI(
    title="NPIDB Home Health Scraper",
    description="Scrape home health agency data from NPIDB (npidb.org)",
    version="1.0.0",
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory and serve index.html at root
# Try React frontend first, fall back to vanilla JS frontend
frontend_react_path = Path(__file__).parent.parent / "frontend-react" / "dist"
frontend_path = Path(__file__).parent.parent / "frontend"

# Serve React frontend if built, otherwise serve vanilla JS frontend
if frontend_react_path.exists() and (frontend_react_path / "index.html").exists():
    # Serve React frontend
    app.mount("/static", StaticFiles(directory=str(frontend_react_path)), name="static")
    app.mount("/assets", StaticFiles(directory=str(frontend_react_path / "assets")), name="assets")
    
    @app.get("/app")
    async def serve_frontend():
        """Serve the React frontend application."""
        from fastapi.responses import FileResponse
        index_path = frontend_react_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        raise HTTPException(status_code=404, detail="Frontend not found")
elif frontend_path.exists():
    # Serve vanilla JS frontend
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")
    
    @app.get("/app")
    async def serve_frontend():
        """Serve the frontend application."""
        from fastapi.responses import FileResponse
        index_path = frontend_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        raise HTTPException(status_code=404, detail="Frontend not found")


@app.get("/")
async def root():
    """Root endpoint - redirects to frontend or shows API info."""
    from fastapi.responses import RedirectResponse
    # Check for React frontend first
    frontend_react_index = Path(__file__).parent.parent / "frontend-react" / "dist" / "index.html"
    frontend_index = frontend_path / "index.html"
    if frontend_react_index.exists() or frontend_index.exists():
        return RedirectResponse(url="/app")
    return {
        "name": "NPIDB Home Health Scraper",
        "version": "1.0.0",
        "endpoints": {
            "single": "/scrape/home-health?state=NC&location=Raleigh&method=curl_cffi",
            "batch": "/scrape/home-health/batch",
            "frontend": "/app",
        },
        "default_method": "curl_cffi",
    }


@app.get("/scrape/home-health", response_model=List[HomeHealthAgency])
async def scrape_home_health(
    state: str = Query(
        ..., min_length=2, max_length=2, description="2-letter state code, e.g., NC"
    ),
    location: str = Query(
        ..., description="City or county to search, e.g., Raleigh or Henrico"
    ),
    method: str = Query(
        "curl_cffi", description="Scraping method: curl_cffi (default, recommended), playwright, or selenium"
    ),
    save: bool = Query(
        False, description="Save results to Supabase database"
    ),
):
    """
    Scrape NPIDB for home health agencies for the given state and location.
    
    Args:
        state: 2-letter state code (e.g., "NC", "VA", "OH")
        location: City or county name (e.g., "Raleigh", "Henrico County")
        method: Scraping method - "playwright" (default), "curl_cffi", or "selenium"
    
    Returns:
        List of HomeHealthAgency objects with scraped data
    
    Example:
        GET /scrape/home-health?state=NC&location=Raleigh&method=curl_cffi
    """
    try:
        logger.info(f"Scraping request: state={state}, location={location}, method={method}")
        
        if method == "curl_cffi":
            if not CURL_CFFI_AVAILABLE:
                raise HTTPException(
                    status_code=400,
                    detail="curl_cffi not available. Install with: pip install curl-cffi beautifulsoup4"
                )
            agencies = await scrape_home_health_agencies_curl_cffi(state=state, location=location)
        elif method == "playwright":
            agencies = await scrape_home_health_agencies(state=state, location=location)
        elif method == "selenium":
            if not SELENIUM_AVAILABLE:
                raise HTTPException(
                    status_code=400,
                    detail="Selenium not available. Install with: pip install undetected-chromedriver selenium"
                )
            agencies = await scrape_home_health_agencies_selenium(state=state, location=location)
        else:
            # Default to curl_cffi if invalid method specified
            logger.warning(f"Invalid method '{method}', defaulting to curl_cffi")
            if not CURL_CFFI_AVAILABLE:
                raise HTTPException(
                    status_code=400,
                    detail="curl_cffi not available. Install with: pip install curl-cffi beautifulsoup4"
                )
            agencies = await scrape_home_health_agencies_curl_cffi(state=state, location=location)
        
        logger.info(f"Successfully scraped {len(agencies)} agencies using {method}")
        
        # Save to Supabase if requested and storage is available
        if save:
            if storage:
                try:
                    save_stats = await storage.save_agencies(agencies)
                    logger.info(f"Saved to Supabase: {save_stats}")
                    # Log the scrape
                    storage.log_scrape(
                        state=state,
                        location=location,
                        agencies_found=len(agencies),
                        scrape_method=method,
                    )
                except Exception as e:
                    logger.error(f"Failed to save to Supabase: {e}", exc_info=True)
            else:
                logger.warning("Supabase storage not configured. Set SUPABASE_URL and SUPABASE_KEY environment variables.")
        
        return agencies
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scrape failed for {state}/{location} with {method}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Scrape failed: {str(e)}"
        )


@app.get("/scrape/home-health/batch", response_model=List[BatchScrapeResult])
async def scrape_home_health_batch(
    save: bool = Query(
        False, description="Save results to Supabase database"
    ),
):
    """
    Batch scrape all state/county pairs from counties.csv.
    
    Reads counties.csv from the project root and processes each state/county pair.
    Returns a list of BatchScrapeResult objects, one for each state/county combination.
    
    Args:
        save: If True, save all scraped agencies to Supabase
    
    Example:
        GET /scrape/home-health/batch?save=true
    """
    csv_path = Path(__file__).parent.parent / "counties.csv"
    
    if not csv_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"counties.csv not found at {csv_path}",
        )
    
    results = []
    
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row_num, row in enumerate(reader, start=1):
                if not row or len(row) < 2:
                    continue
                
                state = row[0].strip()
                location = row[1].strip()
                
                if not state or not location:
                    continue
                
                logger.info(f"Processing batch item {row_num}: {state}/{location}")
                
                try:
                    # Use curl_cffi for batch processing (more reliable)
                    if CURL_CFFI_AVAILABLE:
                        agencies = await scrape_home_health_agencies_curl_cffi(
                            state=state, location=location
                        )
                    else:
                        agencies = await scrape_home_health_agencies(
                            state=state, location=location
                        )
                    # Save to Supabase if requested
                    if save and storage:
                        try:
                            save_stats = await storage.save_agencies(agencies)
                            logger.info(
                                f"Saved {state}/{location} to Supabase: {save_stats}"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to save {state}/{location} to Supabase: {e}"
                            )
                    
                    results.append(
                        BatchScrapeResult(
                            state=state,
                            location=location,
                            agencies=agencies,
                            error=None,
                        )
                    )
                    logger.info(
                        f"Successfully processed {state}/{location}: {len(agencies)} agencies"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to process {state}/{location}: {e}", exc_info=True
                    )
                    results.append(
                        BatchScrapeResult(
                            state=state,
                            location=location,
                            agencies=[],
                            error=str(e),
                        )
                    )
        
        logger.info(f"Batch processing complete: {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Batch scrape failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Batch scrape failed: {str(e)}"
        )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Counties CRUD endpoints
@app.get("/counties")
async def get_counties():
    """Get all counties from counties.csv."""
    csv_path = Path(__file__).parent.parent / "counties.csv"
    
    if not csv_path.exists():
        return {"counties": []}
    
    counties = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row_num, row in enumerate(reader, start=1):
                if not row or len(row) < 2:
                    continue
                state = row[0].strip()
                location = row[1].strip()
                if state and location:
                    counties.append({
                        "id": row_num - 1,  # 0-based index
                        "state": state,
                        "location": location,
                    })
    except Exception as e:
        logger.error(f"Failed to read counties.csv: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to read counties: {str(e)}")
    
    return {"counties": counties}


@app.post("/counties")
async def add_county(
    state: str = Query(..., min_length=2, max_length=2, description="2-letter state code"),
    location: str = Query(..., description="City or county name"),
):
    """Add a new county to counties.csv."""
    csv_path = Path(__file__).parent.parent / "counties.csv"
    
    try:
        # Read existing counties
        existing = []
        if csv_path.exists():
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                existing = [row for row in reader if row and len(row) >= 2]
        
        # Check for duplicates
        state_upper = state.upper().strip()
        location_clean = location.strip()
        
        for row in existing:
            if len(row) >= 2 and row[0].strip().upper() == state_upper and row[1].strip() == location_clean:
                raise HTTPException(status_code=400, detail="County already exists")
        
        # Append new county
        existing.append([state_upper, location_clean])
        
        # Write back to file
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(existing)
        
        logger.info(f"Added county: {state_upper}/{location_clean}")
        return {
            "message": "County added successfully",
            "county": {"state": state_upper, "location": location_clean}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add county: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to add county: {str(e)}")


@app.put("/counties/{county_id}")
async def update_county(
    county_id: int,
    state: str = Query(..., min_length=2, max_length=2, description="2-letter state code"),
    location: str = Query(..., description="City or county name"),
):
    """Update a county in counties.csv."""
    csv_path = Path(__file__).parent.parent / "counties.csv"
    
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="counties.csv not found")
    
    try:
        # Read existing counties
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            counties = [row for row in reader if row and len(row) >= 2]
        
        if county_id < 0 or county_id >= len(counties):
            raise HTTPException(status_code=404, detail=f"County with ID {county_id} not found")
        
        # Update the county
        state_upper = state.upper().strip()
        location_clean = location.strip()
        counties[county_id] = [state_upper, location_clean]
        
        # Write back to file
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(counties)
        
        logger.info(f"Updated county {county_id}: {state_upper}/{location_clean}")
        return {
            "message": "County updated successfully",
            "county": {"id": county_id, "state": state_upper, "location": location_clean}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update county: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update county: {str(e)}")


@app.delete("/counties/{county_id}")
async def delete_county(county_id: int):
    """Delete a county from counties.csv."""
    csv_path = Path(__file__).parent.parent / "counties.csv"
    
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="counties.csv not found")
    
    try:
        # Read existing counties
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            counties = [row for row in reader if row and len(row) >= 2]
        
        if county_id < 0 or county_id >= len(counties):
            raise HTTPException(status_code=404, detail=f"County with ID {county_id} not found")
        
        # Remove the county
        deleted = counties.pop(county_id)
        
        # Write back to file
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(counties)
        
        logger.info(f"Deleted county {county_id}: {deleted[0]}/{deleted[1]}")
        return {
            "message": "County deleted successfully",
            "deleted": {"id": county_id, "state": deleted[0], "location": deleted[1]}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete county: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete county: {str(e)}")


# Storage endpoints (only available if Supabase is configured)
if storage:
    @app.post("/agencies/save")
    async def save_agencies(agencies: List[HomeHealthAgency]):
        """
        Save a list of agencies to Supabase.
        
        This endpoint allows you to save agencies that were scraped separately.
        Agencies with existing NPIs will be updated, new ones will be inserted.
        """
        try:
            stats = await storage.save_agencies(agencies)
            return {
                "message": "Agencies saved successfully",
                "stats": stats
            }
        except Exception as e:
            logger.error(f"Failed to save agencies: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to save: {str(e)}")
    
    @app.get("/agencies/stats")
    async def get_agencies_stats():
        """Get statistics about stored agencies."""
        try:
            # Get total count using count parameter
            total_result = storage.supabase.table("agencies").select("*", count="exact").limit(0).execute()
            total_count = total_result.count if hasattr(total_result, 'count') else 0
            
            # Get count by state
            state_result = storage.supabase.table("agencies").select("source_state").execute()
            states = {}
            if state_result.data:
                for agency in state_result.data:
                    state = agency.get("source_state")
                    if state:
                        states[state] = states.get(state, 0) + 1
            
            return {
                "total_agencies": total_count,
                "by_state": states,
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Stats query failed: {str(e)}")
    
    @app.get("/agencies")
    async def get_agencies(
        state: Optional[str] = Query(None, description="Filter by state code"),
        location: Optional[str] = Query(None, description="Filter by location"),
        npi: Optional[str] = Query(None, description="Filter by NPI"),
        limit: int = Query(100, ge=1, le=10000, description="Maximum number of results"),
        offset: int = Query(0, ge=0, description="Offset for pagination"),
    ):
        """
        Query agencies from Supabase database.
        
        Returns agencies with their addresses and authorized officials.
        """
        try:
            agencies = storage.get_agencies(
                state=state,
                location=location,
                npi=npi,
                limit=limit,
                offset=offset,
            )
            return {
                "count": len(agencies),
                "agencies": agencies
            }
        except Exception as e:
            logger.error(f"Failed to query agencies: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
    
    @app.get("/agencies/{npi}")
    async def get_agency_by_npi(npi: str):
        """Get a single agency by NPI number."""
        try:
            agency = storage.get_agency_by_npi(npi)
            if not agency:
                raise HTTPException(status_code=404, detail=f"Agency with NPI {npi} not found")
            return agency
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get agency: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
    
    @app.put("/agencies/{agency_id}")
    async def update_agency(agency_id: str, updates: dict = Body(...)):
        """Update an agency by ID."""
        try:
            # First check if agency exists
            agency = storage.get_agency_by_id(agency_id)
            if not agency:
                raise HTTPException(status_code=404, detail=f"Agency with ID {agency_id} not found")
            
            # Only allow updating specific fields
            allowed_fields = ["provider_name", "agency_name", "phone", "npi"]
            filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
            
            if not filtered_updates:
                raise HTTPException(status_code=400, detail="No valid fields to update")
            
            # Update the agency
            updated = storage.update_agency(agency_id, filtered_updates)
            return updated
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update agency: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
    
    @app.delete("/agencies/{agency_id}")
    async def delete_agency(agency_id: str):
        """Delete an agency by ID."""
        try:
            # First check if agency exists
            agency = storage.get_agency_by_id(agency_id)
            if not agency:
                raise HTTPException(status_code=404, detail=f"Agency with ID {agency_id} not found")
            
            # Delete the agency (cascade will delete related records)
            storage.delete_agency(agency_id)
            return {"message": "Agency deleted successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete agency: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
    
    # List management endpoints
    @app.post("/lists")
    async def create_list(request: CreateListRequest):
        """Create a new list."""
        try:
            list_obj = storage.create_list(name=request.name, description=request.description)
            return list_obj
        except Exception as e:
            logger.error(f"Failed to create list: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to create list: {str(e)}")
    
    @app.get("/lists")
    async def get_lists():
        """Get all lists."""
        try:
            lists = storage.get_lists()
            return {"lists": lists}
        except Exception as e:
            logger.error(f"Failed to get lists: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get lists: {str(e)}")
    
    @app.get("/lists/{list_id}")
    async def get_list(list_id: str):
        """Get a single list by ID."""
        try:
            list_obj = storage.get_list(list_id)
            if not list_obj:
                raise HTTPException(status_code=404, detail=f"List {list_id} not found")
            return list_obj
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get list: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get list: {str(e)}")
    
    @app.delete("/lists/{list_id}")
    async def delete_list(list_id: str):
        """Delete a list."""
        try:
            storage.delete_list(list_id)
            return {"message": "List deleted successfully"}
        except Exception as e:
            logger.error(f"Failed to delete list: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to delete list: {str(e)}")
    
    @app.post("/lists/{list_id}/agencies/{agency_id}")
    async def add_agency_to_list(list_id: str, agency_id: str):
        """Add an agency to a list."""
        try:
            result = storage.add_agency_to_list(list_id=list_id, agency_id=agency_id)
            return result
        except Exception as e:
            logger.error(f"Failed to add agency to list: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to add agency: {str(e)}")
    
    @app.delete("/lists/{list_id}/agencies/{agency_id}")
    async def remove_agency_from_list(list_id: str, agency_id: str):
        """Remove an agency from a list."""
        try:
            storage.remove_agency_from_list(list_id=list_id, agency_id=agency_id)
            return {"message": "Agency removed from list successfully"}
        except Exception as e:
            logger.error(f"Failed to remove agency from list: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to remove agency: {str(e)}")
    
    @app.get("/lists/{list_id}/agencies")
    async def get_list_agencies(list_id: str):
        """Get all agencies in a list."""
        try:
            agencies = storage.get_list_agencies(list_id)
            return {"count": len(agencies), "agencies": agencies}
        except Exception as e:
            logger.error(f"Failed to get list agencies: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get list agencies: {str(e)}")
    
    # Download endpoints
    @app.get("/lists/{list_id}/download/csv")
    async def download_list_csv(list_id: str):
        """Download a list as CSV."""
        try:
            agencies = storage.get_list_agencies(list_id)
            
            def generate_csv():
                if not agencies:
                    yield "No agencies in list\n"
                    return
                
                # CSV header
                yield "NPI,Provider Name,Agency Name,Street,City,State,Zip,Phone,Enumeration Date,Official Name,Official Title,Official Phone,Source State,Source Location,Detail URL\n"
                
                # CSV rows
                for agency in agencies:
                    address = agency.get("agency_addresses", [{}])[0] if agency.get("agency_addresses") else {}
                    official = agency.get("agency_officials", [{}])[0] if agency.get("agency_officials") else {}
                    
                    # Escape commas and quotes in CSV
                    def escape_csv(s):
                        if s is None:
                            return ""
                        s = str(s)
                        if "," in s or '"' in s or "\n" in s:
                            return '"' + s.replace('"', '""') + '"'
                        return s
                    
                    row = [
                        escape_csv(agency.get("npi")),
                        escape_csv(agency.get("provider_name")),
                        escape_csv(agency.get("agency_name")),
                        escape_csv(address.get("street")),
                        escape_csv(address.get("city")),
                        escape_csv(address.get("state")),
                        escape_csv(address.get("zip")),
                        escape_csv(agency.get("phone")),
                        escape_csv(agency.get("enumeration_date")),
                        escape_csv(official.get("name")),
                        escape_csv(official.get("title")),
                        escape_csv(official.get("telephone")),
                        escape_csv(agency.get("source_state")),
                        escape_csv(agency.get("source_location")),
                        escape_csv(agency.get("detail_url")),
                    ]
                    yield ",".join(row) + "\n"
            
            list_obj = storage.get_list(list_id)
            list_name = list_obj.get("name", "list") if list_obj else "list"
            filename = f"{list_name.replace(' ', '_')}.csv"
            
            return StreamingResponse(
                generate_csv(),
                media_type="text/csv",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'}
            )
        except Exception as e:
            logger.error(f"Failed to download list CSV: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to download CSV: {str(e)}")
    
    @app.get("/lists/{list_id}/download/json")
    async def download_list_json(list_id: str):
        """Download a list as JSON."""
        try:
            agencies = storage.get_list_agencies(list_id)
            list_obj = storage.get_list(list_id)
            list_name = list_obj.get("name", "list") if list_obj else "list"
            filename = f"{list_name.replace(' ', '_')}.json"
            
            return JSONResponse(
                content={"list": list_obj, "agencies": agencies},
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
                media_type="application/json"
            )
        except Exception as e:
            logger.error(f"Failed to download list JSON: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to download JSON: {str(e)}")
else:
    logger.info("Supabase storage not configured. Storage endpoints will not be available.")

