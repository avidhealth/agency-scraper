-- Lists table for user-created agency lists
CREATE TABLE IF NOT EXISTS lists (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Junction table for agencies in lists
CREATE TABLE IF NOT EXISTS list_agencies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  list_id UUID REFERENCES lists(id) ON DELETE CASCADE,
  agency_id UUID REFERENCES agencies(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(list_id, agency_id)  -- Prevent duplicate agencies in same list
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_list_agencies_list_id ON list_agencies(list_id);
CREATE INDEX IF NOT EXISTS idx_list_agencies_agency_id ON list_agencies(agency_id);
CREATE INDEX IF NOT EXISTS idx_lists_updated_at ON lists(updated_at);

-- Trigger to update updated_at for lists
CREATE TRIGGER update_lists_updated_at
    BEFORE UPDATE ON lists
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS
ALTER TABLE lists ENABLE ROW LEVEL SECURITY;
ALTER TABLE list_agencies ENABLE ROW LEVEL SECURITY;

-- RLS policies (allow all for authenticated users, or adjust as needed)
CREATE POLICY "Allow all for authenticated users" ON lists
  FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all for authenticated users" ON list_agencies
  FOR ALL USING (auth.role() = 'authenticated');

