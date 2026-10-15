// node test_entries.js: the live record on Vercel, offline. Rules 3 and 4 and the post rules (api/_record.js) on made-up
// posts, then the function (api/entries.js) against a fake database that answers like PostgREST, with fixed times.
// Port of live/test_live.py. The export and the SQLite triggers are not here: the export is still Python-only, and the
// triggers are in live.sql, which only a database can run. Also compares this reader with build.py's on the real
// ledger.txt when python is on the PATH.
'use strict';
const assert = require('assert');
const fs = require('fs');
const { execFileSync } = require('child_process');
const { hash } = require('./api/_claims.js');
const R = require('./api/_record.js');

const T0 = Date.parse('2026-10-15T12:00:00Z'), HOUR = 36e5, DAY = 864e5;
const MEMBERS = ['Ann', 'Bo', 'Cy'];

// ---- Rules 3 and 4 -------------------------------------------------------------------------------------------------
const posts = (...pairs) => pairs.map(([who, result], i) => ({ who, result, at: new Date(T0 + i * HOUR).toISOString() }));
const state = (pairs, at = T0 + DAY) => R.standing('Wes', MEMBERS, posts(...pairs), new Date(at)).slice(0, 2);
const H = 'HOLDS', N = "DOESN'T HOLD";

assert.deepEqual(state([]), ['OPEN', []]);                                                      // nobody yet is open
assert.deepEqual(state([['Ann', H], ['Bo', H]]), ['CLOSED', [H]]);                              // two members agreeing close it
assert.equal(state([['Ann', H], ['Stranger', H]])[0], 'OPEN');                                  // a member and someone else do not
assert.equal(state([['Wes', H], ['Ann', H]])[0], 'OPEN');                                       // the writer never counts
const split = [['Ann', H], ['X', N], ['Y', N], ['Bo', H]];
assert.deepEqual(state(split), ['SPLIT', [N, H]]);                                              // two and two keep it open with both
assert.equal(state(split, T0 + 3 * HOUR + 29 * DAY)[0], 'SPLIT');                               // split for 30 days is CAN'T TELL
assert.equal(state(split, T0 + 3 * HOUR + 30 * DAY)[0], "CAN'T TELL");
const reopened = [['Ann', H], ['Bo', H], ['X', N], ['Y', N]];
assert.deepEqual(state(reopened), ['SPLIT', [H, N]]);                                           // two rivals after closing reopen it
assert.equal(state([...reopened, ['Cy', H]])[0], 'SPLIT');                                      // and it closes on later posts only
assert.deepEqual(state([...reopened, ['Cy', H], ['Ann', H]]), ['CLOSED', [H]]);

// ---- The post rules, on one entry ------------------------------------------------------------------------------------
const promise = { num: 7, kind: 'PROMISE', writer: 'Wes', due: '2026-11-01' };
const kept = { who: 'Ann', result: 'KEPT', saw: 'a', tested: 'b', new: 'c', minutes: 3, opened: true };
const row = (e, at, extra) => R.checkRow(Object.assign({ e, members: MEMBERS, member: 'Ann', body: kept, seconds: [{ who: 'Bo' }],
  checks: [], viaToday: 0, at: new Date(at) }, extra));
assert.throws(() => row(promise, Date.parse('2026-10-31T23:00:00Z')), /on or after 2026-11-01/);   // a promise waits for its date
assert.equal(row(promise, Date.parse('2026-11-01T00:00:00Z')).seq, 1);
assert.throws(() => row(Object.assign({}, promise, { due: null }), T0), /no date yet/);
assert.throws(() => row({ num: 3, kind: 'FACT', writer: 'Wes', due: null }, T0), /Pick a result: HOLDS or DOESN'T HOLD/);

// The notation the ledger keeps off its pages, and the reader, against build.py's on the real ledger.txt
const banned = ['balance went -1', 'GF(3) field', 'a trit', '−1', '-1', 'step-1', 'x = -1', '-10', '1-1', 'won\'t -1.5', 'strait', '"-1"', 'a -1b'];
const ledger = fs.readFileSync('ledger.txt', 'utf8');
const read = R.readLedger(ledger);
assert.equal(read.members.length, 7);
assert.deepEqual(read.entries.map(e => e.num), [1, 2, 3, 4, 5, 6, 7, 8, 9]);
assert.deepEqual(read.entries.filter(e => e.kind === 'PROMISE').map(e => [e.num, e.writer, e.due]), [[7, 'Zurandol', null]]);   // "the group" is whoever proposed it
for (const py of ['python', 'python3']) {
  let got;
  try {
    got = JSON.parse(execFileSync(py, ['-I', '-c', [
      'import sys, json', 'sys.path.insert(0, "live")', 'import server', 'raw = server.build.raw_text(server.build.LEDGER).decode("utf-8")',
      'members, entries = server.read_ledger(raw.rstrip("\\n"))',
      'print(json.dumps({"members": members, "entries": entries, "banned": [bool(server.build.BANNED.search(s)) for s in json.loads(sys.argv[1])]}))',
    ].join('\n'), JSON.stringify(banned)], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }));
  } catch (e) { continue; }                                                                       // that python is not here
  assert.deepEqual(read, { members: got.members, entries: got.entries }, 'ledger.txt read differently by build.py');
  assert.deepEqual(banned.map(s => R.isBanned(s)), got.banned);
  console.log('reader and notation filter agree with build.py');
  break;
}

