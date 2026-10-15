-- The live record (api/entries.js, api/_record.js; live/server.py is its local twin). Paste into the SQL editor of the
-- same Supabase project as claims.sql, once, after it. Two tables: who seconded which entry, and who checked it. The entries
-- themselves stay in ledger.txt; a row here points at one by its number.
-- Row-level security is on with no policies, so the publishable key can neither read nor write them: only the service
-- key, which lives in the febu-assembly Vercel project's environment, reaches them.

create table if not exists public.assembly_seconds (
  id    bigint generated always as identity primary key,
  num   integer not null,                       -- the ledger entry's number
  who   text not null,                          -- a member's name, taken from their claim
  at    timestamptz not null default now()
);
-- one second per person per entry, in any capitals; this also stops two posts at the same moment from both landing
create unique index if not exists assembly_seconds_once on public.assembly_seconds (num, lower(who));

create table if not exists public.assembly_checks (
  id      bigint generated always as identity primary key,
  num     integer not null,
  seq     integer not null,                     -- this check's place on the entry: 1, 2, 3. Two posts that both
                                                -- read the same entry and both take the next place cannot both land
  who     text not null,                        -- a member's name from their claim, or a stranger's own name
  result  text not null check (result in ('HOLDS', 'DOESN''T HOLD', 'KEPT', 'BROKEN')),
  saw     text not null,
  tested  text not null,
  "new"   text not null,                        -- the thing nobody had written yet (quoted: NEW is a word in triggers)
  minutes integer not null check (minutes between 1 and 600),
  at      timestamptz not null default now(),
  via     text                                  -- a stranger's salted source hash; null for a member. Never returned.
);
create unique index if not exists assembly_checks_place on public.assembly_checks (num, seq);
create index if not exists assembly_checks_source on public.assembly_checks (via, at) where via is not null;

alter table public.assembly_seconds enable row level security;
alter table public.assembly_checks  enable row level security;
-- The two public roles get nothing, so a later policy or a switched-off RLS cannot open these by itself.
revoke all on public.assembly_seconds, public.assembly_checks from anon, authenticated;
-- Likewise the service key's role (see claims.sql): without this the project answers 403 and the record does not answer.
grant all on public.assembly_seconds, public.assembly_checks to service_role;

-- Rule 2: nothing in the record is rewritten or removed. The database refuses it, whoever asks.
-- ponytail: rule 2 lets personal information become "[removed]"; this refuses that too, until someone needs it. Whoever
-- owns the database can still drop a trigger or a table; the ledger's git history and the Internet Archive copies are
-- what hold that line.
create or replace function public.assembly_rule_2() returns trigger language plpgsql as $$
begin
  raise exception 'rule 2: nothing in the record is rewritten or removed';
end $$;

drop trigger if exists assembly_seconds_fixed on public.assembly_seconds;
create trigger assembly_seconds_fixed before update or delete on public.assembly_seconds
  for each row execute function public.assembly_rule_2();

drop trigger if exists assembly_checks_fixed on public.assembly_checks;
create trigger assembly_checks_fixed before update or delete on public.assembly_checks
  for each row execute function public.assembly_rule_2();
