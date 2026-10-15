// The live record's pure part: reading entries and members from ledger.txt, rules 3 and 4, and what a second or a check
// must satisfy before it is written. Kept out of the function (a leading underscore: Vercel does not deploy it as one)
// so node test_entries.js can run it without a database. live/server.py is its local twin; keep the two in step.
'use strict';
const crypto = require('crypto');

const CANT_TELL_DAYS = 30;                                      // rule 4
const STRANGER_PER_ENTRY = 6;                                   // checks from outside the seven that one entry takes in all
const STRANGER_PER_DAY = 5;                                     // checks one source may post in 24 hours
const LONGEST = 1000;                                           // characters in one answer
const MOST_MINUTES = 600;
const RESULTS = { FACT: ['HOLDS', "DOESN'T HOLD"], PROMISE: ['KEPT', 'BROKEN'] };
const HANDLE = /^[A-Za-z0-9][A-Za-z0-9 ._'-]{1,39}$/;           // a stranger's name: plain ASCII, so no lookalike of a member's
// build.py's BANNED: notation that never goes on a public page
const BANNED = /GF\(3\)|\btrits?\b|(?<![\p{L}\p{N}_="'-])[-−]1(?!\d)/iu;
const isBanned = s => BANNED.test(s);

class Refused extends Error {
  // A post the rules turn away; the message is shown to the person as it is. 401: no claim, or one the table does not know.
  constructor(message, status) { super(message); this.status = status || 400; }
}

// ---------------------------------------------------------------------------------------------------------------
// ledger.txt in: the members and the entries. A port of build.py's reader (sections, entries, member_names) and
// live/server.py's read_ledger; test_entries.js runs both on the real ledger and compares.

const ENTRY = /^ {2}(FACT|PROMISE) (\d+)\.\s*(?:\((.*)\))?\s*$/;
const FIELD = /^([A-Z]+(?: [A-Z]+)?)(?: {2,}| (?=[a-z])|$)/;     // "SAYS      one", "IF BROKEN what"
const TAG = /\s{3,}(\([^()]*\)|\[[^\[\]]*\])\s*$/;               // "(changed 2026-10-13)" set off to the right
const HEADLINE = { FACT: 'SAYS', PROMISE: 'WILL' };
const DATE = /\d{4}-\d\d-\d\d/;
const indent = s => s.length - s.replace(/^ +/, '').length;
const short = heading => heading.split(/[(:.]/)[0].trim();

function sections(text) {
  const out = [];
  for (const raw of text.split('\n').slice(1)) {
    if (/^\S/.test(raw)) out.push([raw.trimEnd(), []]);          // a heading starts at the left edge
    else if (out.length) out[out.length - 1][1].push(raw);
  }
  return out;
}

function noTag(raw) {                                            // a continuation line, without the note set off to its right
  raw = raw.trimEnd();
  const m = TAG.exec(raw);
  return (m && (raw.slice(0, m.index).trim() || indent(raw) >= 40) ? raw.slice(0, m.index) : raw).trim();
}

// [{kind, num, who, fields: [[label, [text, ...]], ...]}] for the lines of the one section that holds entries
function parseEntries(body) {
  const out = [];
  let cur = null, fcol = null;
  for (const raw of body) {
    const m = ENTRY.exec(raw);
    if (m) { cur = { kind: m[1], num: Number(m[2]), who: m[3] || '', fields: [] }; out.push(cur); fcol = null; continue; }
    if (!raw.trim()) continue;
    if (cur && (fcol === null || indent(raw) >= fcol)) {
      if (fcol === null) fcol = indent(raw);
      const f = indent(raw) === fcol ? FIELD.exec(raw.slice(fcol)) : null;
      if (f) cur.fields.push([f[1], [raw.slice(fcol + f[0].length).trim()]]);
      else if (cur.fields.length) cur.fields[cur.fields.length - 1][1].push(noTag(raw));
      else throw new Error(`${cur.kind} ${cur.num}: a line before its first field`);
    } else {
      cur = null;                                                // a line between entries, not part of one
    }
  }
  return out;
}

function memberNames(secs) {
  const words = secs.find(([h]) => short(h) === 'WORDS USED HERE');
  const m = /\bMember\s{2,}(.+?)\.\s/.exec(words ? words[1].join(' ') : '');
  if (!m) throw new Error('WORDS USED HERE has no Member line');
  return m[1].split(',').map(n => n.trim());
}

// {members: [names, in the Member line's order], entries: [{num, kind, writer, posted, due, says, test}]}
function readLedger(raw) {
  const secs = sections(raw.replace(/\r\n/g, '\n').replace(/\n+$/, ''));
  const holding = secs.filter(([, body]) => body.some(r => ENTRY.test(r)));
  if (holding.length !== 1) throw new Error(`the ledger should have one section with entries in it; found ${holding.length}`);
  const entries = parseEntries(holding[0][1]).map(it => {
    const f = {};
    for (const [label, lines] of it.fields) f[label] = (f[label] ? f[label] + ' ' : '') + lines.filter(Boolean).join(' ');   // a label can repeat (CHANGED, SEEN): keep all
    let writer = it.who.split(',')[0].trim();
    if (writer === 'the group') {                                // rule 3: such an entry's writer is who proposed it
      const m = /([\p{L}\p{N}_]+) proposed it/u.exec(f.CHANGED || '');
      writer = m ? m[1] : writer;
    }
    const posted = DATE.exec(it.who), due = DATE.exec(f.BY || '');
    const says = f[HEADLINE[it.kind]];
    if (says === undefined) throw new Error(`${it.kind} ${it.num} has no ${HEADLINE[it.kind]} line`);
    return { num: it.num, kind: it.kind, writer, posted: posted && posted[0], due: due && due[0], says,
             test: f['WRONG IF'] || f['KNOWN BY'] || '' };
  });
  return { members: memberNames(secs), entries };
}

// ---------------------------------------------------------------------------------------------------------------
// Rules 3 and 4, and the two kinds of post.

// Rules 3 and 4 over one entry's checks, oldest first: [state, results, since]. state is OPEN, CLOSED, SPLIT (kept
// open or reopened: two people each posted a different result) or CAN'T TELL (split for 30 days). since is where the
// posts that count now begin: a reopened entry closes counting only posts made after it reopened. `at` is a Date.
function standing(writer, members, checks, at) {
  const ms = new Set(members.map(m => m.toLowerCase())), w = writer.toLowerCase();
  let state = 'OPEN', results = [], since = 0, splitAt = null;
  checks.forEach((c, i) => {
    const people = new Map();
    for (const p of checks.slice(since, i + 1)) {
      const who = p.who.toLowerCase();
      if (who === w) continue;
      if (!people.has(p.result)) people.set(p.result, new Set());
      people.get(p.result).add(who);
    }
    const two = [...people].filter(([, who]) => who.size >= 2).map(([r]) => r).sort();
    if (state === 'CLOSED') {
      const rival = two.find(r => r !== results[0]);
      if (rival !== undefined) { state = 'SPLIT'; results = results.concat(rival); since = i + 1; splitAt = c.at; }
    } else if (two.length >= 2) {
      if (state === 'OPEN') { state = 'SPLIT'; results = two; since = i + 1; splitAt = c.at; }
    } else {
      const closing = two.filter(r => [...people.get(r)].filter(n => ms.has(n)).length >= 2);
      if (closing.length) { state = 'CLOSED'; results = closing; since = i + 1; }
    }
  });
  if (state === 'SPLIT' && at - new Date(splitAt) >= CANT_TELL_DAYS * 864e5) state = "CAN'T TELL";
  return [state, results, since];
}

// One entry as the page shows it: the entry, its seconds and checks, and where it stands. The source never leaves.
function view(e, members, seconds, checks, at) {
  const shown = checks.map(({ via, ...c }) => c);
  const [state, results] = standing(e.writer, members, shown, at);
  return Object.assign({}, e, { seconds, checks: shown, state, results });
}

const words = v => (typeof v === 'string' ? v.split(/\s+/).filter(Boolean).join(' ') : '');
const fold = s => s.toLowerCase().replace(/[^a-z0-9]/g, '');

// The name a stranger posts under: plain ASCII, and not any member's, however it is spaced or capitalised.
function strangerName(raw, members) {
  const who = words(raw);
  if (!HANDLE.test(who)) throw new Refused("Pick a name to post under: 2 to 40 letters (A to Z), numbers, spaces or . _ ' -");
  if (members.some(m => fold(m) === fold(who))) {
    throw new Refused("That is a member's name. Members post from the device that claimed it. Pick another name.");
  }
  return who;
}

// A salted hash of where a post came from: enough to tell two posts came from one place, not to find the place.
const sourceOf = (address, salt) => crypto.createHash('sha256').update(salt + address).digest('hex').slice(0, 16);

function answer(body, key, label) {
  const s = words(body[key]);
  if (!s) throw new Refused(`${label} is empty.`);
  if (s.length > LONGEST) throw new Refused(`${label} is longer than ${LONGEST} characters.`);
  if (isBanned(s)) throw new Refused(`${label} has notation the ledger keeps off its pages. Say it in words.`);
  return s;
}

// The row for a second, or Refused. who: the member's name, from their claim.
function secondRow({ e, who, body, seconds, at }) {
  if (who.toLowerCase() === e.writer.toLowerCase()) throw new Refused('You wrote this entry. Someone else has to second it.');
  if (body.tests !== true) {
    throw new Refused('Tick the box to second it. If its test does not check what it says, say so in the chat instead.');
  }
  if (seconds.some(s => s.who.toLowerCase() === who.toLowerCase())) throw new Refused('You have already seconded this entry.');
  return { num: e.num, who, at: at.toISOString() };
}

// The row for a check, or Refused. member: the name from the poster's claim; for a stranger, member is null, `via` is
// the source hash and the name is the one typed. Rule 3 then does the rest: a name outside the Member line counts
// toward keeping open or reopening an entry and never toward closing it. seconds and checks are the entry's, oldest
// first (checks with their `via`); viaToday is how many checks this source has posted in the last day, on any entry.
function checkRow({ e, members, member, via, body, seconds, checks, viaToday, at }) {
  const who = via ? strangerName(body.who, members) : member;
  if (who.toLowerCase() === e.writer.toLowerCase()) throw new Refused('Nobody checks their own entry (rule 3).');
  if (e.kind === 'PROMISE' && !e.due) throw new Refused('This promise has no date yet, so nobody can check it.');
  if (e.kind === 'PROMISE' && at.toISOString().slice(0, 10) < e.due) {
    throw new Refused(`This promise can be checked on or after ${e.due}.`);
  }
  if (!RESULTS[e.kind].includes(body.result)) throw new Refused(`Pick a result: ${RESULTS[e.kind].join(' or ')}.`);
  const saw = answer(body, 'saw', 'What you saw');
  const tested = answer(body, 'tested', 'What you tested');
  const fresh = answer(body, 'new', 'The thing nobody has written yet');
  const minutes = body.minutes;
  if (!Number.isInteger(minutes) || minutes <= 0 || minutes > MOST_MINUTES) {
    throw new Refused(`Say how many minutes it took, from 1 to ${MOST_MINUTES}.`);
  }
  if (body.opened !== true) throw new Refused('Tick the box only if you opened the link yourself. An AI may help you look; it never posts.');
  if (!seconds.length) throw new Refused('This entry needs a second before anyone checks it.');
  const counting = checks.slice(standing(e.writer, members, checks, at)[2]);
  if (counting.some(c => c.who.toLowerCase() === who.toLowerCase())) {
    throw new Refused('You have already posted a check on this entry. If you see it differently now, say so in the chat.');
  }
  if (via) {
    if (counting.some(c => c.via === via)) {
      throw new Refused('A check has already come from your connection on this entry. If you see it differently now, say so in the chat.');
    }
    if (checks.filter(c => c.via).length >= STRANGER_PER_ENTRY) {
      throw new Refused(`This entry already has ${STRANGER_PER_ENTRY} checks from outside the seven. Say it in the chat.`);
    }
    if (viaToday >= STRANGER_PER_DAY) throw new Refused('That is as many checks as one connection posts in a day. Come back tomorrow.');
  }
  // ponytail: catches a copied "new thing" only word for word; a person still has to read it
  if (checks.some(c => c.new.toLowerCase() === fresh.toLowerCase())) {
    throw new Refused('Someone already posted that as their new thing. Name something nobody has written yet.');
  }
  // seq is this check's place on the entry; the table takes each place once, so a post that read the entry before
  // another landed cannot also land (the function answers 409)
  return { num: e.num, seq: checks.length + 1, who, result: body.result, saw, tested, new: fresh, minutes,
           at: at.toISOString(), via: via || null };
}

module.exports = { Refused, CANT_TELL_DAYS, STRANGER_PER_ENTRY, STRANGER_PER_DAY, isBanned, readLedger, standing, view, strangerName,
                   sourceOf, secondRow, checkRow };
