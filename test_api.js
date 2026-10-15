// node test_api.js: the claim endpoint, offline. The pure part (api/_claims.js) on made-up rows, then the handler
// (api/claim.js) against a fake database that answers like PostgREST.
'use strict';
const assert = require('assert');
const { hash, norm, attempt, LOCK, PAUSE } = require('./api/_claims.js');

const row = (over) => Object.assign({ name: 'Laura', code_hash: hash(norm('ab12-cd34-ef56-gh78')), claimed_at: null, failed: 0 }, over);

assert.equal(attempt(undefined, 'x').status, 404);
assert.equal(attempt(row({ claimed_at: '2026-10-16T10:00:00Z' }), 'ab12-cd34-ef56-gh78').status, 409);
const T = Date.parse('2026-10-16T10:00:00Z'), at = (ms) => new Date(T - ms).toISOString();
const wrong = attempt(row(), 'nope', T);
assert.equal(wrong.status, 401);
assert.deepEqual(wrong.patch, { failed: 1, failed_at: new Date(T).toISOString() });
assert.equal(wrong.body.left, LOCK - 1);
// a run of wrong codes turns wrong guesses away without a write, but never the right code (nobody can lock a name)
const paused = row({ failed: LOCK, failed_at: at(60 * 1000) });
const slow = attempt(paused, 'nope', T);
assert.deepEqual([slow.status, slow.patch, slow.body.retry_after], [429, undefined, (PAUSE - 60 * 1000) / 1000]);
assert.equal(attempt(paused, 'ab12-cd34-ef56-gh78', T).status, 200);
assert.equal(attempt(row({ failed: LOCK, failed_at: at(PAUSE + 1) }), 'nope', T).status, 401);   // a quiet stretch clears the run
assert.equal(attempt(row({ failed: LOCK, failed_at: at(PAUSE + 1) }), 'nope', T).body.left, LOCK - 1);
const ok = attempt(row(), 'AB12 CD34 EF56 GH78');           // case and separators do not matter
assert.equal(ok.status, 200);
assert.equal(ok.patch.token_hash, hash(ok.body.token));
assert.equal(ok.body.token.length, 64);

// the handler, with fetch replaced by a tiny PostgREST
process.env.SUPABASE_URL = 'https://x.supabase.co';
process.env.SUPABASE_SERVICE_KEY = 'service';
const table = [row()];
const calls = [];
global.fetch = async (url, init) => {
  calls.push([url, init && init.method || 'GET']);
  const u = new URL(url), name = (u.searchParams.get('name') || '').replace(/^eq\./, '');
  const tokenHash = (u.searchParams.get('token_hash') || '').replace(/^eq\./, '');
  let rows = table.filter(r => (name ? r.name === name : true) && (tokenHash ? r.token_hash === tokenHash : true));
  if (u.searchParams.get('claimed_at') === 'is.null') rows = rows.filter(r => !r.claimed_at);
  if (init && init.method === 'PATCH') rows.forEach(r => Object.assign(r, JSON.parse(init.body)));
  return { ok: true, status: 200, json: async () => rows.map(r => Object.assign({}, r)) };
};
const handler = require('./api/claim.js');
const run = (method, extra) => new Promise(resolve => {
  const res = { setHeader() {}, status(s) { this.s = s; return this; }, json(b) { resolve({ status: this.s, body: b }); } };
  handler(Object.assign({ method, headers: {}, query: {}, body: {} }, extra), res);
});
(async () => {
  assert.equal((await run('GET', { query: { name: 'Laura' } })).body.claimed_at, null);
  assert.equal((await run('GET', { query: { name: 'Nobody' } })).status, 404);
  assert.equal((await run('GET', { query: { name: '<b>' } })).status, 400);
  assert.equal((await run('POST', { body: { name: 'Laura', code: 'wrong' } })).status, 401);
  assert.equal(table[0].failed, 1);
  const won = await run('POST', { body: { name: 'Laura', code: 'ab12-cd34-ef56-gh78' } });
  assert.equal(won.status, 200);
  assert.ok(table[0].claimed_at && table[0].token_hash === hash(won.body.token));
  assert.equal((await run('POST', { body: { name: 'Laura', code: 'ab12-cd34-ef56-gh78' } })).status, 409);
  const me = await run('GET', { headers: { authorization: 'Bearer ' + won.body.token } });
  assert.deepEqual([me.status, me.body.name, me.body.mine], [200, 'Laura', true]);
  assert.equal((await run('GET', { headers: { authorization: 'Bearer nope' } })).status, 401);
  assert.equal((await run('DELETE', {})).status, 405);
  assert.ok(calls.every(([u]) => u.startsWith('https://x.supabase.co/rest/v1/assembly_claims')));
  console.log('ok');
})().catch(e => { console.error(e); process.exit(1); });
