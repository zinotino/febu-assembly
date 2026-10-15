-- The one-time name claim (api/claim.js, claims.py). Paste into the febu-host Supabase project's SQL editor once.
-- One row per member name. Row-level security is on with no policies, so the publishable key can neither read nor
-- write it: only the service key, which lives in the febu-ledger Vercel project's environment, reaches it.
create table if not exists public.assembly_claims (
  name        text primary key,                 -- as on the ledger's Member line
  code_hash   text not null,                    -- sha256 of the invite code, issued by claims.py
  token_hash  text,                             -- sha256 of the device token, once claimed
  claimed_at  timestamptz,                      -- null until the code is entered on the site
  failed      integer not null default 0,       -- wrong codes since issue; five lock the name until reissued
  issued_at   timestamptz not null default now()
);
alter table public.assembly_claims enable row level security;