// ---- The function, against a fake PostgREST --------------------------------------------------------------------------
process.env.SUPABASE_URL = 'https://x.supabase.co';
process.env.SUPABASE_SERVICE_KEY = 'service';
const SALT = 'a-long-random-salt';
const claims = ['CrypticK', 'Crypto Fish', 'Ksizzle', 'Laura', 'Merc', 'WitnesstoFebu', 'Zurandol']
  .map(name => ({ name, token_hash: hash('tok-' + name), claimed_at: '2026-10-14T10:00:00Z' }));
const seconds = [], checks = [], calls = [];
const tables = { assembly_claims: claims, assembly_seconds: seconds, assembly_checks: checks };
const unique = { assembly_seconds: r => r.num + '|' + r.who.toLowerCase(), assembly_checks: r => r.num + '|' + r.seq };   // live.sql's indexes
let clock = T0, nextId = 1, claimsDown = false, beforePost = null;
Date.now = () => clock;

const stamped = r => (r.at ? Object.assign({}, r, { at: new Date(r.at).toISOString().replace(/\.\d+Z$/, '+00:00') }) : r);
global.fetch = async (url, init) => {
  const method = (init && init.method) || 'GET', u = new URL(url), table = u.pathname.replace('/rest/v1/', '');
  calls.push([url, method]);
  const reply = (status, body) => ({ ok: status < 300, status, json: async () => body });
  if (method === 'POST') {
    if (beforePost) { const f = beforePost; beforePost = null; f(); }
    const added = JSON.parse(init.body);
    if (tables[table].some(r => unique[table](r) === unique[table](added))) return reply(409, { code: '23505' });
    tables[table].push(Object.assign({ id: nextId++ }, added));
    return reply(201, [stamped(tables[table][tables[table].length - 1])]);
  }
  if (method !== 'GET') return reply(405, {});                                                    // rule 2: the tables refuse these too
  if (table === 'assembly_claims' && claimsDown) return reply(500, {});
  let rows = tables[table].filter(r => [...u.searchParams].every(([k, v]) => {
    if (['select', 'order', 'limit'].includes(k)) return true;
    const [op, ...rest] = v.split('.'), want = rest.join('.');
    return op === 'eq' ? String(r[k]) === want : op === 'gt' ? r[k] > want : false;
  }));
  if (u.searchParams.get('order') === 'seq') rows = rows.slice().sort((a, b) => a.seq - b.seq);
  if (u.searchParams.get('limit')) rows = rows.slice(0, Number(u.searchParams.get('limit')));
  return reply(200, rows.map(stamped));
};

const handler = require('./api/entries.js');
const run = (method, extra) => new Promise((resolve, reject) => {
  const res = { setHeader() {}, status(s) { this.s = s; return this; }, json(b) { resolve({ status: this.s, body: b }); } };
  Promise.resolve(handler(Object.assign({ method, headers: {}, query: {}, body: {} }, extra), res)).catch(reject);
});

const JSON_TYPE = { 'content-type': 'application/json' };
const member = name => Object.assign({ authorization: 'Bearer tok-' + name }, JSON_TYPE);
const send = (num, act, body, headers, at) => {
  clock = at === undefined ? T0 : at;
  return run('POST', { url: `/api/entries/${num}/${act}`, query: { num: String(num), act }, headers, body });
};
const second = (num, name, extra, at) => send(num, 'second', Object.assign({ tests: true }, extra), member(name), at);
const GOOD = who => ({ result: H, saw: 'the phrase, in the archived script', tested: 'the phrase is not in that copy',
                       new: 'new thing from ' + who, minutes: 4, opened: true });
