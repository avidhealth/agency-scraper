"""Playwright-based scraper for NPIDB home health agencies."""

import asyncio
import logging
import urllib.parse
import random
from typing import List, Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from .config import (
    BASE_URL,
    PLAYWRIGHT_SETTINGS,
    PAGE_LOAD_TIMEOUT,
    SELECTOR_TIMEOUT,
)
from .models import HomeHealthAgency, Address, AuthorizedOfficial

logger = logging.getLogger(__name__)

# Try to import playwright-stealth, fall back if not available
try:
    from playwright_stealth import stealth_async
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False
    logger.warning("playwright-stealth not available, using basic anti-detection measures")


async def scrape_home_health_agencies(
    state: str, location: str
) -> List[HomeHealthAgency]:
    """
    Scrape home health agencies from NPIDB for the given state and location.
    
    Args:
        state: 2-letter state code (e.g., "NC", "VA")
        location: City or county name (e.g., "Raleigh", "Henrico County")
    
    Returns:
        List of HomeHealthAgency objects with scraped data
    
    Raises:
        Exception: If scraping fails after retries
    """
    # Normalize inputs
    state_lower = state.strip().lower()
    location_encoded = urllib.parse.quote_plus(location.strip())
    
    # Build URL
    url = f"{BASE_URL}/{state_lower}/?location={location_encoded}"
    logger.info(f"Scraping URL: {url}")
    
    # Launch Playwright using async context manager
    async with async_playwright() as playwright:
        browser = None
        context = None
        page = None
        
        try:
            # Launch browser with additional args to reduce detection
            launch_args = {
                **PLAYWRIGHT_SETTINGS,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-site-isolation-trials",
                ],
            }
            browser = await playwright.chromium.launch(**launch_args)
            
            # Create context with realistic browser fingerprint
            # Use a recent Chrome user agent
            user_agents = [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ]
            
            context = await browser.new_context(
                user_agent=random.choice(user_agents),
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/New_York",
                permissions=["geolocation"],
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Cache-Control": "max-age=0",
                },
                # Add realistic screen and color depth
                screen={"width": 1920, "height": 1080},
                color_scheme="light",
            )
            
            # Apply stealth mode if available
            page = await context.new_page()
            if STEALTH_AVAILABLE:
                await stealth_async(page)
                logger.debug("Applied playwright-stealth")
            
            # Enhanced anti-detection: override webdriver and other automation indicators
            await page.add_init_script("""
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Override plugins to look realistic
                Object.defineProperty(navigator, 'plugins', {
                    get: () => {
                        return [
                            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
                            { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' }
                        ];
                    }
                });
                
                // Override languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                // Add Chrome runtime
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
                
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Override getBattery if it exists
                if (navigator.getBattery) {
                    const originalGetBattery = navigator.getBattery;
                    navigator.getBattery = function() {
                        return originalGetBattery.apply(navigator, arguments).then(battery => {
                            Object.defineProperty(battery, 'charging', { get: () => true });
                            Object.defineProperty(battery, 'chargingTime', { get: () => 0 });
                            Object.defineProperty(battery, 'dischargingTime', { get: () => Infinity });
                            Object.defineProperty(battery, 'level', { get: () => 1 });
                            return battery;
                        });
                    };
                }
                
                // Override canvas fingerprinting
                const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function() {
                    return originalToDataURL.apply(this, arguments);
                };
                
                // Override WebGL fingerprinting
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter.apply(this, arguments);
                };
            """)
            
            page.set_default_timeout(PAGE_LOAD_TIMEOUT)
            
            # Add random delay to simulate human behavior
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Load results page with retry
            agencies = []
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        logger.info(f"Retry attempt {attempt + 1}/{max_retries}")
                        # Close old page and create new one
                        try:
                            await page.close()
                        except Exception:
                            pass
                        page = await context.new_page()
                        if STEALTH_AVAILABLE:
                            await stealth_async(page)
                        # Re-apply init script
                        await page.add_init_script("""
                            Object.defineProperty(navigator, 'webdriver', {
                                get: () => undefined
                            });
                        """)
                        page.set_default_timeout(PAGE_LOAD_TIMEOUT)
                    
                    logger.info(f"Loading results page (attempt {attempt + 1})...")
                    await _load_results_page(page, url)
                    logger.info("Results page loaded, extracting agencies...")
                    agencies = await _extract_all_agencies(
                        page, state, location, url
                    )
                    # If we got here without exception, break out of retry loop
                    break
                except Exception as e:
                    error_msg = str(e)
                    logger.warning(f"Attempt {attempt + 1} failed: {error_msg}")
                    if "Target page, context or browser has been closed" in error_msg:
                        if attempt < max_retries - 1:
                            # Wait a bit longer before retry
                            await asyncio.sleep(random.uniform(2.0, 4.0))
                            continue
                    # If it's the last attempt or a different error, raise
                    if attempt == max_retries - 1:
                        raise
            
            logger.info(f"Found {len(agencies)} agencies for {state}/{location}")
            return agencies
            
        except Exception as e:
            logger.error(f"Scraping failed for {state}/{location}: {e}")
            raise
        finally:
            # Clean up
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass


