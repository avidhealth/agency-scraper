"""Supabase storage module for saving and querying agency data."""

import logging
import os
from typing import List, Optional, Dict, Any
from datetime import datetime

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

from .models import HomeHealthAgency

logger = logging.getLogger(__name__)


class SupabaseStorage:
    """Storage interface for saving and querying agencies in Supabase."""
    
    def __init__(self):
        if not SUPABASE_AVAILABLE:
            raise ImportError(
                "supabase package not installed. Install with: pip install supabase"
            )
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY environment variables must be set"
            )
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized")
    
    async def save_agencies(self, agencies: List[HomeHealthAgency]) -> Dict[str, Any]:
        """
        Save or update agencies in Supabase.
        
        Uses upsert to update existing agencies (matched by NPI) or insert new ones.
        
        Args:
            agencies: List of HomeHealthAgency objects to save
            
        Returns:
            Dictionary with save statistics
        """
        if not agencies:
            return {"saved": 0, "updated": 0, "errors": 0}
        
        saved_count = 0
        updated_count = 0
        error_count = 0
        
        for agency in agencies:
            try:
                # Prepare agency data
                agency_data = {
                    "npi": agency.npi,
                    "provider_name": agency.provider_name,
                    "agency_name": agency.agency_name,
                    "phone": agency.phone,
                    "enumeration_date": agency.enumeration_date,
                    "detail_url": agency.detail_url,
                    "source_state": agency.source_state,
                    "source_location": agency.source_location,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                
                # Upsert agency (update if NPI exists, insert if not)
                # First check if agency exists
                existing = None
                if agency.npi:
                    result = self.supabase.table("agencies").select("id").eq("npi", agency.npi).execute()
                    if result.data:
                        existing = result.data[0]
                
                if existing:
                    # Update existing agency
                    result = self.supabase.table("agencies").update(agency_data).eq("id", existing["id"]).execute()
                    updated_count += 1
                    agency_id = existing["id"]
                else:
                    # Insert new agency
                    agency_data["created_at"] = datetime.utcnow().isoformat()
                    result = self.supabase.table("agencies").insert(agency_data).execute()
                    saved_count += 1
                    agency_id = result.data[0]["id"] if result.data else None
                
                if not agency_id:
                    logger.warning(f"Failed to get agency_id for {agency.npi}")
                    error_count += 1
                    continue
                
                # Save address (upsert)
                if agency.address:
                    address_data = {
                        "agency_id": agency_id,
                        "street": agency.address.street,
                        "city": agency.address.city,
                        "state": agency.address.state,
                        "zip": agency.address.zip,
                    }
                    # Delete existing address and insert new one (simpler than upsert with conflict)
                    self.supabase.table("agency_addresses").delete().eq("agency_id", agency_id).execute()
                    self.supabase.table("agency_addresses").insert(address_data).execute()
                
                # Save authorized official (upsert)
                if agency.authorized_official:
                    official_data = {
                        "agency_id": agency_id,
                        "name": agency.authorized_official.name,
                        "title": agency.authorized_official.title,
                        "telephone": agency.authorized_official.telephone,
                    }
                    # Delete existing official and insert new one
                    self.supabase.table("agency_officials").delete().eq("agency_id", agency_id).execute()
                    self.supabase.table("agency_officials").insert(official_data).execute()
                
            except Exception as e:
                logger.error(f"Error saving agency {agency.npi}: {e}", exc_info=True)
                error_count += 1
                continue
        
        result_stats = {
            "saved": saved_count,
            "updated": updated_count,
            "errors": error_count,
            "total": len(agencies),
        }
        
        logger.info(f"Saved agencies: {result_stats}")
        return result_stats
    
    def get_agencies(
        self,
        state: Optional[str] = None,
        location: Optional[str] = None,
        npi: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Query agencies from Supabase.
        
        Args:
            state: Filter by source state
            location: Filter by source location
            npi: Filter by NPI number
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of agency dictionaries with joined address and official data
        """
        query = self.supabase.table("agencies").select(
            """
            *,
            agency_addresses(*),
            agency_officials(*)
            """
        )
        
        if state:
            query = query.eq("source_state", state.upper())
        if location:
            query = query.eq("source_location", location)
        if npi:
            query = query.eq("npi", npi)
        
        query = query.order("updated_at", desc=True).limit(limit).offset(offset)
        
        result = query.execute()
        return result.data if result.data else []
    
    def get_agency_by_npi(self, npi: str) -> Optional[Dict[str, Any]]:
        """Get a single agency by NPI."""
        results = self.get_agencies(npi=npi, limit=1)
        return results[0] if results else None
    
    def get_agency_by_id(self, agency_id: str) -> Optional[Dict[str, Any]]:
        """Get a single agency by ID."""
        try:
            result = self.supabase.table("agencies").select("*").eq("id", agency_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get agency by ID: {e}", exc_info=True)
            raise
    
    def delete_agency(self, agency_id: str) -> bool:
        """Delete an agency by ID (cascade deletes addresses and officials)."""
        try:
            self.supabase.table("agencies").delete().eq("id", agency_id).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to delete agency: {e}", exc_info=True)
            raise
    
    def update_agency(self, agency_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an agency by ID."""
        try:
            updates["updated_at"] = datetime.utcnow().isoformat()
            result = self.supabase.table("agencies").update(updates).eq("id", agency_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to update agency: {e}", exc_info=True)
            raise
    
    def log_scrape(
        self,
        state: str,
        location: str,
        agencies_found: int,
        scrape_method: str,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Log a scrape operation to the scrape_logs table.
        
        Args:
            state: State code
            location: Location name
            agencies_found: Number of agencies found
            scrape_method: Method used (playwright, curl_cffi, selenium)
            error: Error message if scrape failed
            
        Returns:
            Created log entry
        """
        log_data = {
            "state": state,
            "location": location,
            "agencies_found": agencies_found,
            "scrape_method": scrape_method,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "error": error,
        }
        
        result = self.supabase.table("scrape_logs").insert(log_data).execute()
        return result.data[0] if result.data else None


    def create_list(self, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new list."""
        try:
            list_data = {
                "name": name,
                "description": description,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            result = self.supabase.table("lists").insert(list_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to create list: {e}", exc_info=True)
            raise
    
    def get_lists(self) -> List[Dict[str, Any]]:
        """Get all lists."""
        try:
            result = self.supabase.table("lists").select("*").order("updated_at", desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Failed to get lists: {e}", exc_info=True)
            raise
    
    def get_list(self, list_id: str) -> Optional[Dict[str, Any]]:
        """Get a single list by ID."""
        try:
            result = self.supabase.table("lists").select("*").eq("id", list_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get list: {e}", exc_info=True)
            raise
    
    def delete_list(self, list_id: str) -> bool:
        """Delete a list (cascade deletes list_agencies)."""
        try:
            self.supabase.table("lists").delete().eq("id", list_id).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to delete list: {e}", exc_info=True)
            raise
    
    def add_agency_to_list(self, list_id: str, agency_id: str) -> Dict[str, Any]:
        """Add an agency to a list."""
        try:
            list_agency_data = {
                "list_id": list_id,
                "agency_id": agency_id,
            }
            result = self.supabase.table("list_agencies").insert(list_agency_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to add agency to list: {e}", exc_info=True)
            raise
    
    def remove_agency_from_list(self, list_id: str, agency_id: str) -> bool:
        """Remove an agency from a list."""
        try:
            self.supabase.table("list_agencies").delete().eq("list_id", list_id).eq("agency_id", agency_id).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to remove agency from list: {e}", exc_info=True)
            raise
    
    def get_list_agencies(self, list_id: str) -> List[Dict[str, Any]]:
        """Get all agencies in a list with full agency details."""
        try:
            result = self.supabase.table("list_agencies").select(
                """
                *,
                agency:agencies(
                    *,
                    agency_addresses(*),
                    agency_officials(*)
                )
                """
            ).eq("list_id", list_id).execute()
            
            agencies = []
            if result.data:
                for item in result.data:
                    if item.get("agency"):
                        agencies.append(item["agency"])
            return agencies
        except Exception as e:
            logger.error(f"Failed to get list agencies: {e}", exc_info=True)
            raise


def get_storage() -> Optional[SupabaseStorage]:
    """Get SupabaseStorage instance if configured, None otherwise."""
    try:
        return SupabaseStorage()
    except (ImportError, ValueError) as e:
        logger.warning(f"Supabase storage not available: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error initializing Supabase storage: {e}", exc_info=True)
        return None

