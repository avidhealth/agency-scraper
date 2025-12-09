-- Fix RLS policies for lists to allow anon key access
-- Drop existing policies
DROP POLICY IF EXISTS "Allow all for authenticated users" ON lists;
DROP POLICY IF EXISTS "Allow all for authenticated users" ON list_agencies;

-- Create new policies that allow all operations for anon key
CREATE POLICY "Allow all for anon" ON lists
  FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all for anon" ON list_agencies
  FOR ALL USING (true) WITH CHECK (true);

