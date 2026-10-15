// The live record: who seconded which entry, and who checked it. Seconds and checks live in the Assembly's Supabase
// project, the one claims.sql is in (live.sql), reached only from here with the service key in this project's environment. The entries
// themselves are read from ledger.txt as deployed. The rules are api/_record.js; the page is live/live.js.
//
//   GET  /api/entries                         {members, signin, strangers, entries: [... seconds, checks, state]}
//   POST /api/entries/<n>/second   {tests}    201 the entry | 400 refused (error) | 401 no claim | 409 posted at the same moment
//   POST /api/entries/<n>/check    {who?, result, saw, tested, new, minutes, opened}      likewise
//
// Who posts: a member sends the token the front page's name claim left on the device (Authorization: Bearer); the
// name comes from assembly_claims, never from what was typed. With ASSEMBLY_STRANGERS=1 and ASSEMBLY_SALT set, a post
// with no Authorization header at all may be a check (never a second) under a name of its own. A token the table does
// not know is a 401, never a stranger. The stranger's source is a salted hash of x-forwarded-for, kept in the row and
// never returned. Without SUPABASE_URL and SUPABASE_SERVICE_KEY the answer is 503 and the ledger page stays as built.
'use strict';
const fs = require('fs');
const path = require('path');
const { hash } = require('./_claims');
const R = require('./_record');

const TABLES = '/rest/v1/';
const NAME = /^[A-Za-z0-9][\w .'-]{0,39}$/;                      // the claim table's own rule for a name
const LEDGER = path.join(__dirname, '..', 'ledger.txt');         // vercel.json includes it in the function
const MOST_BYTES = 16384;
const q = encodeURIComponent;
const now = () => new Date(Math.floor(Date.now() / 1000) * 1000);

const env = () => ({
  url: process.env.SUPABASE_URL, key: process.env.SUPABASE_SERVICE_KEY, salt: process.env.ASSEMBLY_SALT || '',
  // no salt, no stranger lane: an unsalted hash of an address can be undone by trying every address
  strangers: process.env.ASSEMBLY_STRANGERS === '1' && !!process.env.ASSEMBLY_SALT,
});

async function db(cfg, table, tail, init) {
  const r = await fetch(cfg.url + TABLES + table + tail, Object.assign({
    headers: { apikey: cfg.key, Authorization: 'Bearer ' + cfg.key, 'Content-Type': 'application/json',
               Prefer: 'return=representation' },
  }, init || {}));
  if (!r.ok) throw Object.assign(new Error('db ' + r.status), { status: r.status });
  return r.json();
}

// Both lists for one entry (num) or all of them, oldest first. ponytail: PostgREST returns at most 1000 rows a
// request, far above seven members' checks on nine entries; page the listing if the record ever nears it.
const lists = (cfg, num) => {
  const only = num ? 'num=eq.' + num + '&' : '';
  return Promise.all([db(cfg, 'assembly_seconds', '?' + only + 'select=*&order=id'),
                      db(cfg, 'assembly_checks', '?' + only + 'select=*&order=seq')]);
};

async function insert(cfg, table, row, clash) {
  try {
    return (await db(cfg, table, '', { method: 'POST', body: JSON.stringify(row) }))[0];
  } catch (e) {
    if (e.status === 409) throw new R.Refused(clash, 409);   // the table's unique index: this one is already there
    throw e;
  }
}

// Who is posting: {member} from their claim, or {via} for a stranger's check, or a 401.
async function poster(cfg, req, act) {
  const auth = req.headers.authorization;
  if (auth) {
    const token = String(auth).replace(/^Bearer\s+/i, '').trim();
    if (!token) throw new R.Refused('Claim your name on the front page first, then post from the same device.', 401);
    const rows = await db(cfg, 'assembly_claims', '?token_hash=eq.' + q(hash(token)) + '&select=name');
    if (!rows.length) throw new R.Refused('This device has no claim, or it was reissued. Claim your name on the front page again.', 401);
    if (!NAME.test(rows[0].name)) throw new Error('claim row with a bad name');
    return { member: rows[0].name };
  }
  if (!(cfg.strangers && act === 'check')) {
    throw new R.Refused('Claim your name on the front page first, then post from the same device.', 401);
  }
  // Vercel sets x-forwarded-for to the client's address and drops any the client sent
  const address = String(req.headers['x-forwarded-for'] || '').split(',')[0].trim();
  if (!address) throw new R.Refused('Your connection did not say where it is posting from. Claim your name on the front page instead.');
  return { via: R.sourceOf(address, cfg.salt) };
}

async function post(cfg, req, res) {
  const m = /^\/api\/entries\/(\d+)\/(second|check)\/?(?:\?|$)/.exec(req.url || '');
  const num = Number((req.query && req.query.num) || (m && m[1])), act = (req.query && req.query.act) || (m && m[2]);
  if (!(Number.isInteger(num) && num > 0) || (act !== 'second' && act !== 'check')) {
    return res.status(404).json({ error: 'Nothing is posted at that address.' });
  }
  // JSON only: a page on another site can send a plain-text form here without asking, but not JSON
  if (String(req.headers['content-type'] || '').split(';')[0].trim().toLowerCase() !== 'application/json') {
    return res.status(415).json({ error: 'Send the post as JSON.' });
  }
  const body = req.body;
  if (!body || typeof body !== 'object' || Array.isArray(body)) return res.status(400).json({ error: 'The post is not a set of answers.' });
  if (JSON.stringify(body).length > MOST_BYTES) return res.status(413).json({ error: 'The post is too long.' });

  const who = await poster(cfg, req, act);
  const { members, entries } = R.readLedger(fs.readFileSync(LEDGER, 'utf8'));
  const e = entries.find(x => x.num === num);
  if (!e) throw new R.Refused(`There is no entry ${num}.`);
  const [seconds, checks] = await lists(cfg, num);
  const at = now();
  if (act === 'second') {
    const row = R.secondRow({ e, who: who.member, body, seconds, at });
    seconds.push(await insert(cfg, 'assembly_seconds', row, 'You have already seconded this entry.'));
  } else {
    const viaToday = !who.via ? 0 : (await db(cfg, 'assembly_checks', '?via=eq.' + q(who.via) + '&at=gt.' +
      q(new Date(at - 864e5).toISOString()) + '&select=id&limit=' + R.STRANGER_PER_DAY)).length;
    const row = R.checkRow({ e, members, member: who.member, via: who.via, body, seconds, checks, viaToday, at });
    checks.push(await insert(cfg, 'assembly_checks', row, 'Someone posted on this entry at the same moment. Read it again and post again.'));
  }
  return res.status(201).json(R.view(e, members, seconds, checks, at));
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  const cfg = env();
  if (!cfg.url || !cfg.key) return res.status(503).json({ error: 'not set up' });
  try {
    if (req.method === 'POST') return await post(cfg, req, res);
    if (req.method !== 'GET') return res.status(405).json({ error: 'method' });
    const { members, entries } = R.readLedger(fs.readFileSync(LEDGER, 'utf8'));
    const [seconds, checks] = await lists(cfg);
    const of = (rows, num) => rows.filter(r => r.num === num);
    const at = now();
    return res.status(200).json({ members, signin: true, strangers: cfg.strangers,
      entries: entries.map(e => R.view(e, members, of(seconds, e.num), of(checks, e.num), at)) });
  } catch (e) {
    if (e instanceof R.Refused) return res.status(e.status).json({ error: e.message });
    return res.status(502).json({ error: 'the record did not answer' });
  }
};
