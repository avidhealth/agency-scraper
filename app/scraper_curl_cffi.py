"""Alternative scraper using curl_cffi for better Cloudflare bypass."""

import asyncio
import logging
import urllib.parse
import re
from typing import List, Optional
from curl_cffi import requests
from bs4 import BeautifulSoup

from .config import BASE_URL
from .models import HomeHealthAgency, Address, AuthorizedOfficial

logger = logging.getLogger(__name__)


async def scrape_home_health_agencies_curl_cffi(
    state: str, location: str
) -> List[HomeHealthAgency]:
    """
    Scrape using curl_cffi for better Cloudflare bypass.
    
    Args:
        state: 2-letter state code (e.g., "NC", "VA")
        location: City or county name (e.g., "Raleigh", "Henrico County")
    
    Returns:
        List of HomeHealthAgency objects with scraped data
    """
    # Normalize inputs
    state_lower = state.strip().lower()
    location_encoded = urllib.parse.quote_plus(location.strip())
    
    # Build URL
    url = f"{BASE_URL}/{state_lower}/?location={location_encoded}"
    logger.info(f"Scraping URL with curl_cffi: {url}")
    
    agencies = []
    
    try:
        # Use curl_cffi with browser impersonation
        # Impersonate Chrome to get real TLS fingerprint
        session = requests.Session()
        
        # Get results page
        response = session.get(
            url,
            impersonate="chrome120",  # Use Chrome 120 fingerprint
            timeout=30,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to load page: {response.status_code}")
            return agencies
        
        # Check for Cloudflare challenge
        if "Just a moment" in response.text or "challenge" in response.text.lower():
            logger.warning("Cloudflare challenge detected, curl_cffi may need additional handling")
            # Could implement challenge solving here if needed
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract agency links
        agency_links = soup.find_all('a', href=lambda x: x and ('.aspx' in x or 'home-health_251e00000x' in x))
        
        logger.info(f"Found {len(agency_links)} agency links")
        
        # Extract basic info from listing and get detail URLs
        detail_urls = []
        for link in agency_links:
            href = link.get('href', '')
            if href.startswith('/'):
                detail_url = f"https://npidb.org{href}"
            elif href.startswith('http'):
                detail_url = href
            else:
                detail_url = f"{BASE_URL}/{href}"
            
            agency_name = link.get_text(strip=True)
            if not agency_name:
                agency_name = link.get('title', 'Unknown Agency')
            
            detail_urls.append({
                'url': detail_url,
                'name': agency_name
            })
        
        # Scrape each detail page
        for detail_info in detail_urls:
            try:
                detail_response = session.get(
                    detail_info['url'],
                    impersonate="chrome120",
                    timeout=30
                )
                
                if detail_response.status_code == 200:
                    agency = _parse_detail_page(detail_response.text, detail_info, state, location)
                    if agency:
                        agencies.append(agency)
                        logger.debug(f"Scraped: {agency.provider_name}")
                
                # Small delay between requests
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Failed to scrape detail page {detail_info['url']}: {e}")
                continue
        
        logger.info(f"Successfully scraped {len(agencies)} agencies")
        return agencies
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        raise


def _parse_detail_page(html: str, detail_info: dict, state: str, location: str) -> Optional[HomeHealthAgency]:
    """Parse detail page HTML to extract agency information."""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        
        # Extract NPI
        npi = None
        npi_patterns = [
            r"NPI\s*#?\s*:?\s*(\d{10})",
            r"NPI\s*Number\s*:?\s*(\d{10})",
        ]
        for pattern in npi_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                npi = match.group(1)
                break
        
        # Extract provider name
        provider_name = detail_info.get('name')
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text()
            # Remove NPI from title if present
            provider_name = re.sub(r'NPI\s*#?\s*\d+', '', title_text, flags=re.IGNORECASE).strip()
            if provider_name:
                provider_name = provider_name.split(';')[0].strip()
        
        # Extract enumeration date
        enumeration_date = None
        enum_match = re.search(r"Enumeration\s+Date\s*:?\s*([0-9/]+)", text, re.IGNORECASE)
        if enum_match:
            enumeration_date = enum_match.group(1)
        
        # Extract address
        address = Address()
        address_match = re.search(r"Address\s*:?\s*([^\n]+)", text, re.IGNORECASE)
        if address_match:
            address_text = address_match.group(1).strip()
            parts = address_text.split(',')
            if len(parts) >= 2:
                address.street = parts[0].strip()
                address.city = parts[1].strip() if len(parts) > 1 else None
                if len(parts) >= 3:
                    state_zip = parts[2].strip()
                    state_zip_match = re.match(r"([A-Z]{2})\s+(\d{5}(?:-\d{4})?)", state_zip)
                    if state_zip_match:
                        address.state = state_zip_match.group(1)
                        address.zip = state_zip_match.group(2)
        
        # Extract phone
        phone = None
        phone_match = re.search(r"Phone\s*:?\s*([\(\)\d\s\-]+)", text, re.IGNORECASE)
        if phone_match:
            phone = phone_match.group(1).strip()
        
        # Extract authorized official
        authorized_official = AuthorizedOfficial()
        ao_match = re.search(r"Authorized\s+Official\s*:?\s*([^\n]+)", text, re.IGNORECASE)
        if ao_match:
            ao_text = ao_match.group(1).strip()
            lines = ao_text.split('\n')
            if lines:
                authorized_official.name = lines[0].strip()
                if len(lines) > 1:
                    authorized_official.title = lines[1].strip()
                phone_match = re.search(r"(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})", ao_text)
                if phone_match:
                    authorized_official.telephone = phone_match.group(1).strip()
        
        return HomeHealthAgency(
            npi=npi,
            provider_name=provider_name or detail_info.get('name'),
            agency_name=detail_info.get('name'),
            address=address,
            phone=phone,
            enumeration_date=enumeration_date,
            authorized_official=authorized_official,
            detail_url=detail_info['url'],
            source_state=state,
            source_location=location,
        )
        
    except Exception as e:
        logger.warning(f"Error parsing detail page: {e}")
        return None