async def _load_results_page(page: Page, url: str) -> None:
    """Load the results page and wait for content to appear."""
    # Add human-like delay before navigation
    await asyncio.sleep(random.uniform(0.5, 1.5))
    
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    
    # Simulate human-like mouse movement
    try:
        await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
        await asyncio.sleep(random.uniform(0.1, 0.3))
    except Exception:
        pass
    
    # Check title quickly - if it's not "Just a moment", we're good
    title = await page.title()
    if "Just a moment" in title:
        # Wait for Cloudflare with random delays to appear more human
        for i in range(10):  # Max 10 seconds
            await asyncio.sleep(random.uniform(0.5, 1.0))
            try:
                title = await page.title()
                if "Just a moment" not in title:
                    logger.debug(f"Cloudflare check passed after {i+1} attempts")
                    break
            except Exception:
                # Page might be closed, proceed anyway
                break
    else:
        logger.debug(f"Page loaded with title: {title}")
    
    # Human-like delay before interacting with page
    await asyncio.sleep(random.uniform(1.0, 2.0))
    
    # Wait for results container - try multiple common selectors quickly
    # These selectors may need adjustment based on actual NPIDB HTML structure
    selectors_to_try = [
        "table",  # Common table selector
        "tbody tr",  # Table body rows
        ".results",  # Common results class
        "#results",  # Common results ID
        "[class*='result']",  # Any element with "result" in class
        "[class*='agency']",  # Any element with "agency" in class
    ]
    
    for selector in selectors_to_try:
        try:
            # Use shorter timeout to fail fast
            await page.wait_for_selector(selector, timeout=3000)
            logger.debug(f"Found results using selector: {selector}")
            return
        except Exception:
            continue
    
    # If no selector worked, proceed anyway - content might be there
    logger.warning("Could not find results container with standard selectors, proceeding anyway")


