// node test_claims.js: the weekly page's reading of a pasted chat (assets/claims.js), offline, on a made-up week.
'use strict';
const assert = require('assert');
const { parse, review, seenText, standing } = require('./assets/claims.js');

const data = {
  members: ['Ann', 'Bo', 'Cy', 'Di', 'Ed', 'Flo', 'Zed'],
  next: 4,
  votes: [{ subject: 'version 3', by: '2026-10-22' }],
  entries: [
    { kind: 'FACT', num: 1, writer: 'Zed', lines: 3, empty: true, results: [] },
    { kind: 'FACT', num: 2, writer: 'Zed', lines: 2, empty: false, results: [['Ann', '2026-10-13', 'HOLDS', [1, 2]]] },
    { kind: 'PROMISE', num: 3, writer: 'Zed', lines: 0, empty: true, results: [] },
  ],
};

const chat = `Ann, [16.10.26 14:02]
CHECK FACT 1 · HOLDS · lines 1,2,3 · Ann · 2026-10-16
Line 1: the payment is not there
Saw: none after 2026-09-14
Line 2: the balance is low
Saw: 11.125 SOL
Line 3: the old balance
Saw: 3.8712 SOL
New: the last payment out was at 18:02 UTC
Minutes: 12
I opened the link myself. No AI wrote this result.

Bo, [16.10.26 15:40]
CHECK FACT 1 | HOLDS | lines 1-3 | Bo | 2026-10-16
Saw: all three as Ann said
New: the account was made on 2026-07-08
I opened the link myself.

CHECK FACT 2 · DOESN’T HOLD · line 1 · Cy · 2026-10-17
Saw: a different amount
New: a second sale on 09-23
I opened the link myself.

CHECK FACT 2 · HOLDS · lines 1,2 · Bo · 2026-10-17
Saw: the amount
I opened the link myself.

CHECK FACT 1 · HOLDS · lines 1 · Zed · 2026-10-17
Saw: x
New: y
I opened the link myself.

CHECK FACT 2 · HOLDS · lines 1,2 · Ann · 2026-10-13
Saw: as before
New: as before
I opened the link myself.

VOTE YES · version 3 · Ann · 2026-10-16
VOTE YES · Version  3 · Bo · 2026-10-16
VOTE OBJECT · version 3 · Cy · 2026-10-17
Which line is wrong: rule 5
What would change my mind: a date
VOTE YES · version 3 · Cy · 2026-10-18
VOTE YES · version 3 · Di · 2026-10-19
VOTE OBJECT · version 3 · Ed · 2026-10-23
VOTE YES · version 3 · Stranger · 2026-10-19

ENTRY FACT 4 · Di · 2026-10-18
\`\`\`
  FACT 4. (Di, 2026-10-18)
    SAYS      Something.
\`\`\`
yes from me too`;

const p = parse(chat);
assert.strictEqual(p.checks.length, 6);
assert.strictEqual(p.votes.length, 7);
assert.deepStrictEqual(p.checks[1].lines, [1, 2, 3], 'a range, and "|" in place of "·"');
assert.strictEqual(p.checks[2].word, "DOESN'T HOLD", 'a phone\'s curly apostrophe');
assert.deepStrictEqual(p.entries[0].text, ['  FACT 4. (Di, 2026-10-18)', '    SAYS      Something.'], 'fences dropped');
assert.deepStrictEqual(p.unread.map((u) => u.text), ['Ann, [16.10.26 14:02]', 'Bo, [16.10.26 15:40]', 'yes from me too']);

const r = review(p, data, '2026-10-20');

// SEEN lines: two for fact 1, in the ledger's layout, the first replacing "nobody yet"
const one = r.add.find((a) => a.entry.num === 1);
assert.ok(one.lines[0].startsWith('    SEEN      - Ann, 2026-10-16: HOLDS on lines 1, 2, 3. Saw:'));
assert.ok(one.lines.every((l) => l.length <= 92), 'wrapped at 92');
assert.ok(one.lines.slice(1).some((l) => l.startsWith('              - Bo, 2026-10-16: HOLDS on lines 1, 2, 3.')));
assert.ok(one.lines.join(' ').replace(/\s+/g, ' ').includes('Saw: line 1, none after 2026-09-14; line 2, 11.125 SOL; line 3, 3.8712 SOL.'));

// rule 3: two members other than the writer, the same result on the same lines
assert.deepStrictEqual([one.closes.state, one.closes.by, one.closes.since], ['HOLDS', ['Ann', 'Bo'], '2026-10-16']);
const two = r.add.find((a) => a.entry.num === 2);
assert.strictEqual(two.closes, null, 'Cy says DOESN\'T HOLD on line 1 only: no agreement');
assert.deepStrictEqual(two.lines, ['              - Cy, 2026-10-17: DOESN\'T HOLD on line 1. Saw: a different amount. New: a',
  '                second sale on 09-23.']);

// held back for a person: no new detail, and the writer checking their own entry; the repeat of a filed line skipped
assert.deepStrictEqual(r.held.map((h) => h.post.who + ': ' + h.why.split(' ')[0]), ['Bo: it', 'Zed: Zed']);
assert.deepStrictEqual(r.already.map((c) => c.who), ['Ann']);

// rule 7: Cy's later yes replaces their objection; Ed voted late; a stranger does not count
const v = r.votes[0];
assert.deepStrictEqual([v.yes, v.object, v.passes], [['Ann', 'Bo', 'Cy', 'Di'], [], true]);
assert.deepStrictEqual([v.late, v.outsiders], [['Ed (2026-10-23)'], ['Stranger']]);

