// node test_claims.js: the weekly page's reading of a pasted chat (assets/claims.js), offline, on a made-up week after
// the worked version-5 ledger (checks/fixtures/ledger_v5_worked.txt), read through build.py as the page reads it.
'use strict';
const assert = require('assert');
const { execFileSync } = require('child_process');
const claims = require('./assets/claims.js');
const { parse, review, seenText } = claims;

const PY = "import json, sys; sys.path.insert(0, '.'); import build\n" +
  "t, s = build.sections(open('checks/fixtures/ledger_v5_worked.txt', encoding='utf-8').read())\n" +
  'print(json.dumps(build.ledger_dict(t, s, build.model(s))))';
function worked() {   // the weekly page's own data for the worked ledger, written by build.py
  for (const py of [process.env.PYTHON, 'python', 'python3'].filter(Boolean)) {
    try {
      return JSON.parse(execFileSync(py, ['-c', PY], { cwd: __dirname, encoding: 'utf8' }));
    } catch (e) {
      if (e.code !== 'ENOENT') throw e;
    }
  }
  throw new Error('test_claims.js reads the worked ledger through build.py: it needs python');
}
const data = worked(), NOW = '2026-11-09';

// Q2 answer 2 copies fact 5: its posters are CrypticK and Zurandol, and nobody has checked it yet.
const chat = `Merc, [09.11.26 10:02]
CHECK Q2 ANSWER 2 · HOLDS · lines 1,2 · Merc · 2026-11-09
Line 1: any of the eight words is on pages 1-24
Saw: none of the eight on 1-24
Items: all 24
Line 2: jest, hollow or laugh is on fewer than 40 of pages 25-164
Saw: jest on 61, hollow on 52, laugh on 44
Items: all 140
New: page 25 is in verse
I opened the link myself. No AI wrote this result.

CHECK Q2 ANSWER 2 | HOLDS | lines 1-2 | Ksizzle | 2026-11-09
Saw: as Merc said
Items: all 1
New: page 164 is the last
Script: python checks/fact5.py by Zurandol said HOLDS on ledger 220e9ee4 at 2026-11-09T12:00Z via febu-assembly.vercel.app
I opened the link myself.

CHECK Q2 ANSWER 2 • HOLDS • lines 1,2 • Laura • 2026-11-09
Saw: the same counts
Items: all 1
New: page 26 names the jester
I opened the link myself.

CHECK Q2 ANSWER 1 · DOESN’T HOLD · line 1 · Crypto Fish · 2026-11-09
Line 1: any of the eight words is on pages 1-24
Saw: "mocking" on page 3
Items: all 24
New: page 3 is short
I opened the link myself.

CHECK Q2 ANSWER 2 · HOLDS · lines 1,2 · CrypticK · 2026-11-09
Saw: x
Items: all 1
New: y
I opened the link myself.

CHECK Q2 ANSWER 2 · HOLDS · lines 1,2 · WitnesstoFebu · 2026-11-09
Saw: x
Items: all 1
I opened the link myself.

CHECK Q1 ANSWER 1 · HOLDS · lines 1,2,3 · Merc · 2026-11-01
Saw: as before
Items: all 1
New: as before
I opened the link myself.

PROPOSE P4 · Did the wallet that created $FEBU create another token in September? · Laura · 2026-11-09
YES P4 · Merc · 2026-11-09
YES P4 · Ksizzle · 2026-11-09
YES P4 · Laura · 2026-11-09
YES P4 · CrypticK · 2026-11-09
YES P9 · Merc · 2026-11-09

VOTE YES · Rule 9 wording · Merc · 2026-11-09
VOTE OBJECT · Rule 9 wording · CrypticK · 2026-11-09
Which line is wrong: the second
What would change my mind: a date
VOTE YES · Rule 9 wording · Stranger · 2026-11-09

ANSWER Q2 · Merc · 2026-11-09
\`\`\`
    ANSWER 3.   (Merc, 2026-11-09)
      SAYS      Something.
\`\`\`
ANSWER Q1 · Merc · 2026-11-09
\`\`\`
    ANSWER 2.   (Merc, 2026-11-09)
\`\`\`
yes from me too`;

const p = parse(chat);
assert.deepStrictEqual([p.checks.length, p.proposals.length, p.yeses.length, p.votes.length, p.answers.length],
  [7, 1, 5, 3, 2]);