async def _extract_all_agencies(
    page: Page, state: str, location: str, base_url: str
) -> List[HomeHealthAgency]:
    """
    Extract all agencies from all pages of results.
    
    Handles pagination by detecting and clicking "next" links.
    """
    all_agencies = []
    page_num = 1
    
    while True:
        try:
            logger.info(f"Extracting agencies from page {page_num}")
            
            # Check if page is still valid
            if page.is_closed():
                logger.warning("Page was closed, stopping extraction")
                break
            
            # Extract agencies from current page
            agencies = await _extract_agencies_from_page(page, state, location, base_url)
            all_agencies.extend(agencies)
        except Exception as e:
            error_msg = str(e)
            if "Target page, context or browser has been closed" in error_msg or "Target closed" in error_msg:
                logger.warning(f"Page/context closed during extraction: {error_msg}")
                break
            else:
                logger.warning(f"Error extracting from page {page_num}: {error_msg}")
                # Continue to next page or break
                break
        
        # Check for pagination - try to find "next" button/link
        # Common patterns: "Next", ">", "Next Page", page numbers
        next_selectors = [
            'a:has-text("Next")',
            'a:has-text(">")',
            'a:has-text("Next Page")',
            'a[aria-label*="next" i]',
            'button:has-text("Next")',
            # Look for page number links that are greater than current
            f'a:has-text("{page_num + 1}")',
        ]
        
        next_found = False
        for selector in next_selectors:
            try:
                next_link = await page.query_selector(selector)
                if next_link:
                    # Check if it's actually clickable (not disabled)
                    is_disabled = await next_link.get_attribute("disabled")
                    is_aria_disabled = await next_link.get_attribute("aria-disabled")
                    if not is_disabled and is_aria_disabled != "true":
                        # Human-like delay before clicking
                        await asyncio.sleep(random.uniform(0.5, 1.0))
                        await next_link.click()
                        # Wait for navigation with human-like timing
                        await asyncio.sleep(random.uniform(1.0, 2.0))
                        try:
                            await page.wait_for_load_state("domcontentloaded", timeout=10000)
                        except Exception:
                            pass
                        next_found = True
                        page_num += 1
                        break
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        if not next_found:
            logger.info(f"No more pages found, stopping at page {page_num}")
            break
        
        # Safety limit to prevent infinite loops
        if page_num > 100:
            logger.warning("Reached page limit (100), stopping pagination")
            break
    
    return all_agencies


async def _extract_agencies_from_page(
    page: Page, state: str, location: str, base_url: str
) -> List[HomeHealthAgency]:
    """
    Extract agency information from the current results page.
    
    Returns list of agency data with detail page URLs.
    """
    agencies = []
    
    # Try multiple selectors to find agency rows
    # These may need adjustment based on actual NPIDB structure
    row_selectors = [
        "table tbody tr",  # Standard table rows
        "table tr",  # All table rows (may include header)
        "tbody tr",  # Just tbody rows
        "[class*='agency']",  # Elements with "agency" in class
        "[class*='result']",  # Elements with "result" in class
        ".agency-row",  # Common class name
        ".result-row",  # Common class name
        "tr",  # Any table row
    ]
    
    rows = []
    for selector in row_selectors:
        try:
            found_rows = await page.query_selector_all(selector)
            if len(found_rows) > 0:
                logger.debug(f"Found {len(found_rows)} elements using selector: {selector}")
                # Filter out header row if present
                if selector.startswith("table") or selector == "tbody tr" or selector == "tr":
                    # Skip first row if it looks like a header
                    if len(found_rows) > 1:
                        try:
                            first_row_text = await found_rows[0].inner_text()
                            if any(header in first_row_text.lower() for header in ["name", "npi", "address", "provider"]):
                                rows = found_rows[1:]
                                logger.debug(f"Filtered out header row, {len(rows)} data rows remaining")
                            else:
                                rows = found_rows
                        except Exception:
                            rows = found_rows
                    else:
                        rows = found_rows
                else:
                    rows = found_rows
                
                if len(rows) > 0:
                    logger.debug(f"Using {len(rows)} rows from selector: {selector}")
                    break
        except Exception as e:
            logger.debug(f"Selector {selector} failed: {e}")
            continue
    
    # If still no rows, try finding any links to detail pages as a fallback
    if not rows:
        logger.debug("No rows found with standard selectors, trying to find detail page links")
        detail_links = await page.query_selector_all('a[href*="home-health_251e00000x"][href*=".aspx"]')
        if len(detail_links) > 0:
            logger.info(f"Found {len(detail_links)} detail page links, will extract from links")
            # Create pseudo-rows from links
            rows = detail_links
    
    if not rows:
        logger.warning("No agency rows found on page")
        # Debug: log page title and a snippet of HTML
        try:
            title = await page.title()
            logger.debug(f"Page title: {title}")
            html_snippet = await page.content()
            logger.debug(f"HTML length: {len(html_snippet)} chars")
            # Look for any links with aspx
            all_links = await page.query_selector_all('a[href*="aspx"]')
            logger.debug(f"Found {len(all_links)} links with .aspx")
            if len(all_links) > 0:
                href = await all_links[0].get_attribute('href')
                logger.debug(f"First .aspx link: {href}")
        except Exception as e:
            logger.debug(f"Could not get debug info: {e}")
        return agencies
    
    # Extract data from each row (or link if rows weren't found)
    for row in rows:
        try:
            # If rows are actually links, handle differently
            tag_name = await row.evaluate("el => el.tagName.toLowerCase()")
            if tag_name == "a":
                # Extract from link directly
                agency_data = await _extract_agency_from_link(row, base_url)
            else:
                agency_data = await _extract_agency_from_row(row, base_url)
            if agency_data:
                # Visit detail page to get full information
                detail_url = agency_data.get("detail_url")
                if detail_url:
                    # Open detail page in a new page/tab to avoid losing results page state
                    detail_page = None
                    try:
                        detail_page = await page.context.new_page()
                        detail_page.set_default_timeout(PAGE_LOAD_TIMEOUT)
                        full_agency = await _scrape_detail_page(
                            detail_page, detail_url, agency_data, state, location
                        )
                        if full_agency:
                            agencies.append(full_agency)
                    except Exception as e:
                        logger.warning(f"Failed to open detail page {detail_url}: {e}")
                        # Return partial data if detail page fails
                        agencies.append(HomeHealthAgency(
                            npi=None,
                            provider_name=agency_data.get("agency_name"),
                            agency_name=agency_data.get("agency_name"),
                            address=Address(
                                city=agency_data.get("city"),
                                state=agency_data.get("state"),
                                zip=agency_data.get("zip"),
                            ),
                            phone=agency_data.get("phone"),
                            enumeration_date=None,
                            authorized_official=AuthorizedOfficial(),
                            detail_url=detail_url,
                            source_state=state,
                            source_location=location,
                        ))
                    finally:
                        if detail_page:
                            try:
                                await detail_page.close()
                            except Exception:
                                pass
        except Exception as e:
            logger.warning(f"Failed to extract agency from row: {e}")
            continue
    
    return agencies


