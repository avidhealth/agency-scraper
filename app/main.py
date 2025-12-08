"""FastAPI application for NPIDB home health agency scraper."""

import logging
import csv
from typing import List
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException

from .models import HomeHealthAgency, BatchScrapeResult
from .scraper import scrape_home_health_agencies

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="NPIDB Home Health Scraper",
    description="Scrape home health agency data from NPIDB (npidb.org)",
    version="1.0.0",
)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "NPIDB Home Health Scraper",
        "version": "1.0.0",
        "endpoints": {
            "single": "/scrape/home-health?state=NC&location=Raleigh",
            "batch": "/scrape/home-health/batch",
        },
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
        "playwright", description="Scraping method: playwright, curl_cffi, or selenium"
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
        elif method == "selenium":
            if not SELENIUM_AVAILABLE:
                raise HTTPException(
                    status_code=400,
                    detail="Selenium not available. Install with: pip install undetected-chromedriver selenium"
                )
            agencies = await scrape_home_health_agencies_selenium(state=state, location=location)
        else:  # default to playwright
            agencies = await scrape_home_health_agencies(state=state, location=location)
        
        logger.info(f"Successfully scraped {len(agencies)} agencies using {method}")
        return agencies
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scrape failed for {state}/{location} with {method}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Scrape failed: {str(e)}"
        )


@app.get("/scrape/home-health/batch", response_model=List[BatchScrapeResult])
async def scrape_home_health_batch():
    """
    Batch scrape all state/county pairs from counties.csv.
    
    Reads counties.csv from the project root and processes each state/county pair.
    Returns a list of BatchScrapeResult objects, one for each state/county combination.
    
    Example:
        GET /scrape/home-health/batch
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
                    agencies = await scrape_home_health_agencies(
                        state=state, location=location
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

