// The claim endpoint's pure part: hashing, and what one attempt does to one row. Kept out of the functions (a
// leading underscore: Vercel does not deploy it) so node test_api.js can run it without a database.
'use strict';
const crypto = require('crypto');

const LOCK = 5;                                                 // wrong codes that lock a name until reissued
const hash = s => crypto.createHash('sha256').update(String(s)).digest('hex');
const norm = code => String(code || '').toLowerCase().replace(/[^a-z0-9]/g, '');   // "ab12-cd34" and "AB12 CD34" agree
const same = (a, b) => a.length === b.length && crypto.timingSafeEqual(Buffer.from(a), Buffer.from(b));
const token = () => crypto.randomBytes(32).toString('hex');

// One attempt on one row: the answer to send, and the change to write (patch), if any.
function attempt(row, code) {
  if (!row) return { status: 404, body: { error: 'no such name' } };
  if (row.claimed_at) return { status: 409, body: { error: 'claimed', claimed_at: row.claimed_at } };
  if (row.failed >= LOCK) return { status: 423, body: { error: 'locked' } };
  if (!same(hash(norm(code)), row.code_hash)) {
    return { status: 401, body: { error: 'wrong code', left: LOCK - row.failed - 1 }, patch: { failed: row.failed + 1 } };
  }
  const t = token();
  return { status: 200, body: { name: row.name, token: t }, patch: { token_hash: hash(t), claimed_at: true } };
}

module.exports = { LOCK, hash, norm, attempt };
