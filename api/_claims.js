// The claim endpoint's pure part: hashing, and what one attempt does to one row. Kept out of the functions (a
// leading underscore: Vercel does not deploy it) so node test_api.js can run it without a database.
'use strict';
const crypto = require('crypto');

const LOCK = 5;                                                 // wrong codes in a run before wrong guesses are turned away
const PAUSE = 10 * 60 * 1000;                                   // a run ends after this long without a wrong code
const hash = s => crypto.createHash('sha256').update(String(s)).digest('hex');
const norm = code => String(code || '').toLowerCase().replace(/[^a-z0-9]/g, '');   // "ab12-cd34" and "AB12 CD34" agree
const same = (a, b) => a.length === b.length && crypto.timingSafeEqual(Buffer.from(a), Buffer.from(b));
const token = () => crypto.randomBytes(32).toString('hex');

// One attempt on one row: the answer to send, and the change to write (patch), if any. The right code always works,
// so nobody can lock a name out by guessing at it; only wrong guesses are slowed. A code is 16 characters of 31
// (about 79 bits), so slowing is for the log, not for safety: `failed` shows Z that someone is trying.
function attempt(row, code, now = Date.now()) {
  if (!row) return { status: 404, body: { error: 'no such name' } };
  if (row.claimed_at) return { status: 409, body: { error: 'claimed', claimed_at: row.claimed_at } };
  if (same(hash(norm(code)), row.code_hash)) {
    const t = token();
    return { status: 200, body: { name: row.name, token: t }, patch: { token_hash: hash(t), claimed_at: true, failed: 0 } };
  }
  const since = now - (row.failed_at ? Date.parse(row.failed_at) : 0);
  const run = since < PAUSE ? row.failed : 0;
  if (run >= LOCK) return { status: 429, body: { error: 'too many wrong codes', retry_after: Math.ceil((PAUSE - since) / 1000) } };
  return { status: 401, body: { error: 'wrong code', left: LOCK - run - 1 },
           patch: { failed: run + 1, failed_at: new Date(now).toISOString() } };
}

module.exports = { LOCK, PAUSE, hash, norm, attempt };