const check = (num, name, extra, at) => send(num, 'check', Object.assign(GOOD(name), extra), member(name), at);
const stranger = (num, who, ip, extra, at) =>
  send(num, 'check', Object.assign(GOOD(who), { who }, extra), Object.assign({ 'x-forwarded-for': ip }, JSON_TYPE), at);
const done = (r, status = 201) => { assert.equal(r.status, status, JSON.stringify(r.body)); return r.body; };
const refused = (r, pattern, status = 400) => { assert.equal(r.status, status, JSON.stringify(r.body)); assert.match(r.body.error, pattern); };

const cases = [];
const test = (name, fn) => cases.push([name, fn]);
const reset = () => {
  seconds.length = checks.length = calls.length = 0;
  claimsDown = false; beforePost = null;
  process.env.ASSEMBLY_SALT = SALT;
  delete process.env.ASSEMBLY_STRANGERS;
};
const strangersOn = () => { process.env.ASSEMBLY_STRANGERS = '1'; };

test('the listing: every entry, the seven members, the sign-in flags, no source', async () => {
  const out = done(await run('GET', {}), 200);
  assert.deepEqual([out.entries.length, out.members.length, out.signin, out.strangers], [9, 7, true, false]);
  assert.deepEqual(out.entries[2].seconds.concat(out.entries[2].checks), []);
  assert.equal(out.entries[2].state, 'OPEN');
  strangersOn();
  assert.equal(done(await run('GET', {}), 200).strangers, true);
  delete process.env.ASSEMBLY_SALT;                                                               // no salt, no stranger lane
  assert.equal(done(await run('GET', {}), 200).strangers, false);
});

test('a second and checks: two members agreeing close it, and who seconded may check too', async () => {
  const s = done(await second(3, 'Laura'));
  assert.deepEqual([s.seconds.length, s.state], [1, 'OPEN']);
  assert.equal(done(await check(3, 'Ksizzle')).state, 'OPEN');
  assert.equal(done(await check(3, 'Merc', {}, T0 + HOUR)).state, 'CLOSED');
  const after = done(await check(3, 'Laura', {}, T0 + 2 * HOUR));
  assert.deepEqual([after.state, after.results, after.checks.length], ['CLOSED', [H], 3]);
  const listed = done(await run('GET', {}), 200).entries.find(e => e.num === 3);
  assert.deepEqual([listed.state, listed.checks.map(c => c.who)], ['CLOSED', ['Ksizzle', 'Merc', 'Laura']]);
  assert.deepEqual(checks.map(c => c.seq), [1, 2, 3]);
  assert.equal(checks[0].at, new Date(T0).toISOString());
});

test('what the rules turn away', async () => {
  refused(await second(3, 'Zurandol'), /You wrote this entry/);                                   // the writer seconding
  refused(await second(3, 'Laura', { tests: false }), /Tick the box/);                            // a second without the tick
  refused(await check(3, 'Laura'), /needs a second/);                                             // a check before any second
  refused(await check(7, 'Laura'), /no date yet/);                                                // a promise with no date
  done(await second(3, 'Laura'));
  refused(await check(3, 'Zurandol'), /own entry/);                                               // the writer checking
  refused(await check(3, 'Merc', { opened: false }), /opened the link yourself/);
  refused(await check(3, 'Merc', { minutes: 0 }), /minutes/);
  refused(await check(3, 'Merc', { minutes: 4.5 }), /minutes/);
  refused(await check(3, 'Merc', { result: 'KEPT' }), /Pick a result/);                           // a result for the other kind
  refused(await check(3, 'Merc', { saw: 'balance went -1' }), /notation/);
  refused(await check(3, 'Merc', { saw: ' \n ' }), /empty/);
  refused(await check(3, 'Merc', { saw: 'x'.repeat(1001) }), /longer than/);
  refused(await check(3, 'Merc', { saw: ['not', 'text'] }), /empty/);
  refused(await send(99, 'second', { tests: true }, member('Laura')), /no entry 99/);
  done(await check(3, 'Merc'));
  refused(await check(3, 'Merc', { new: 'something else' }), /already posted a check/);          // the same person twice
  refused(await second(3, 'Laura'), /already seconded/);
  refused(await check(3, 'Ksizzle', { new: 'NEW THING FROM MERC' }), /new thing/);                // a copied new thing
  assert.equal(seconds.length, 1);
  assert.equal(checks.length, 1);
});

test('nothing in the record is rewritten or removed: the function only ever reads and adds', async () => {
  done(await second(3, 'Laura'));
  done(await check(3, 'Merc'));
  done(await run('GET', {}), 200);
  assert.ok(calls.length > 0 && calls.every(([, m]) => m === 'GET' || m === 'POST'));
  assert.ok(calls.every(([u]) => u.startsWith('https://x.supabase.co/rest/v1/assembly_')));
});

