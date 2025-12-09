-- Fix RLS policies to allow anon key access
-- Drop existing policies
DROP POLICY IF EXISTS "Allow all for authenticated users" ON agencies;
DROP POLICY IF EXISTS "Allow all for authenticated users" ON agency_addresses;
DROP POLICY IF EXISTS "Allow all for authenticated users" ON agency_officials;
DROP POLICY IF EXISTS "Allow all for authenticated users" ON scrape_logs;

-- Create new policies that allow all operations for anon key
CREATE POLICY "Allow all for anon" ON agencies
  FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all for anon" ON agency_addresses
  FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all for anon" ON agency_officials
  FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all for anon" ON scrape_logs
  FOR ALL USING (true) WITH CHECK (true);

