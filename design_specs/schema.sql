-- Brain Trust v2.0 - Supabase Schema

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- 1. WORKFLOWS
-- Stores the visual graph structure (nodes/edges)
create table public.workflows (
  id uuid default uuid_generate_v4() primary key,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null,
  name text not null,
  description text,
  graph_json jsonb not null default '{}'::jsonb, -- The React Flow JSON state
  is_template boolean default false -- If true, appears in "Templates" sidebar
);

-- 2. AGENTS (Global Library)
-- Reusable agent definitions (like your agents.json, but SQL)
create table public.agents (
  id uuid default uuid_generate_v4() primary key,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  name text not null,
  role text not null,
  goal text,
  backstory text,
  model text default 'gemini-1.5-pro',
  avatar_url text, -- For the UI
  tools text[] -- Array of tool identifiers e.g. ['web_search', 'drive_reader']
);

-- 3. RUNS (Execution History)
create table public.runs (
  id uuid default uuid_generate_v4() primary key,
  workflow_id uuid references public.workflows(id) on delete cascade,
  started_at timestamp with time zone default timezone('utc'::text, now()) not null,
  completed_at timestamp with time zone,
  status text check (status in ('running', 'completed', 'failed')) default 'running',
  result_output text, -- Final output
  logs jsonb -- Structured logs of the execution steps
);

-- RLS Policies (Row Level Security) - Optional if single user
alter table public.workflows enable row level security;
create policy "Allow generic access" on public.workflows for all using (true);