assert.deepStrictEqual(p.checks[1].lines, [1, 2], 'a range, and "|" in place of "·"');
assert.strictEqual(p.checks[2].who, 'Laura', '"•" in place of "·"');
assert.strictEqual(p.checks[3].word, "DOESN'T HOLD", "a phone's curly apostrophe");
assert.deepStrictEqual(p.checks[0].items, [{ line: 1, n: 24, of: 24 }, { line: 2, n: 140, of: 140 }]);
assert.deepStrictEqual(p.checks[1].script, { name: 'python checks/fact5.py', by: 'Zurandol', via: 'febu-assembly.vercel.app' });
assert.deepStrictEqual(p.answers[0].text, ['    ANSWER 3.   (Merc, 2026-11-09)', '      SAYS      Something.'], 'fences dropped');
assert.deepStrictEqual(p.unread.map((u) => u.text), ['Merc, [09.11.26 10:02]', 'yes from me too']);

const r = review(p, data, NOW);

// SEEN items for Q2 answer 2 in the ledger's layout, the first in place of "nobody yet"
const two = r.add.find((g) => g.q.num === 2 && g.answer.num === 2);
assert.ok(two.lines[0].startsWith('      SEEN      - Merc, 2026-11-09: HOLDS on lines 1, 2. Items: line 1, all 24; line 2, all'));
assert.ok(two.lines.every((l) => l.length <= 92), 'wrapped at 92');
assert.ok(two.lines.slice(1).some((l) => l.startsWith('                - Ksizzle, 2026-11-09: HOLDS on lines 1, 2. Items: all 1.')));
assert.ok(two.lines.join(' ').replace(/\s+/g, ' ').includes('Saw: line 1, none of the eight on 1-24; line 2, jest on 61'));

// rule 4: Merc and Laura checked by hand; Ksizzle ran a script a poster (Zurandol) wrote, which is no Saw. Two of the
// three needed: it stays open.
assert.deepStrictEqual([two.before.state, two.after.state], ['OPEN', 'OPEN']);
assert.deepStrictEqual(two.samples, []);
const one = r.add.find((g) => g.q.num === 2 && g.answer.num === 1);
assert.deepStrictEqual(one.lines, ['                - Crypto Fish, 2026-11-09: DOESN\'T HOLD on line 1. Items: line 1, all 24.',
  '                  Saw: line 1, "mocking" on page 3. New: page 3 is short.']);

// held back for a person: a poster's check and one with nothing new; the repeat of a filed item skipped
assert.deepStrictEqual(r.held.filter((h) => h.post.type === 'check').map((h) => h.post.who + ': ' + h.why.split(' ').slice(0, 3).join(' ')),
  ['CrypticK: CrypticK posted or', 'WitnesstoFebu: it names nothing']);
assert.deepStrictEqual(r.already.map((c) => c.who), ['Merc']);

// rule 2: a new proposal is numbered from "The next proposal is P4."; the proposer's own yes and a yes for no proposal
// are held; with Q2 open, nothing opens
const prop = r.props.find((x) => x.prop.num === 4);
assert.ok(prop.prop.fresh && prop.lines[0].startsWith('  P4. Laura, 2026-11-09: Did the wallet'));
assert.ok(prop.lines.some((l) => l.includes('Yes: Merc 2026-11-09, Ksizzle 2026-11-09, CrypticK 2026-11-09.')));
assert.strictEqual(prop.prop.reach, '2026-11-09');
assert.strictEqual(r.next, 5);
assert.ok(r.held.some((h) => h.post.type === 'yes' && h.post.who === 'Laura' && /own yes/.test(h.why)));
assert.ok(r.held.some((h) => h.post.type === 'yes' && /no P9/.test(h.why)));
assert.deepStrictEqual(r.opens, []);

// rule 3: an answer goes under the open question, numbered in order; Q1 is closed
assert.deepStrictEqual(r.answers.map((a) => [a.q.num, a.num]), [[2, 3]]);
assert.ok(r.held.some((h) => h.post.type === 'answer' && /Q1 is not open \(CLOSED\)/.test(h.why)));

// rule 8: a new text's votes, the objection with its two lines; a stranger does not vote
const vote = r.votes.find((v) => v.subject === 'Rule 9 wording');
assert.ok(vote.fresh && vote.lines.length === 3 && vote.objections.length === 1);
assert.ok(r.held.some((h) => h.post.type === 'vote' && /only members vote/.test(h.why)));

// LAST POSTS: each member's last post on or before today
assert.ok(r.last.join(' ').startsWith('  - 2026-11-09: CrypticK 2026-11-09, Crypto Fish 2026-11-09, Ksizzle 2026-11-09,'));

