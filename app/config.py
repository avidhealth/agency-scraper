"""Configuration constants for NPIDB scraper."""

# Base URL for NPIDB home health agencies
BASE_URL = "https://npidb.org/organizations/agencies/home-health_251e00000x"

# Taxonomy code for home health agencies
TAXONOMY_CODE = "home-health_251e00000x"

# Playwright settings
PLAYWRIGHT_SETTINGS = {
    "headless": True,
    "timeout": 30000,  # 30 seconds default timeout
}

# Page load timeout (in milliseconds)
PAGE_LOAD_TIMEOUT = 15000  # 15 seconds

# Selector wait timeout (in milliseconds)
SELECTOR_TIMEOUT = 10000  # 10 seconds


