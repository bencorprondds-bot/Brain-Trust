/**
 * Supabase Client
 *
 * Shared database client for memory operations
 */

import { createClient } from '@supabase/supabase-js';

let supabase = null;

export function getSupabaseClient() {
  if (supabase) return supabase;

  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_KEY;

  if (!url || !key) {
    throw new Error(
      'SUPABASE_URL and SUPABASE_KEY environment variables must be set'
    );
  }

  supabase = createClient(url, key);
  return supabase;
}

export default getSupabaseClient;