test('two posts at the same moment: the table takes one place once, the second poster is told', async () => {
  done(await second(3, 'Laura'));
  beforePost = () => checks.push({ id: nextId++, num: 3, seq: 1, who: 'Merc', result: H, saw: 's', tested: 't', new: 'n', minutes: 1, at: new Date(T0).toISOString(), via: null });
  refused(await check(3, 'Ksizzle'), /same moment/, 409);
  assert.equal(checks.length, 1);
  done(await check(3, 'Ksizzle'));                                                                // reading again, it lands as place 2
  assert.deepEqual(checks.map(c => c.seq), [1, 2]);
  seconds.length = 0;
  beforePost = () => seconds.push({ id: nextId++, num: 3, who: 'laura', at: new Date(T0).toISOString() });
  refused(await second(3, 'Laura'), /already seconded/, 409);
});

test('who is posting comes from the claim, never from what was typed', async () => {
  const s = done(await send(3, 'second', { who: 'Merc', tests: true }, member('Laura')));
  assert.deepEqual(s.seconds.map(x => x.who), ['Laura']);
  const c = done(await send(3, 'check', Object.assign(GOOD('Ksizzle'), { who: 'Merc' }), member('Ksizzle')));
  assert.deepEqual(c.checks.map(x => x.who), ['Ksizzle']);
});

test('no claim, or a dead one, is a 401, and a dead one is never a stranger', async () => {
  for (const lane of [false, true]) {
    if (lane) strangersOn();
    refused(await send(3, 'second', { tests: true }, JSON_TYPE), /Claim your name/, 401);       // no header
    refused(await send(3, 'second', { tests: true }, Object.assign({ authorization: 'Bearer ' }, JSON_TYPE)), /Claim your name/, 401);
    refused(await send(3, 'check', GOOD('Rook'), Object.assign({ authorization: 'Bearer nope' }, JSON_TYPE)), /no claim, or it was reissued/, 401);
    refused(await send(3, 'check', GOOD('Rook'), Object.assign({ authorization: 'nope', 'x-forwarded-for': '203.0.113.5' }, JSON_TYPE)), /no claim/, 401);
  }
  delete process.env.ASSEMBLY_STRANGERS;
  refused(await send(3, 'check', Object.assign(GOOD('Rook'), { who: 'Rook' }), Object.assign({ 'x-forwarded-for': '203.0.113.5' }, JSON_TYPE)), /Claim your name/, 401);   // lane off
  assert.deepEqual([seconds.length, checks.length], [0, 0]);
});

test('a claim table that fails is refused, not trusted', async () => {
  strangersOn();
  claimsDown = true;
  const r = await send(3, 'second', { tests: true }, member('Laura'));
  assert.equal(r.status, 502);
  assert.equal((await send(3, 'check', GOOD('Rook'), Object.assign({ authorization: 'Bearer tok-Laura', 'x-forwarded-for': '203.0.113.5' }, JSON_TYPE))).status, 502);
  assert.deepEqual([seconds.length, checks.length], [0, 0]);
});

test('the request itself: method, address, type, size, shape, setup', async () => {
  assert.equal((await run('DELETE', {})).status, 405);
  assert.equal((await run('POST', { url: '/api/entries', headers: member('Laura'), body: {} })).status, 404);
  assert.equal((await run('POST', { url: '/api/entries/3/second', headers: member('Laura'), body: { tests: true } })).status, 201);   // no route query: the path will do
  assert.equal((await run('POST', { query: { num: '3', act: 'delete' }, headers: member('Laura'), body: {} })).status, 404);
  assert.equal((await run('POST', { query: { num: '3', act: 'check' }, headers: { authorization: 'Bearer tok-Laura', 'content-type': 'text/plain' }, body: 'x' })).status, 415);
  assert.equal((await run('POST', { query: { num: '3', act: 'check' }, headers: member('Laura'), body: ['a'] })).status, 400);
  assert.equal((await run('POST', { query: { num: '3', act: 'check' }, headers: member('Laura'), body: { saw: 'x'.repeat(20000) } })).status, 413);
  const url = process.env.SUPABASE_URL;
  delete process.env.SUPABASE_URL;
  assert.equal((await run('GET', {})).status, 503);
  assert.equal((await run('POST', { query: { num: '3', act: 'second' }, headers: member('Laura'), body: { tests: true } })).status, 503);
  process.env.SUPABASE_URL = url;
});

