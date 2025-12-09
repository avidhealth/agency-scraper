const API_BASE = import.meta.env.VITE_API_URL || '';

export interface Agency {
  id: string;
  npi: string | null;
  provider_name: string | null;
  agency_name: string | null;
  phone: string | null;
  enumeration_date: string | null;
  detail_url: string;
  source_state: string;
  source_location: string;
  agency_addresses?: Array<{
    street: string | null;
    city: string | null;
    state: string | null;
    zip: string | null;
  }>;
  agency_officials?: Array<{
    name: string | null;
    title: string | null;
    telephone: string | null;
  }>;
}

export interface List {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface AgencyStats {
  total_agencies: number;
  by_state: Record<string, number>;
}

// Agencies API
export async function getAgencies(params?: {
  state?: string;
  location?: string;
  npi?: string;
  limit?: number;
  offset?: number;
}): Promise<{ count: number; agencies: Agency[] }> {
  const queryParams = new URLSearchParams();
  if (params?.state) queryParams.append('state', params.state);
  if (params?.location) queryParams.append('location', params.location);
  if (params?.npi) queryParams.append('npi', params.npi);
  queryParams.append('limit', String(params?.limit || 100));
  queryParams.append('offset', String(params?.offset || 0));

  const response = await fetch(`${API_BASE}/agencies?${queryParams}`);
  if (!response.ok) throw new Error('Failed to fetch agencies');
  return response.json();
}

export async function getAgencyStats(): Promise<AgencyStats> {
  const response = await fetch(`${API_BASE}/agencies/stats`);
  if (!response.ok) throw new Error('Failed to fetch stats');
  return response.json();
}

export async function updateAgency(agencyId: string, updates: Partial<Agency>): Promise<Agency> {
  const response = await fetch(`${API_BASE}/agencies/${agencyId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to update agency' }));
    throw new Error(error.detail || 'Failed to update agency');
  }
  return response.json();
}

export async function deleteAgency(agencyId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/agencies/${agencyId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to delete agency' }));
    throw new Error(error.detail || 'Failed to delete agency');
  }
}

// Lists API
export async function getLists(): Promise<{ lists: List[] }> {
  const response = await fetch(`${API_BASE}/lists`);
  if (!response.ok) throw new Error('Failed to fetch lists');
  return response.json();
}

export async function createList(name: string, description?: string): Promise<List> {
  const response = await fetch(`${API_BASE}/lists`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description: description || null }),
  });
  if (!response.ok) throw new Error('Failed to create list');
  return response.json();
}

export async function deleteList(listId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/lists/${listId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete list');
}

export async function getListAgencies(listId: string): Promise<{ count: number; agencies: Agency[] }> {
  const response = await fetch(`${API_BASE}/lists/${listId}/agencies`);
  if (!response.ok) throw new Error('Failed to fetch list agencies');
  return response.json();
}

export async function addAgencyToList(listId: string, agencyId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/lists/${listId}/agencies/${agencyId}`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to add agency to list');
}

export async function removeAgencyFromList(listId: string, agencyId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/lists/${listId}/agencies/${agencyId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to remove agency from list');
}

export function downloadListCSV(listId: string, _listName: string): void {
  window.location.href = `${API_BASE}/lists/${listId}/download/csv`;
}

export function downloadListJSON(listId: string, _listName: string): void {
  window.location.href = `${API_BASE}/lists/${listId}/download/json`;
}

// Batch scraping API
export interface BatchScrapeResult {
  state: string;
  location: string;
  agencies: Agency[];
  error: string | null;
}

export async function startBatchScrape(save: boolean = false): Promise<BatchScrapeResult[]> {
  const response = await fetch(`${API_BASE}/scrape/home-health/batch?save=${save ? "true" : "false"}`, {
    method: 'GET',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to start batch scrape' }));
    throw new Error(error.detail || 'Failed to start batch scrape');
  }
  return response.json();
}

// Counties CRUD API
export interface County {
  id: number;
  state: string;
  location: string;
}

export async function getCounties(): Promise<{ counties: County[] }> {
  const response = await fetch(`${API_BASE}/counties`);
  if (!response.ok) throw new Error('Failed to fetch counties');
  return response.json();
}

export async function addCounty(state: string, location: string): Promise<{ message: string; county: County }> {
  const response = await fetch(`${API_BASE}/counties?state=${encodeURIComponent(state)}&location=${encodeURIComponent(location)}`, {
    method: 'POST',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to add county' }));
    throw new Error(error.detail || 'Failed to add county');
  }
  return response.json();
}

export async function updateCounty(countyId: number, state: string, location: string): Promise<{ message: string; county: County }> {
  const response = await fetch(`${API_BASE}/counties/${countyId}?state=${encodeURIComponent(state)}&location=${encodeURIComponent(location)}`, {
    method: 'PUT',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to update county' }));
    throw new Error(error.detail || 'Failed to update county');
  }
  return response.json();
}

export async function deleteCounty(countyId: number): Promise<void> {
  const response = await fetch(`${API_BASE}/counties/${countyId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to delete county' }));
    throw new Error(error.detail || 'Failed to delete county');
  }
}

