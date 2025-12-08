# NPIDB Home Health Agency Scraper

A FastAPI service that scrapes home health agency data from NPIDB (npidb.org) using Playwright.

## Features

- Scrape home health agencies by state and location (city/county)
- Batch processing from `counties.csv`
- Extracts comprehensive agency information including:
  - NPI number
  - Provider name and agency name
  - Full address (street, city, state, zip)
  - Phone number
  - Enumeration date
  - Authorized official information (name, title, phone)

## Setup

### Prerequisites

- Python 3.8+
- pip

### Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
playwright install
```

Or install just Chromium:
```bash
playwright install chromium
```

## Running the Server

Start the FastAPI server with auto-reload:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

API documentation (Swagger UI) is available at:
- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## Usage

### Single Scrape Endpoint

Scrape agencies for a specific state and location:

```bash
curl 'http://localhost:8000/scrape/home-health?state=NC&location=Raleigh'
```

Example response:
```json
[
  {
    "npi": "1649055153",
    "provider_name": "A NEW HORIZON HOME CARE VII,LLP",
    "agency_name": "A NEW HORIZON HOME CARE VII,LLP",
    "address": {
      "street": "123 Main St",
      "city": "Raleigh",
      "state": "NC",
      "zip": "27601"
    },
    "phone": "(919) 555-1234",
    "enumeration_date": "01/01/2020",
    "authorized_official": {
      "name": "John Doe",
      "title": "CEO",
      "telephone": "(919) 555-1234"
    },
    "detail_url": "https://npidb.org/organizations/agencies/home-health_251e00000x/1649055153.aspx",
    "source_state": "NC",
    "source_location": "Raleigh"
  }
]
```

### Batch Scrape Endpoint

Process all state/county pairs from `counties.csv`:

```bash
curl 'http://localhost:8000/scrape/home-health/batch'
```

This will read `counties.csv` and process each row, returning results for all state/county combinations.

## Project Structure

```
agency-scraper/
├── app/
│   ├── __init__.py          # Package initialization
│   ├── main.py              # FastAPI app and route definitions
│   ├── scraper.py           # Playwright scraping logic
│   ├── models.py            # Pydantic models for request/response
│   └── config.py            # Configuration constants
├── counties.csv             # State/county pairs for batch processing
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Configuration

Configuration constants are defined in `app/config.py`:

- `BASE_URL`: Base URL for NPIDB home health agencies
- `TAXONOMY_CODE`: Taxonomy code for home health agencies
- `PLAYWRIGHT_SETTINGS`: Browser settings (headless mode, timeouts)
- `PAGE_LOAD_TIMEOUT`: Timeout for page loads (15 seconds)
- `SELECTOR_TIMEOUT`: Timeout for selector waits (10 seconds)

## Scraper Details

The scraper uses Playwright to:

1. Navigate to NPIDB search results page
2. Extract agency listings from the results table
3. Handle pagination automatically
4. Visit each agency's detail page to extract full information
5. Return structured data as Pydantic models

### Selector Notes

The scraper uses flexible selector patterns to handle variations in NPIDB's HTML structure. If the site structure changes, you may need to update selectors in `app/scraper.py`:

- Results table: Tries multiple selectors (`table`, `.results`, `tbody tr`, etc.)
- Agency rows: Looks for table rows or elements with "agency" or "result" in class names
- Pagination: Searches for "Next" links, page number links, or navigation buttons
- Detail page fields: Uses regex patterns to extract NPI, dates, addresses, etc.

All selectors are documented in the code with comments explaining their purpose and potential alternatives.

### Error Handling

- Individual agency failures don't stop the entire scrape
- Retry logic for failed page loads (one retry before failing)
- Comprehensive logging for debugging
- Graceful handling of missing fields (returns None)

## Development

### Running Tests

(Add test instructions if you create tests)

### Code Style

The code follows Python best practices:
- Type hints throughout
- Async/await for all I/O operations
- Comprehensive error handling
- Clear logging
- Modular structure

## Troubleshooting

### Playwright Browser Issues

If you encounter browser-related errors:

1. Ensure browsers are installed: `playwright install`
2. Check that Chromium is available: `playwright install chromium`
3. Try running with headless=False in `app/config.py` for debugging

### Selector Issues

If scraping fails to find elements:

1. Check the NPIDB site structure - it may have changed
2. Update selectors in `app/scraper.py` based on current HTML
3. Use browser dev tools to inspect the actual page structure
4. Check logs for which selectors are being tried

### Timeout Issues

If pages are timing out:

1. Increase `PAGE_LOAD_TIMEOUT` in `app/config.py`
2. Check your internet connection
3. Verify the NPIDB site is accessible

## License

(Add license information if applicable)