// The stranger lane: no claim, a check only, a name that is not a member's, and rule 3's limits
const close = async (num, result = H) => {
  done(await second(num, 'Laura'));
  done(await check(num, 'Merc', { result }));
  return done(await check(num, 'Ksizzle', { result }, T0 + HOUR));
};

test('strangers never close an entry', async () => {
  strangersOn();
  done(await second(3, 'Laura'));
  done(await stranger(3, 'Rook', '203.0.113.1'));
  assert.equal(done(await stranger(3, 'Pawn', '203.0.113.2')).state, 'OPEN');
  assert.equal(done(await check(3, 'Merc')).state, 'OPEN');                                       // one member with two strangers is still not two members
});

test('a stranger cannot second', async () => {
  strangersOn();
  refused(await send(3, 'second', { who: 'Rook', tests: true }, Object.assign({ 'x-forwarded-for': '203.0.113.1' }, JSON_TYPE)), /Claim your name/, 401);
});

test('two strangers reopen a closed entry', async () => {
  strangersOn();
  assert.equal((await close(3)).state, 'CLOSED');
  assert.equal(done(await stranger(3, 'Rook', '203.0.113.1', { result: N }, T0 + 2 * HOUR)).state, 'CLOSED');   // one is a NOTE, not a reopening
  assert.equal(done(await stranger(3, 'Pawn', '203.0.113.2', { result: N }, T0 + 3 * HOUR)).state, 'SPLIT');
});

test("a stranger cannot take a member's name", async () => {
  strangersOn();
  done(await second(3, 'Laura'));
  for (const who of ['Laura', 'laura', 'L a u r a', 'LAURA.', 'crypto-fish', 'Laurа', 'x']) {   // the last two: Cyrillic a, too short
    refused(await stranger(3, who, '203.0.113.1'), /name/);
  }
  assert.equal(checks.length, 0);
});

test('one source posts once per entry', async () => {
  strangersOn();
  done(await second(3, 'Laura'));
  done(await stranger(3, 'Rook', '203.0.113.1'));
  refused(await stranger(3, 'Rook2', '203.0.113.1'), /your connection/);                         // the same source under another name
  done(await stranger(3, 'Pawn', '203.0.113.2'));                                                 // another source is not held back
  done(await stranger(3, 'Knight', '198.51.100.7, 10.0.0.1'));                                    // the client is the first address
});

test('one source posts only so many a day', async () => {
  strangersOn();
  for (const n of [1, 2, 3, 4, 5, 6]) done(await second(n, 'Laura'));
  for (const n of [1, 2, 3, 4, 5]) done(await stranger(n, 'Day' + n, '203.0.113.9'));
  refused(await stranger(6, 'Late', '203.0.113.9'), /in a day/);
  done(await stranger(6, 'Late', '203.0.113.9', {}, T0 + DAY + 60000));
});

test('an entry takes only so many from outside', async () => {
  strangersOn();
  done(await second(3, 'Laura'));
  for (let n = 0; n < R.STRANGER_PER_ENTRY; n++) done(await stranger(3, 'Guest' + n, '203.0.113.' + (10 + n)));
  refused(await stranger(3, 'OneMore', '203.0.113.99'), /from outside the seven/);
});

test('a stranger needs somewhere to post from', async () => {
  strangersOn();
  done(await second(3, 'Laura'));
  refused(await send(3, 'check', Object.assign(GOOD('Rook'), { who: 'Rook' }), JSON_TYPE), /where it is posting from/);
});

test('the source never leaves the record', async () => {
  strangersOn();
  done(await second(3, 'Laura'));
  const out = done(await stranger(3, 'Rook', '203.0.113.77'));
  const listed = JSON.stringify(done(await run('GET', {}), 200));
  for (const text of [JSON.stringify(out), listed]) {
    assert.ok(!/"via"|203\.0\.113\.77/.test(text));
    assert.ok(!text.includes(checks[0].via));
  }
  assert.deepEqual([checks[0].via.length, checks[0].via === '203.0.113.77', checks[0].num], [16, false, 3]);
});

test('the source is a hash that depends on the address and the salt', () => {
  const a = R.sourceOf('203.0.113.5', SALT), b = R.sourceOf('203.0.113.6', SALT);
  assert.equal(a.length, 16);
  assert.notEqual(a, b);
  assert.notEqual(a, R.sourceOf('203.0.113.5', 'another salt'));
  assert.ok(!a.includes('203.0.113'));
});

(async () => {
  for (const [name, fn] of cases) {
    reset();
    try { await fn(); } catch (e) { e.message = name + ': ' + e.message; throw e; }
  }
  console.log('ok');
})().catch(e => { console.error(e); process.exit(1); });
