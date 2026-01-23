-- Enable JSONB checks if needed
-- create extension if not exists "uuid-ossp";

CREATE TABLE IF NOT EXISTS executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    workflow_snapshot JSONB NOT NULL,  -- Stores the full node/edge graph
    result_summary TEXT,               -- Stores the final output string
    agents_active INTEGER,             -- How many agents participated
    status TEXT DEFAULT 'completed',   -- completed, failed, running
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for faster history lookup
CREATE INDEX idx_executions_timestamp ON executions(timestamp DESC);