// the other way round (rule 6): Ann's filed line from 10-13 is before this paste, so it is not asked for
assert.deepStrictEqual(r.back, []);
assert.strictEqual(r.from, '2026-10-13');

// the SEEN form build.py reads back (test_build.py parses this same line)
assert.strictEqual(seenText({ who: 'Ann', date: '2026-10-20', word: 'HOLDS', lines: [1, 2], minutes: 1,
  saw: [{ line: 1, text: 'it.' }, { line: 2, text: 'that' }], fresh: 'a date' }),
  '- Ann, 2026-10-20: HOLDS on lines 1, 2. Saw: line 1, it; line 2, that. New: a date. 1 minute.');

// rules 3 and 4: the cases build.py standing() passes too (test_build.py), so the two copies cannot drift
const fx = require('./checks/states.json');
fx.cases.forEach((c) => {
  const got = standing(c.results, fx.writer, fx.members, c.start);
  delete got.groups;
  assert.deepStrictEqual(got, c.want, c.why);
});

// before adoption the paste above is the dry run, counted as if adopted; after it, a post before an entry's first
// day counts for nothing, so the same two HOLDS on fact 1 close nothing
const after = JSON.parse(JSON.stringify(data));
after.adopted = '2026-10-22';
after.entries.forEach((e) => { e.state = { state: 'OPEN', by: [], start: '2026-10-23' }; });
let ra = review(p, after, '2026-10-20');
assert.ok(!ra.add.some((a) => a.entry.num === 1), 'dated before the first day: held back, not copied');
assert.ok(ra.held.some((h) => h.post.who === 'Ann' && /dated before 2026-10-23/.test(h.why)));
after.entries.forEach((e) => { e.state.start = '2026-10-16'; });
assert.strictEqual(review(p, after, '2026-10-20').add.find((a) => a.entry.num === 1).closes.state, 'HOLDS');
after.entries[0].state = { state: 'WITHDRAWN', by: [], since: '2026-10-15', start: '2026-10-16' };   // only a promise can be,
ra = review(p, after, '2026-10-20');                                                                   // but the page asks no more
assert.ok(!ra.add.some((a) => a.entry.num === 1) && ra.held.some((h) => /withdrawn on 2026-10-15/.test(h.why)));

// Items: and Script: (ASSEMBLY_SPEC section 4) go into the SEEN item, and two samples of a line over many items, fact 4's
// 164 pages, close nothing (rule 3). The Script: line is agent.py's own, "via" and all.
const many = { members: data.members, next: 2, votes: [], adopted: '2026-10-22',
  entries: [{ kind: 'FACT', num: 1, writer: 'Zed', lines: 1, empty: true, results: [], state: { state: 'OPEN', by: [], start: '2026-10-23' } }] };
const samples = `CHECK FACT 1 · HOLDS · line 1 · Ann · 2026-10-24
Line 1: any page sits in a book the rotation does not predict
Saw: pages 1-20 as predicted
Items: 20 of 164
New: page 7 is short
Minutes: 30
Script: python checks/resolve.py fact4 by Zurandol said HOLDS on ledger d3e17658 at 2026-10-24T12:00Z via api.mainnet-beta.solana.com
I opened the link myself.

CHECK FACT 1 · HOLDS · line 1 · Bo · 2026-10-25
Saw: pages 100-119 as predicted
Items: 20 of 164
New: page 101 has a typo
I opened the link myself.`;
const ps = parse(samples);
assert.deepStrictEqual(ps.unread, []);
assert.deepStrictEqual([ps.checks[0].items, ps.checks[1].items], [[{ line: 1, n: 20, of: 164 }], [{ line: 0, n: 20, of: 164 }]]);
assert.deepStrictEqual(ps.checks[0].script, { name: 'python checks/resolve.py fact4', by: 'Zurandol', via: 'api.mainnet-beta.solana.com' });
assert.strictEqual(seenText(ps.checks[0]), '- Ann, 2026-10-24: HOLDS on line 1. Items: line 1, 20 of 164. Script: python ' +
  'checks/resolve.py fact4 by Zurandol via api.mainnet-beta.solana.com. Saw: line 1, pages 1-20 as predicted. New: page 7 ' +
  'is short. 30 minutes.');   // test_build.py reads this same line back (SLOTS)
const rs = review(ps, many, '2026-10-25');
assert.strictEqual(rs.add[0].posts.length, 2, 'a sample stays a SEEN line');
assert.strictEqual(rs.add[0].closes, null, 'two samples close nothing');
const all = review(parse(samples.replace(/Items: 20 of 164/g, 'Items: 164 of 164')), many, '2026-10-25');
assert.strictEqual(all.add[0].closes.state, 'HOLDS', 'the same two over all 164 pages close it');
assert.ok(seenText(all.add[0].posts[1]).includes(' Items: all 164. Saw:'));
const why = (t) => review(parse(t), many, '2026-10-25').held.map((h) => h.why);
assert.ok(/write Items: all 164/.test(why(samples.replace('Items: 20 of 164', 'Items: twenty pages'))[0]));
assert.ok(/write Items: all 164/.test(why(samples.replace('Items: 20 of 164', 'Items: 165 of 164'))[0]));
assert.ok(/whose script/.test(why(samples.replace(' by Zurandol', ''))[0]), 'a Script: line names whose script it is');

console.log('ok');

// A pasted line with a long run of spaces must not take quadratic time (the weekly page parses on every keystroke).
const t0 = Date.now();
parse('CHECK FACT 1 · HOLDS · lines 1' + ' '.repeat(200000) + 'x');
assert(Date.now() - t0 < 300, "parse took " + (Date.now() - t0) + " ms on a 200k-space line");