// The control: Ksizzle's script is Ksizzle's own. Three members other than the posters, two by hand: Q2 answer 2 closes
// HOLDS today, Q2 closes, and P4, the first proposal with three yeses, opens as Q3 the same day (rule 2).
const own = review(parse(chat.replace('fact5.py by Zurandol said', 'fact5.py by Ksizzle said')), data, NOW);
const closed = own.add.find((g) => g.q.num === 2 && g.answer.num === 2).after;
assert.deepStrictEqual([closed.state, closed.since, closed.by], ['HOLDS', NOW, ['Ksizzle', 'Laura', 'Merc']]);
assert.deepStrictEqual(own.questions.map((x) => [x.q.num, x.now.state, x.now.since]), [[2, 'CLOSED', NOW]]);
assert.deepStrictEqual(own.opens.map((o) => [o.num, o.prop.num, o.day]), [[3, 4, NOW]]);
assert.ok(own.opens[0].lines[0] === '  Q3. (opened 2026-11-09, from P4)');
assert.deepStrictEqual(own.answers, [], 'Q2 closed today: no answer goes under it');

// A name is a name: "constructor", "__proto__" or "toString" in a post is no lookup on an object's prototype
const odd = review(parse('CHECK Q2 ANSWER 2 · HOLDS · lines 1,2 · constructor · 2026-11-09\nSaw: x\nItems: all 1\nNew: y\n' +
  'I opened the link myself.\n\nVOTE YES · Rule 9 wording · __proto__ · 2026-11-09\nYES P2 · toString · 2026-11-09'), data, NOW);
assert.deepStrictEqual([odd.add.length, odd.add[0].after.state], [1, 'OPEN']);
assert.ok(odd.held.some((h) => h.post.who === '__proto__' && /only members vote/.test(h.why)));
assert.ok(odd.held.some((h) => h.post.who === 'toString' && /only members say yes/.test(h.why)));
assert.ok(odd.last.join(' ').includes('Zurandol 2026-11-06'));

// A post dated on no calendar day, or after today (UTC), is held for a person, as lint I4 fails it in the file
const days = review(parse('VOTE YES · Rule 9 wording · Merc · 2026-13-45\n\nCHECK Q2 ANSWER 2 · HOLDS · lines 1,2 · Merc · ' +
  '2026-11-10\nSaw: x\nItems: all 1\nNew: y\nI opened the link myself.'), data, NOW);
assert.deepStrictEqual(days.held.map((h) => h.why).sort(), ['2026-13-45 is not a day on the calendar',
  'it is dated after today, 2026-11-09 (UTC)']);
assert.deepStrictEqual([days.add, days.votes.filter((v) => v.fresh)], [[], []]);

// An ANSWER post's header is who posted it (Posters): it must be the post's own name and day
const answerPost = (who, head) => 'ANSWER Q2 · ' + who + ' · 2026-11-09\n```\n' + head + '      SAYS      Something.\n```';
assert.strictEqual(review(parse(answerPost('Merc', '    ANSWER 3.   (Merc, 2026-11-09)\n')), data, NOW).answers.length, 1);
assert.ok(/its header names Merc, 2026-11-09, and the post is Laura's/.test(
  review(parse(answerPost('Laura', '    ANSWER 3.   (Merc, 2026-11-09)\n')), data, NOW).held[0].why));
assert.ok(/no header line/.test(review(parse(answerPost('Merc', '')), data, NOW).held[0].why));

// An address in a proposal: the page's data has it cut to 7 characters, as build.py clip does. A repost of it whole is
// the same proposal, and when it opens the page says to copy its question from the file, not the cut text.
const cut = JSON.parse(JSON.stringify(data)), p2 = cut.proposals[1];
p2.asks = 'Did ApWpkd8… buy $benchcoin?';
p2.yes = p2.yes.concat([['Ksizzle', '2026-11-08']]);   // Merc's P2: its third yes, while Q2 is open
const again = 'PROPOSE · Did ApWpkd8tpPTdTFNihoYuF5en8Y27TQn4LAQTvvmf8faG buy $benchcoin? · ' + p2.who + ' · ' + p2.date;
assert.deepStrictEqual(review(parse(again), cut, NOW).already.map((x) => x.type), ['propose']);
const opened = review(parse(chat.replace('fact5.py by Zurandol said', 'fact5.py by Ksizzle said')), cut, NOW).opens[0];
assert.strictEqual(opened.prop.num, 2);
assert.ok(opened.lines.join(' ').includes("copy P2's question here from PROPOSED QUESTIONS"), opened.lines);

