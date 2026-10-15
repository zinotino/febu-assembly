// node test_claims.js: the weekly page's reading of a pasted chat (assets/claims.js), offline, on a made-up week.
'use strict';
const assert = require('assert');
const { parse, review, seenText } = require('./assets/claims.js');

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
assert.deepStrictEqual([one.closes.word, one.closes.names], ['HOLDS', ['Ann', 'Bo']]);
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

console.log('ok');
