"""Pydantic models for request and response types."""

from pydantic import BaseModel
from typing import Optional


class Address(BaseModel):
    """Address model for agency location."""
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None


class AuthorizedOfficial(BaseModel):
    """Authorized official information."""
    name: Optional[str] = None
    title: Optional[str] = None
    telephone: Optional[str] = None


class HomeHealthAgency(BaseModel):
    """Home health agency information."""
    npi: Optional[str] = None
    provider_name: Optional[str] = None
    agency_name: Optional[str] = None  # Name from listing table vs legal name
    address: Address
    phone: Optional[str] = None
    enumeration_date: Optional[str] = None
    authorized_official: AuthorizedOfficial
    detail_url: str
    source_state: str
    source_location: str


class ScrapeRequest(BaseModel):
    """Request model for batch scraping."""
    state: str
    location: str


class BatchScrapeResult(BaseModel):
    """Result for a single state/location scrape in batch processing."""
    state: str
    location: str
    agencies: list[HomeHealthAgency]
    error: Optional[str] = None


class CreateListRequest(BaseModel):
    """Request model for creating a list."""
    name: str
    description: Optional[str] = None


