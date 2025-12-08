"""Alternative scraper using Selenium with undetected-chromedriver."""

import asyncio
import logging
import urllib.parse
import re
from typing import List, Optional

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

from .config import BASE_URL
from .models import HomeHealthAgency, Address, AuthorizedOfficial

logger = logging.getLogger(__name__)


async def scrape_home_health_agencies_selenium(
    state: str, location: str
) -> List[HomeHealthAgency]:
    """
    Scrape using Selenium with undetected-chromedriver.
    
    Args:
        state: 2-letter state code (e.g., "NC", "VA")
        location: City or county name (e.g., "Raleigh", "Henrico County")
    
    Returns:
        List of HomeHealthAgency objects with scraped data
    """
    if not SELENIUM_AVAILABLE:
        raise ImportError("undetected-chromedriver and selenium are required. Install with: pip install undetected-chromedriver selenium")
    
    # Normalize inputs
    state_lower = state.strip().lower()
    location_encoded = urllib.parse.quote_plus(location.strip())
    
    # Build URL
    url = f"{BASE_URL}/{state_lower}/?location={location_encoded}"
    logger.info(f"Scraping URL with Selenium: {url}")
    
    agencies = []
    driver = None
    
    try:
        # Create undetected Chrome driver
        options = uc.ChromeOptions()
        options.add_argument('--headless=new')  # Use new headless mode
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        driver = uc.Chrome(options=options, version_main=None)
        driver.set_page_load_timeout(30)
        
        # Navigate to page
        logger.info("Loading results page...")
        driver.get(url)
        
        # Wait for Cloudflare to pass
        wait = WebDriverWait(driver, 20)
        try:
            # Wait for page title to change from "Just a moment"
            wait.until(lambda d: "Just a moment" not in d.title)
            logger.info("Cloudflare check passed")
        except TimeoutException:
            logger.warning("Cloudflare check timeout, proceeding anyway")
        
        # Wait for table or results
        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        except TimeoutException:
            logger.warning("Table not found, trying to find links")
        
        # Find agency links
        links = driver.find_elements(By.CSS_SELECTOR, 'a[href*=".aspx"], a[href*="home-health_251e00000x"]')
        logger.info(f"Found {len(links)} agency links")
        
        # Extract detail URLs
        detail_urls = []
        for link in links:
            href = link.get_attribute('href')
            if href and ('.aspx' in href or 'home-health_251e00000x' in href):
                agency_name = link.text.strip() or link.get_attribute('title') or 'Unknown'
                detail_urls.append({
                    'url': href,
                    'name': agency_name
                })
        
        # Scrape each detail page
        for detail_info in detail_urls[:10]:  # Limit for testing
            try:
                logger.debug(f"Scraping: {detail_info['url']}")
                driver.get(detail_info['url'])
                
                # Wait for content
                wait.until(lambda d: "Just a moment" not in d.title)
                await asyncio.sleep(1)
                
                # Parse page
                agency = _parse_detail_page_selenium(driver, detail_info, state, location)
                if agency:
                    agencies.append(agency)
                
            except Exception as e:
                logger.warning(f"Failed to scrape {detail_info['url']}: {e}")
                continue
        
        logger.info(f"Successfully scraped {len(agencies)} agencies")
        return agencies
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        raise
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def _parse_detail_page_selenium(driver, detail_info: dict, state: str, location: str) -> Optional[HomeHealthAgency]:
    """Parse detail page using Selenium."""
    try:
        text = driver.find_element(By.TAG_NAME, "body").text
        
        # Extract NPI
        npi = None
        npi_match = re.search(r"NPI\s*#?\s*:?\s*(\d{10})", text, re.IGNORECASE)
        if npi_match:
            npi = npi_match.group(1)
        
        # Extract provider name from title
        provider_name = driver.title
        provider_name = re.sub(r'NPI\s*#?\s*\d+', '', provider_name, flags=re.IGNORECASE).strip()
        if provider_name:
            provider_name = provider_name.split(';')[0].strip()
        
        # Extract other fields (similar to curl_cffi version)
        # ... (implementation similar to _parse_detail_page)
        
        return HomeHealthAgency(
            npi=npi,
            provider_name=provider_name or detail_info.get('name'),
            agency_name=detail_info.get('name'),
            address=Address(),
            phone=None,
            enumeration_date=None,
            authorized_official=AuthorizedOfficial(),
            detail_url=detail_info['url'],
            source_state=state,
            source_location=location,
        )
    except Exception as e:
        logger.warning(f"Error parsing detail page: {e}")
        return None

