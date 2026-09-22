import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
// Supabase's newer API key format ("publishable key", sb_publishable_...)
// replaces the legacy JWT-based anon key; it's used the same way.
const supabasePublishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

if (!supabaseUrl || !supabasePublishableKey) {
  throw new Error(
    "Missing Supabase env vars. Copy .env.local.example to .env.local and fill in " +
      "NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY from your Supabase project settings."
  );
}

// A single server-side client is enough here: every read/write goes through
// Server Components and Server Actions (src/app/posts/actions.ts), never
// directly from the browser, so there's no session/cookie state to manage.
export const supabase = createClient(supabaseUrl, supabasePublishableKey, {
  auth: { persistSession: false },
});
