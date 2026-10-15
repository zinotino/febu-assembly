// The one-time name claim. A name on the ledger's Member line belongs to whoever enters its invite code first;
// the browser then holds a token that says so. Rows live in the febu-host Supabase project (claims.sql), reached
// only from here with the service key in this project's environment. The site works the same without it.
//
//   GET  /api/claim?name=Laura            {name, claimed_at}            is this name claimed, and when
//   GET  /api/claim  Authorization: Bearer <token>   {name, claimed_at, mine}   whose device this is
//   POST /api/claim  {name, code}         200 {name, token} | 401 wrong code (left) | 409 claimed | 429 slow down
'use strict';
const { hash, attempt } = require('./_claims');

const URL = process.env.SUPABASE_URL, KEY = process.env.SUPABASE_SERVICE_KEY;
const TABLE = '/rest/v1/assembly_claims';
const NAME = /^[A-Za-z0-9][\w .'-]{0,39}$/;                      // the record's own rule for a name
const q = s => encodeURIComponent(s);

async function db(path, init) {
  const r = await fetch(URL + TABLE + path, Object.assign({
    headers: { apikey: KEY, Authorization: 'Bearer ' + KEY, 'Content-Type': 'application/json',
               Prefer: 'return=representation' },
  }, init || {}));
  if (!r.ok) throw new Error('db ' + r.status);
  return r.json();
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  if (!URL || !KEY) return res.status(503).json({ error: 'not set up' });
  try {
    if (req.method === 'GET') {
      const tok = String(req.headers.authorization || '').replace(/^Bearer\s+/i, '');
      if (tok) {
        const rows = await db('?token_hash=eq.' + q(hash(tok)) + '&select=name,claimed_at');
        return rows.length ? res.status(200).json({ name: rows[0].name, claimed_at: rows[0].claimed_at, mine: true })
                           : res.status(401).json({ error: 'unknown token' });
      }
      const name = String((req.query && req.query.name) || '');
      if (!NAME.test(name)) return res.status(400).json({ error: 'bad name' });
      const rows = await db('?name=eq.' + q(name) + '&select=name,claimed_at');
      return rows.length ? res.status(200).json({ name, claimed_at: rows[0].claimed_at })
                         : res.status(404).json({ error: 'no such name' });
    }
    if (req.method !== 'POST') return res.status(405).json({ error: 'method' });
    const body = req.body && typeof req.body === 'object' ? req.body : {};
    const name = String(body.name || ''), code = String(body.code || '');
    if (!NAME.test(name) || code.length > 64) return res.status(400).json({ error: 'bad request' });
    const rows = await db('?name=eq.' + q(name) + '&select=name,code_hash,claimed_at,failed,failed_at');
    const out = attempt(rows[0], code);
    if (out.patch) {
      const patch = Object.assign({}, out.patch, out.patch.claimed_at ? { claimed_at: new Date().toISOString() } : {});
      // a claim writes only while the row is still unclaimed, so two devices racing cannot both win
      const done = await db('?name=eq.' + q(name) + (out.status === 200 ? '&claimed_at=is.null' : ''),
                            { method: 'PATCH', body: JSON.stringify(patch) });
      if (out.status === 200 && !done.length) return res.status(409).json({ error: 'claimed' });
    }
    return res.status(out.status).json(out.body);
  } catch (e) {
    console.error('claim', req.method, e.message);                // "db 404" and the like; no names, codes or tokens
    return res.status(502).json({ error: 'the record did not answer' });
  }
};