// A sample (Items: 20 of 24) goes in as a SEEN item and counts toward nothing (rule 4)
const sample = review(parse(chat.replace('fact5.py by Zurandol said', 'fact5.py by Ksizzle said')
  .replace('Items: all 24', 'Items: 20 of 24')), data, NOW);
const s2 = sample.add.find((g) => g.q.num === 2 && g.answer.num === 2);
assert.deepStrictEqual([s2.samples, s2.after.state], [['Merc'], 'OPEN']);

// the SEEN form build.py reads back (test_build.py Seen reads this same line)
assert.strictEqual(seenText({ who: 'Ann', date: '2026-11-04', word: 'HOLDS', lines: [1],
  items: [{ line: 1, n: 20, of: 164 }], script: { name: 'python checks/resolve.py fact4', by: 'Zurandol', via: 'api.mainnet-beta.solana.com' },
  saw: [{ line: 1, text: 'pages.' }], fresh: 'page 7' }),
'- Ann, 2026-11-04: HOLDS on line 1. Items: line 1, 20 of 164. Script: python checks/resolve.py fact4 by Zurandol via ' +
  'api.mainnet-beta.solana.com. Saw: line 1, pages. New: page 7.');
const why = (t) => review(parse(t), data, NOW).held.map((h) => h.why);
const merc = chat.split('\n\n')[0].replace(/^Merc, \[.*\n/, '');
assert.ok(/write Items: all 164/.test(why(merc.replace('Items: all 24', 'Items: twenty pages'))[0]));
assert.ok(/write Items: all 164/.test(why(merc.replace('Items: all 24', 'Items: 25 of 24'))[0]));
assert.ok(/write Items: all 164/.test(why(merc.replace('Items: all 24', 'Items: 20 of 99999999999999999999999'))[0]),
  'a count JavaScript would print as 1e+23 cannot be read back from the file');
assert.ok(/whose script/.test(why(merc + '\nScript: python checks/fact5.py')[0]), 'a Script: line names whose script it is');
assert.ok(/whose script/.test(why(merc + '\nScripts: python checks/fact5.py by Bo')[0]), 'misspelt, it is no hand check');
assert.ok(/write Items: all 164/.test(why(merc.replace('Items: all 24', 'Items: all 0'))[0]), 'a count is 1 or more');

// rules 2, 4, 5 and 8: the cases build.py passes too (test_build.py States), so the two copies cannot drift
const fx = require('./checks/states.json');
const st = fx.standing, or = (c, k, all) => (k in c ? c[k] : all[k]);   // a case's own value, null included
st.cases.forEach((c) => {
  const got = claims.standing(c.results, or(c, 'posters', st), st.members, or(c, 'start', st), or(c, 'n', st), or(c, 'posts', st));
  assert.deepStrictEqual(got, c.want, c.why);
});
fx.questions.cases.forEach((c) => {
  const got = claims.questionState(fx.questions.opened, c.answers.map(([num, held]) => ({ num, state: { held } })), c.as_of);
  assert.deepStrictEqual(got, c.want, c.why);
});
fx.slot.cases.forEach((c) => {
  const on = 'adopted' in c ? c.adopted : fx.slot.adopted;
  const props = c.proposals.map(([num, who, date, yes]) => ({ num, who, date, yes }));
  props.forEach((x) => { x.reach = claims.reach(x, fx.slot.members, on); });
  assert.deepStrictEqual(claims.slot(props, c.frees, on), c.want, c.why);
});
fx.votes.cases.forEach((c) => {
  const got = claims.voteState({ posted: fx.votes.posted, votes: c.votes }, fx.votes.members, or(c, 'posts', fx.votes), c.as_of);
  assert.deepStrictEqual(got, c.want, c.why);
});

console.log('ok');

// A pasted line with a long run of spaces must not take quadratic time (the weekly page parses on every keystroke).
const t0 = Date.now();
parse('CHECK Q1 ANSWER 1 · HOLDS · lines 1' + ' '.repeat(200000) + 'x');
assert(Date.now() - t0 < 300, 'parse took ' + (Date.now() - t0) + ' ms on a 200k-space line');
const dots = '.'.repeat(200000) + 'x', t1 = Date.now();   // nor a long run of full stops, in a Script: or a Saw: line
review(parse('CHECK Q2 ANSWER 2 · HOLDS · line 1 · Merc · 2026-11-09\nSaw: a' + dots + '\nNew: b\nScript: a by ' + dots +
  '\nI opened the link myself.'), data, NOW);
assert(Date.now() - t1 < 300, 'review took ' + (Date.now() - t1) + ' ms on 200k full stops');