async def _extract_agency_from_link(link, base_url: str) -> Optional[dict]:
    """
    Extract agency information directly from a detail page link.
    
    Returns dict with agency_name and detail_url.
    """
    try:
        href = await link.get_attribute("href")
        if not href:
            return None
        
        # Build full URL
        if href.startswith("/"):
            detail_url = f"https://npidb.org{href}"
        elif href.startswith("http"):
            detail_url = href
        else:
            detail_url = f"{base_url}/{href}"
        
        # Get agency name from link text
        agency_name = await link.inner_text()
        agency_name = agency_name.strip() if agency_name else None
        
        if not agency_name:
            # Try to get from title or other attributes
            agency_name = await link.get_attribute("title")
            agency_name = agency_name.strip() if agency_name else "Unknown Agency"
        
        return {
            "agency_name": agency_name,
            "city": None,
            "state": None,
            "zip": None,
            "phone": None,
            "detail_url": detail_url,
        }
    except Exception as e:
        logger.warning(f"Error extracting agency from link: {e}")
        return None


async def _extract_agency_from_row(row, base_url: str) -> Optional[dict]:
    """
    Extract basic agency information from a results table row.
    
    Returns dict with agency_name, city, state, zip, phone (if available), and detail_url.
    """
    try:
        # Find the link to detail page - look for links with .aspx or containing NPI
        links = await row.query_selector_all("a")
        detail_url = None
        
        for link in links:
            href = await link.get_attribute("href")
            if href:
                # Check if it's a detail page link
                if ".aspx" in href or "home-health_251e00000x" in href:
                    if href.startswith("/"):
                        detail_url = f"https://npidb.org{href}"
                    elif href.startswith("http"):
                        detail_url = href
                    else:
                        detail_url = f"{base_url}/{href}"
                    break
        
        # Extract text content
        row_text = await row.inner_text()
        cells = await row.query_selector_all("td")
        
        # Try to extract structured data from cells
        agency_name = None
        city = None
        state = None
        zip_code = None
        phone = None
        
        if len(cells) > 0:
            # First cell often contains name
            agency_name = await cells[0].inner_text()
            agency_name = agency_name.strip() if agency_name else None
            
            # Look for address/phone in remaining cells
            for cell in cells[1:]:
                cell_text = await cell.inner_text()
                cell_text = cell_text.strip() if cell_text else ""
                
                # Check for phone pattern
                if not phone and any(char.isdigit() for char in cell_text) and len(cell_text.replace("-", "").replace("(", "").replace(")", "").replace(" ", "")) >= 10:
                    phone = cell_text
                
                # Check for zip code pattern
                if not zip_code and cell_text and cell_text.replace("-", "").isdigit() and len(cell_text.replace("-", "")) == 5:
                    zip_code = cell_text
        
        # If we couldn't get name from cells, try from link text
        if not agency_name and links:
            agency_name = await links[0].inner_text()
            agency_name = agency_name.strip() if agency_name else None
        
        # If still no name, use first non-empty text from row
        if not agency_name:
            parts = row_text.split("\n")
            for part in parts:
                part = part.strip()
                if part and len(part) > 3:
                    agency_name = part
                    break
        
        if not detail_url:
            logger.warning(f"Could not find detail URL for agency: {agency_name}")
            return None
        
        return {
            "agency_name": agency_name,
            "city": city,
            "state": state,
            "zip": zip_code,
            "phone": phone,
            "detail_url": detail_url,
        }
    except Exception as e:
        logger.warning(f"Error extracting agency from row: {e}")
        return None


