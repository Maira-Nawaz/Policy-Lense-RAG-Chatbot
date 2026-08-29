import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    "NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY must be set -- see .env.local.example.",
  );
}

// One client for the whole app: auth session (login/signup/sign-out) and, via
// lib/api.ts, the access token attached to every backend call.
export const supabase = createClient(supabaseUrl, supabaseAnonKey);
