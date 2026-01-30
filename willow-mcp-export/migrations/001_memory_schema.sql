-- Willow MCP Memory Schema
-- Run this in your Supabase SQL Editor

-- Projects table - tracks creative works
CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  type TEXT DEFAULT 'other', -- short_story, novel, article, script, other
  status TEXT DEFAULT 'idea', -- idea, outline, draft, revision, review, published
  word_count INTEGER DEFAULT 0,
  current_draft_id TEXT, -- Google Drive file ID
  notes TEXT,
  key_decisions JSONB DEFAULT '[]'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Creative memory - lessons learned, preferences, patterns
CREATE TABLE IF NOT EXISTS creative_memory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content TEXT NOT NULL,
  category TEXT NOT NULL, -- voice, structure, pacing, character, dialogue, technique, process
  worked BOOLEAN DEFAULT true,
  project_name TEXT, -- optional association
  use_count INTEGER DEFAULT 1,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Sessions - track conversation sessions for continuity
CREATE TABLE IF NOT EXISTS sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id),
  summary TEXT,
  decisions_made JSONB DEFAULT '[]'::jsonb,
  open_questions JSONB DEFAULT '[]'::jsonb,
  started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  ended_at TIMESTAMP WITH TIME ZONE
);

-- Feedback - store feedback received on projects
CREATE TABLE IF NOT EXISTS feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id),
  project_name TEXT, -- denormalized for easier queries
  source TEXT NOT NULL, -- e.g., 'harsh_critic', 'haiku_chorus', 'self'
  feedback TEXT NOT NULL,
  acted_on BOOLEAN DEFAULT false,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_updated ON projects(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_creative_memory_category ON creative_memory(category);
CREATE INDEX IF NOT EXISTS idx_creative_memory_worked ON creative_memory(worked);
CREATE INDEX IF NOT EXISTS idx_sessions_ended ON sessions(ended_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_project ON feedback(project_id);

-- Enable Row Level Security (optional, but recommended)
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE creative_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;

-- Create policies for service role access (adjust as needed)
CREATE POLICY "Service role full access to projects" ON projects
  FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access to creative_memory" ON creative_memory
  FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access to sessions" ON sessions
  FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access to feedback" ON feedback
  FOR ALL USING (true) WITH CHECK (true);

-- Optional: Vector search support (requires pgvector extension)
-- Uncomment if you want semantic search capabilities
/*
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS memory_embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content TEXT NOT NULL,
  embedding VECTOR(1536), -- OpenAI ada-002 dimensions
  source_type TEXT, -- 'draft', 'feedback', 'decision', 'lesson'
  source_id UUID,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memory_embeddings_vector
  ON memory_embeddings USING ivfflat (embedding vector_cosine_ops);
*/