async def _scrape_detail_page(
    page: Page, detail_url: str, agency_data: dict, state: str, location: str
) -> Optional[HomeHealthAgency]:
    """
    Scrape detailed information from an agency's detail page.
    
    Returns HomeHealthAgency object with all available fields.
    """
    try:
        logger.debug(f"Scraping detail page: {detail_url}")
        
        # Check if page is still valid
        if page.is_closed():
            logger.warning(f"Page is closed, cannot scrape detail page: {detail_url}")
            return None
        
        # Add human-like delay before navigation
        await asyncio.sleep(random.uniform(0.3, 0.8))
        
        # Navigate to detail page
        await page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
        
        # Simulate human-like mouse movement
        try:
            await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            await asyncio.sleep(random.uniform(0.1, 0.2))
        except Exception:
            pass
        
        # Check title quickly - if Cloudflare, wait briefly
        title = await page.title()
        if "Just a moment" in title:
            for i in range(8):  # Max 8 seconds
                await asyncio.sleep(random.uniform(0.5, 1.0))
                try:
                    title = await page.title()
                    if "Just a moment" not in title:
                        break
                except Exception:
                    break
        
        # Human-like delay for content to render
        await asyncio.sleep(random.uniform(1.0, 1.5))
        
        # Extract NPI - look for "NPI #" or "NPI:" pattern
        npi = None
        page_text = await page.inner_text("body")
        
        # Try to find NPI in text
        import re
        npi_patterns = [
            r"NPI\s*#?\s*:?\s*(\d{10})",
            r"NPI\s*Number\s*:?\s*(\d{10})",
            r"(\d{10})",  # Just look for 10-digit number
        ]
        
        for pattern in npi_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                npi = match.group(1)
                break
        
        # Extract provider name - often in h1 or title
        provider_name = None
        name_selectors = ["h1", ".provider-name", "[class*='name']", "title"]
        for selector in name_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and len(text.strip()) > 0:
                        provider_name = text.strip()
                        # Remove "NPI #" prefix if present
                        provider_name = re.sub(r"NPI\s*#?\s*\d+", "", provider_name, flags=re.IGNORECASE).strip()
                        break
            except Exception:
                continue
        
        # Extract enumeration date
        enumeration_date = None
        enum_patterns = [
            r"Enumeration\s+Date\s*:?\s*([0-9/]+)",
            r"Enumerated\s*:?\s*([0-9/]+)",
            r"Date\s*:?\s*([0-9/]+)",
        ]
        for pattern in enum_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                enumeration_date = match.group(1)
                break
        
        # Extract address - look for address patterns
        address = Address()
        address_patterns = [
            r"Address\s*:?\s*([^\n]+)",
            r"Location\s*:?\s*([^\n]+)",
        ]
        
        # Try to find address in structured format
        address_text = None
        for pattern in address_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                address_text = match.group(1).strip()
                break
        
        if address_text:
            # Try to parse address components
            # Common format: "123 Street, City, ST 12345"
            parts = address_text.split(",")
            if len(parts) >= 2:
                address.street = parts[0].strip()
                address.city = parts[1].strip() if len(parts) > 1 else None
                if len(parts) >= 3:
                    state_zip = parts[2].strip()
                    # Try to extract state and zip
                    state_zip_match = re.match(r"([A-Z]{2})\s+(\d{5}(?:-\d{4})?)", state_zip)
                    if state_zip_match:
                        address.state = state_zip_match.group(1)
                        address.zip = state_zip_match.group(2)
                    else:
                        address.state = state_zip[:2] if len(state_zip) >= 2 else None
                        address.zip = state_zip[2:].strip() if len(state_zip) > 2 else None
        
        # Extract phone - look for phone patterns
        phone = agency_data.get("phone")
        if not phone:
            phone_patterns = [
                r"Phone\s*:?\s*([\(\)\d\s\-]+)",
                r"Telephone\s*:?\s*([\(\)\d\s\-]+)",
                r"(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})",
            ]
            for pattern in phone_patterns:
                match = re.search(pattern, page_text)
                if match:
                    phone = match.group(1).strip()
                    break
        
        # Extract authorized official information
        authorized_official = AuthorizedOfficial()
        ao_patterns = [
            r"Authorized\s+Official\s*:?\s*([^\n]+)",
            r"Contact\s+Person\s*:?\s*([^\n]+)",
        ]
        
        ao_text = None
        for pattern in ao_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                ao_text = match.group(1).strip()
                break
        
        if ao_text:
            # Try to extract name, title, phone from authorized official text
            # Format varies, so we'll try common patterns
            lines = ao_text.split("\n")
            if lines:
                authorized_official.name = lines[0].strip()
                if len(lines) > 1:
                    # Second line might be title
                    authorized_official.title = lines[1].strip()
                # Look for phone in the text
                phone_match = re.search(r"(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})", ao_text)
                if phone_match:
                    authorized_official.telephone = phone_match.group(1).strip()
        
        # Use agency_name from listing if provider_name not found
        if not provider_name:
            provider_name = agency_data.get("agency_name")
        
        return HomeHealthAgency(
            npi=npi,
            provider_name=provider_name,
            agency_name=agency_data.get("agency_name"),
            address=address,
            phone=phone,
            enumeration_date=enumeration_date,
            authorized_official=authorized_official,
            detail_url=detail_url,
            source_state=state,
            source_location=location,
        )
        
    except Exception as e:
        logger.warning(f"Failed to scrape detail page {detail_url}: {e}")
        # Return partial data if detail page fails
        return HomeHealthAgency(
            npi=None,
            provider_name=agency_data.get("agency_name"),
            agency_name=agency_data.get("agency_name"),
            address=Address(),
            phone=agency_data.get("phone"),
            enumeration_date=None,
            authorized_official=AuthorizedOfficial(),
            detail_url=detail_url,
            source_state=state,
            source_location=location,
        )

