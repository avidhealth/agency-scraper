-- NPIDB Home Health Agency Scraper Database Schema
-- Run this SQL in your Supabase SQL Editor to create the tables

-- Agencies table
CREATE TABLE IF NOT EXISTS agencies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  npi TEXT UNIQUE,  -- National Provider Identifier
  provider_name TEXT,
  agency_name TEXT,
  phone TEXT,
  enumeration_date DATE,
  detail_url TEXT NOT NULL,
  source_state TEXT NOT NULL,
  source_location TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Addresses table
CREATE TABLE IF NOT EXISTS agency_addresses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id UUID REFERENCES agencies(id) ON DELETE CASCADE,
  street TEXT,
  city TEXT,
  state TEXT,
  zip TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(agency_id)  -- One address per agency
);

-- Authorized officials table
CREATE TABLE IF NOT EXISTS agency_officials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id UUID REFERENCES agencies(id) ON DELETE CASCADE,
  name TEXT,
  title TEXT,
  telephone TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(agency_id)  -- One official per agency
);

-- Scrape history (track when data was collected)
CREATE TABLE IF NOT EXISTS scrape_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  state TEXT NOT NULL,
  location TEXT NOT NULL,
  agencies_found INTEGER DEFAULT 0,
  scrape_method TEXT,
  started_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  error TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_agencies_npi ON agencies(npi);
CREATE INDEX IF NOT EXISTS idx_agencies_state ON agencies(source_state);
CREATE INDEX IF NOT EXISTS idx_agencies_location ON agencies(source_location);
CREATE INDEX IF NOT EXISTS idx_agencies_updated ON agencies(updated_at);
CREATE INDEX IF NOT EXISTS idx_agencies_provider_name ON agencies(provider_name);
CREATE INDEX IF NOT EXISTS idx_addresses_agency_id ON agency_addresses(agency_id);
CREATE INDEX IF NOT EXISTS idx_officials_agency_id ON agency_officials(agency_id);
CREATE INDEX IF NOT EXISTS idx_scrape_logs_state_location ON scrape_logs(state, location);
CREATE INDEX IF NOT EXISTS idx_scrape_logs_started_at ON scrape_logs(started_at);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update updated_at
CREATE TRIGGER update_agencies_updated_at
    BEFORE UPDATE ON agencies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (optional - adjust policies as needed)
ALTER TABLE agencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE agency_addresses ENABLE ROW LEVEL SECURITY;
ALTER TABLE agency_officials ENABLE ROW LEVEL SECURITY;
ALTER TABLE scrape_logs ENABLE ROW LEVEL SECURITY;

-- Example RLS policies (adjust based on your needs)
-- Allow all operations for authenticated users
CREATE POLICY "Allow all for authenticated users" ON agencies
  FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all for authenticated users" ON agency_addresses
  FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all for authenticated users" ON agency_officials
  FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all for authenticated users" ON scrape_logs
  FOR ALL USING (auth.role() = 'authenticated');

-- Or allow public read access (adjust as needed)
-- CREATE POLICY "Allow public read" ON agencies
--   FOR SELECT USING (true);

