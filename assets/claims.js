/* claims.js -- what the ledger pages do in the browser: open a folded window a link points into, copy a hash, an
   address or a post with one tap, check that the files this site serves still have the SHA-256 the page prints, and
   the member flows: the check card and "your week" (front page), the weekly turn (weekly.html) and the answer form
   (write.html). Each flow writes text for a person to paste into the chat or into ledger.txt. Nothing here posts,
   stores or counts anything. The only requests go to this same site, for the files on the ledger page.
   The weekly page's reading of a chat (parse, review) needs no page: `node test_claims.js` runs it. */
(function () {
  'use strict';

  /* --- text the pages write -------------------------------------------------------------------------------------- */

  var WIDTH = 92;                               // ledger.txt's lines, as build.py and the README keep them
  var DOT = '  ·  ';                       // between the parts of a post's first line
  function pad(n) { return new Array(n + 1).join(' '); }
  var PAD4 = pad(4), PAD6 = pad(6), PAD7 = pad(7), PAD16 = pad(16), PAD18 = pad(18);
  var DAY = 864e5;

  function today() { return new Date().toISOString().slice(0, 10); }   // the ledger's dates are UTC
  function dec(s) { try { return decodeURIComponent(s); } catch (e) { return ''; } }   // a bad %-escape is no link
  var store = {   // this device's own memory: the name picked, unfinished check cards. Nothing leaves the page.
    get: function (k) { try { return localStorage.getItem('assembly:' + k); } catch (e) { return null; } },
    set: function (k, v) {
      try { if (v === null) localStorage.removeItem('assembly:' + k); else localStorage.setItem('assembly:' + k, v); } catch (e) {}
    }
  };

  function wrap(first, text, rest) {
    var lines = [], cur = first, empty = true;
    String(text).split(/\s+/).filter(Boolean).forEach(function (w) {
      if (!empty && cur.length + 1 + w.length > WIDTH) { lines.push(cur); cur = rest + w; }
      else cur += (empty ? '' : ' ') + w;
      empty = false;
    });
    return lines.concat(cur);
  }

  // s without the trailing characters in set; a regex like /[.]+$/ is quadratic on a long pasted run of them
  function chop(s, set) { var n = s.length; while (n && set.indexOf(s.charAt(n - 1)) >= 0) n--; return s.slice(0, n); }
  function stop(s) { s = String(s).trim(); return /[.!?]$/.test(s) ? s : s + '.'; }
  function norm(s) { return String(s).replace(/\s+/g, ' ').trim().toLowerCase(); }
  function cmp(a, b) { return a < b ? -1 : a > b ? 1 : 0; }
  function byDate(xs) { return xs.slice().sort(function (a, b) { return cmp(a.date, b.date) || a.at - b.at; }); }
  function assign(a, b) { var o = {}; [a, b].forEach(function (x) { Object.keys(x).forEach(function (k) { o[k] = x[k]; }); }); return o; }
  function has(xs, x) { return xs.indexOf(x) >= 0; }

  /* --- the weekly page's reading of a pasted chat ------------------------------------------------------------------
     A post's first line is the part a machine reads. The check card, the buttons under "your week" and the answer form
     write them:
       CHECK Q1 ANSWER 2 · HOLDS · lines 1,2 · Laura · 2026-11-02     then Line n: / Saw: / Items: / New: lines, and
                                                                      Script: <name> by <author> if a script ran
       PROPOSE P4 · the question, in one sentence · Laura · 2026-11-02
       YES P4 · Laura · 2026-11-03
       VOTE YES · rule 4 wording · Laura · 2026-11-03                 an objection adds two lines saying why
       ANSWER Q2 · Laura · 2026-11-04                                 then the answer, as the ledger lays it out
     "|" or "•" work in place of "·", for anyone typing one on a phone. A blank line ends a post. Every other line is
     handed back to be read by a person. */

  var SEP = '\\s*[\\u00b7|\\u2022]\\s*', PART = '([^\\u00b7|\\u2022]+?)', ON = '(\\d{4}-\\d\\d-\\d\\d)\\s*$';
  var CHECK = new RegExp('\\bCHECK\\s+Q\\s*(\\d+)\\s+ANSWER\\s+(\\d+)' + SEP + "(HOLDS|DOESN'?T\\s+HOLD|KEPT|BROKEN)" +
                         '(?:' + SEP + 'lines?\\s*(\\d[\\d\\s,and-]*?))?' + SEP + PART + SEP + ON, 'i');
  var VOTE = new RegExp('\\bVOTE\\s+(YES|OBJECT)' + SEP + PART + SEP + PART + SEP + ON, 'i');
  var PROPOSE = new RegExp('\\bPROPOSE(?:\\s+P\\s*(\\d+))?' + SEP + PART + SEP + PART + SEP + ON, 'i');
  var YES = new RegExp('\\bYES\\s+P\\s*(\\d+)' + SEP + PART + SEP + ON, 'i');
  var ANSWER = new RegExp('\\bANSWER\\s+Q\\s*(\\d+)' + SEP + PART + SEP + ON, 'i');
  var BOTH = ["DOESN'T HOLD", 'HOLDS'];

  function numbers(s) {   // "1,2,3", "1, 2 and 3", "1-3"
    var out = [];
    String(s || '').replace(/(\d+)(?:\s*-\s*(\d+))?/g, function (_, a, b) {
      for (var n = +a; n <= +(b || a) && n - a < 50; n++) if (out.indexOf(n) < 0) out.push(n);
    });
    return out.sort(function (x, y) { return x - y; });
  }

  function parse(text) {
    var out = { checks: [], proposals: [], yeses: [], votes: [], answers: [], unread: [] }, cur = null;
    String(text).replace(/\r\n?/g, '\n').split('\n').forEach(function (raw, i) {
      var s = raw.replace(/[‘’]/g, "'").replace(/\s+/g, ' ').trim(), m;   // one space: the patterns stay linear
      if (!s) { cur = null; return; }
      if ((m = s.match(CHECK))) {
        out.checks.push(cur = { type: 'check', at: i + 1, q: +m[1], a: +m[2], lines: numbers(m[4]),
          word: m[3].toUpperCase().replace(/DOESN'?T\s+HOLD/, "DOESN'T HOLD"), who: m[5].trim(), date: m[6], saw: [],
          fresh: '', opened: false, line: 0, items: [], script: null });
      } else if ((m = s.match(VOTE))) {
        out.votes.push(cur = { type: 'vote', at: i + 1, say: m[1].toUpperCase(), subject: m[2].trim(), who: m[3].trim(),
          date: m[4], why: [] });
      } else if ((m = s.match(PROPOSE))) {
        out.proposals.push(cur = { type: 'propose', at: i + 1, said: m[1] ? +m[1] : null, asks: m[2].trim(),
          who: m[3].trim(), date: m[4] });
      } else if ((m = s.match(YES))) {
        out.yeses.push(cur = { type: 'yes', at: i + 1, num: +m[1], who: m[2].trim(), date: m[3] });
      } else if ((m = s.match(ANSWER))) {
        out.answers.push(cur = { type: 'answer', at: i + 1, q: +m[1], who: m[2].trim(), date: m[3], text: [] });
      } else if (!(cur && more(cur, s, raw))) {
        out.unread.push({ at: i + 1, text: raw.trim() });
      }
    });
    return out;
  }

  function more(cur, s, raw) {   // a line of the post above it, or not
    var m;
    if (cur.type === 'answer') {   // to its closing ``` (or a blank line, if the chat dropped the fences)
      if (cur.fences > 1) return false;
      if (/^`{3}/.test(s)) cur.fences = (cur.fences || 0) + 1;
      else cur.text.push(raw.replace(/\s+$/, ''));
      return true;
    }
    if (cur.type === 'vote') {
      if (!/^(which line is wrong|what would change my mind)\b/i.test(s)) return false;
      cur.why.push(s);
      return true;
    }
    if (cur.type !== 'check') return false;
    if ((m = s.match(/^line\s+(\d+)\s*:/i))) { cur.line = +m[1]; return true; }
    if ((m = s.match(/^saw\s*:\s*(.*)$/i))) { cur.saw.push({ line: cur.line, text: m[1].trim() }); return true; }
    if ((m = s.match(/^new\s*:\s*(.*)$/i))) { cur.fresh = m[1].trim(); return true; }
    if ((m = s.match(/^items?\s*:\s*(.*)$/i))) { cur.items.push(itemsOf(cur.line, m[1])); return true; }
    if ((m = s.match(/^script\s*:\s*(.*)$/i))) { cur.script = scriptOf(m[1]); return true; }
    if (/^i opened the link/i.test(s)) { cur.opened = true; return true; }
    return false;
  }

  // "Items: all 164" or "Items: 20 of 164", under the Line n: it counts for (Result: only "all" counts toward HOLDS)
  function itemsOf(line, text) {
    var m = String(text).trim().match(/^(?:all\s+(\d{1,9})|(\d{1,9})\s+of\s+(\d{1,9}))\.?$/i);   // 9 digits: the count reads back as written
    return m && +(m[2] || m[1]) <= +(m[3] || m[1]) ? { line: line, n: +(m[2] || m[1]), of: +(m[3] || m[1]) }
      : { line: line, bad: String(text).trim() };
  }
  // "Script: python checks/x.py by Ann said HOLDS on ledger 1a2b3c4d at 2026-10-23T12:00Z via host", as agent.py writes
  // it: the name, whose script it is, and where it read from are kept; the rest is that run's own. Split, not one
  // regex, so a long pasted line stays linear.
  function scriptOf(text) {
    var s = String(text).trim(), by = s.indexOf(' by '), via = null;
    if (by < 1) return { bad: s };
    var who = s.slice(by + 4), v = who.lastIndexOf(' via ');
    if (v >= 0) { via = chop(who.slice(v + 5), '.'); who = who.slice(0, v); }
    if (who.indexOf(' said ') >= 0) who = who.slice(0, who.indexOf(' said '));
    who = chop(who, '.').trim();
    if (!who || /[:;,]/.test(who) || (via !== null && !/^\S+$/.test(via))) return { bad: s };
    return { name: s.slice(0, by), by: who, via: via || null };
  }

  function same(a, b) { return a.join(',') === b.join(','); }
  function linesText(ls) { return ls.length ? ' on line' + (ls.length > 1 ? 's ' : ' ') + ls.join(', ') : ''; }
  function answerName(q, a) { return 'Q' + q + ' answer ' + a; }

  function trouble(c, q, a, data) {   // why a CHECK post cannot go in as it stands, or ''
    if (!q) return 'the file has no Q' + c.q;
    if (!a) return 'Q' + c.q + ' has no answer ' + c.a + ' in the file' +
      (c.a > q.answers.length ? ' yet: add the answer first, then its checks' : '');
    var name = answerName(c.q, c.a);
    if (!has(BOTH, c.word)) return 'a result is HOLDS or DOESN\'T HOLD (Result)';
    if (has(a.posters, c.who)) return c.who + ' posted or changed ' + name + ', so their result counts for nothing (rule 4)';
    if (data.adopted && !(a.start && c.date >= a.start)) {
      return 'it is dated before ' + (a.start ? a.start + ', the first day ' + name + "'s results count" :
        'any day ' + name + "'s results count") + ', so it counts for nothing (lint I4)';
    }
    if (!c.lines.length) return 'it names no WRONG IF lines';
    var bad = c.lines.filter(function (n) { return n < 1 || n > a.lines; });
    if (bad.length) return name + ' has ' + a.lines + ' WRONG IF line' + (a.lines === 1 ? '' : 's') + ', and the post names ' + bad.join(', ');
    if (!c.saw.some(function (s) { return s.text; })) return 'it does not say what they saw';
    var odd = c.items.filter(function (i) { return i.bad !== undefined; })[0];
    if (odd) return 'its Items: line says "' + odd.bad + '"; write Items: all 164, or Items: 20 of 164';
    if (c.script && c.script.bad !== undefined) return 'its Script: line does not say whose script it is: Script: <name> by <author>';
    if (!c.fresh) return 'it names nothing new on the page (HOW TO CHECK AN ANSWER, step 3)';
    if (!c.opened) return 'it does not say they opened the link themselves (Saw)';
    return '';
  }

  function seenText(c) {   // build.py reads this back (SEEN_ITEM): keep the part up to Saw: as it is
    var saw = c.saw.filter(function (s) { return s.text; }).map(function (s) {
      return (s.line ? 'line ' + s.line + ', ' : '') + chop(s.text, ' .;');   // parse made all whitespace one space
    });
    var items = (c.items || []).filter(function (i) { return i.bad === undefined; }).map(function (i) {
      return (i.line ? 'line ' + i.line + ', ' : '') + (i.n === i.of ? 'all ' + i.of : i.n + ' of ' + i.of);
    }), sc = c.script && c.script.bad === undefined ? c.script : null;
    return '- ' + c.who + ', ' + c.date + ': ' + c.word + linesText(c.lines) + '.' +
      (items.length ? ' Items: ' + items.join('; ') + '.' : '') +
      (sc ? ' Script: ' + sc.name + ' by ' + sc.by + (sc.via ? ' via ' + sc.via : '') + '.' : '') + ' Saw: ' + stop(saw.join('; ')) +
      ' New: ' + stop(c.fresh);
  }

  function resultOf(c) {   // a CHECK post as build.py results() reads its SEEN item back
    var sc = c.script && c.script.bad === undefined ? c.script : null;
    return [c.who, c.date, c.word, c.lines, c.items.filter(function (i) { return i.bad === undefined; })
      .map(function (i) { return [i.line, i.n, i.of]; }), sc ? [sc.name, sc.by, sc.via] : null];
  }

  /* --- rules 2, 4, 5 and 8, as build.py writes them: checks/states.json holds the cases both copies must pass ----- */

  var DAYS = 30, ACTIVE_DAYS = 90;   // rule 5; WORDS USED HERE, Member
  function daysAfter(d, n) {   // stops at 9999-12-31, as build.py days_after does
    var s = new Date(Date.parse(d + 'T00:00:00Z') + n * DAY).toISOString();
    return s.charAt(0) === '+' ? '9999-12-31' : s.slice(0, 10);
  }
  function realDay(d) {   // Date.parse takes 2026-02-30 as 03-02; build.py does not
    var t = Date.parse(d + 'T00:00:00Z');
    return /^\d{4}-\d\d-\d\d$/.test(d) && d.slice(0, 4) !== '0000' && !isNaN(t) && new Date(t).toISOString().slice(0, 10) === d;
  }
  function range(n) { var out = []; for (var i = 1; i <= n; i++) out.push(i); return out; }
  function keys(o) { return Object.keys(o); }
  function lineKeys(o) { return keys(o).map(Number).sort(function (a, b) { return a - b; }); }

  function active(posts, name, day) {   // a post dated in the 90 days up to and including day
    var first = daysAfter(day, 1 - ACTIVE_DAYS);
    return (posts[name] || []).some(function (d) { return first <= d && d <= day; });
  }

  function full(lines, items, n) {   // a HOLDS on every WRONG IF line with "all" for each (Result)
    var every = range(n), alls = items.filter(function (i) { return i[1] === i[2]; }).map(function (i) { return i[0]; });
    var set = lines.filter(function (x, j, a) { return a.indexOf(x) === j; }).sort(function (a, b) { return a - b; });
    return n > 0 && same(set, every) && items.every(function (i) { return i[1] === i[2]; }) &&
      (has(alls, 0) || every.every(function (l) { return has(alls, l); }));
  }

  function standing(found, posters, members, start, n, posts) {
    var out = { state: 'OPEN', lines: [], since: null, by: [], both: [], held: null }, dated = {}, holds = {}, wrong = {};
    keys(posts || {}).forEach(function (k) { dated[k] = posts[k].slice(); });
    found.forEach(function (r) { if (realDay(r[1])) (dated[r[0]] = dated[r[0]] || []).push(r[1]); });
    var every = range(n), poster = function (x) { return has(posters, x); };
    var rs = found.filter(function (r) { return start && realDay(r[1]) && r[1] >= start; })
      .sort(function (a, b) { return cmp(a[1], b[1]); });   // stable: the file's order within a day
    for (var i = 0; i < rs.length; i++) {
      var name = rs[i][0], date = rs[i][1], word = rs[i][2], lines = rs[i][3], script = rs[i][5];
      if (poster(name) || (script && poster(script[1])) || (out.both.length && date <= out.since)) continue;
      var hand = !script, hit = lines.filter(function (l) { return has(every, l); });
      if (word === 'HOLDS' && full(lines, rs[i][4] || [], n)) holds[name] = holds[name] || hand;
      else if (word === "DOESN'T HOLD" && hit.length) {
        hit.forEach(function (l) { var by = wrong[l] = wrong[l] || {}; by[name] = by[name] || hand; });
      } else continue;                                                   // a sample, or no result here: a SEEN item
      var pair = lineKeys(wrong).filter(function (l) { return keys(wrong[l]).length >= 2; });
      if (out.state !== 'OPEN') {
        if (out.state === 'HOLDS' ? pair.length : keys(holds).length >= 2) {   // reopened (rule 5)
          out = assign(out, { state: 'OPEN', lines: [], since: date, by: [], both: BOTH.slice() });
          holds = {}; wrong = {};
        }
        continue;
      }
      if (keys(holds).length >= 2 && pair.some(function (l) {   // kept open (rule 5)
        return keys(holds).concat(keys(wrong[l]).filter(function (x) { return !(x in holds); })).length >= 4;
      })) {
        out = assign(out, { since: date, both: BOTH.slice() });
        holds = {}; wrong = {};
        continue;
      }
      var others = members.filter(function (m) { return !poster(m) && active(dated, m, date); });
      var need = others.length >= 4 ? 3 : Math.max(2, others.length);
      var ok = function (ns) {
        return keys(ns).filter(function (m) { return has(members, m) && !poster(m) && active(dated, m, date); }).sort();
      };
      var closes = function (ns) { var got = ok(ns); return got.length >= need && got.some(function (m) { return ns[m]; }); };
      var shut = lineKeys(wrong).filter(function (l) { return closes(wrong[l]); });
      if (closes(holds)) {
        out = assign(out, { state: 'HOLDS', lines: every.slice(), since: date, by: ok(holds), both: [], held: out.held || date });
      } else if (shut.length) {
        out = assign(out, { state: "DOESN'T HOLD", lines: shut, since: date, by: ok(wrong[shut[0]]), both: [] });
      } else continue;
      holds = {}; wrong = {};
    }
    return out;
  }

  function questionState(opened, answers, asOf) {   // rule 5: CLOSED, CAN'T TELL after its 30 days, or OPEN
    var until = opened ? daysAfter(opened, DAYS) : null, out = { state: 'OPEN', since: null, until: until, answer: null };
    var held = answers.filter(function (a) { return a.state.held; }).map(function (a) { return [a.state.held, a.num]; })
      .sort(function (x, y) { return cmp(x[0], y[0]) || x[1] - y[1]; })[0];
    if (!until) return out;
    if (held && held[0] <= until) return assign(out, { state: 'CLOSED', since: held[0], answer: held[1] });
    if (asOf && asOf > until) return assign(out, { state: "CAN'T TELL", since: daysAfter(until, 1) });
    return out;
  }
  function freed(st) { return st.state === 'CLOSED' || st.state === "CAN'T TELL" ? st.since : null; }

  function reach(p, members, adopted) {   // rule 2: the day of the third yes from another member, counted from adoption
    var got = [], ys = p.yes.slice().sort(function (a, b) { return cmp(a[1], b[1]); });
    for (var i = 0; i < ys.length; i++) {
      var name = ys[i][0], date = ys[i][1];
      if (adopted && realDay(date) && date >= (adopted > p.date ? adopted : p.date) && has(members, name) &&
          name !== p.who && !has(got, name)) {
        got.push(name);
        if (got.length === 3) return date;
      }
    }
    return null;
  }

  function slot(props, frees, adopted) {   // rule 2 in order: [[proposal, the day it opens]], the first for Q1
    var seq = [], free = adopted, used = {};
    while (free) {
      var ready = props.filter(function (p) { return p.reach && !used[p.num]; }).map(function (p) { return [p.reach, p.num]; })
        .sort(function (x, y) { return cmp(x[0], y[0]) || x[1] - y[1]; });
      if (!ready.length) break;
      seq.push([ready[0][1], ready[0][0] > free ? ready[0][0] : free]);
      used[ready[0][1]] = true;
      free = seq.length <= frees.length ? frees[seq.length - 1] : null;
    }
    return seq;
  }

  function voteState(v, members, posts, asOf) {   // rule 8, from the VOTES section alone
    var out = { passed: null, yes: [], object: [] };
    var first = realDay(v.posted) ? daysAfter(v.posted, 7) : null;
    if (!first || !asOf || asOf < first) return out;
    var p = {}, days = {};
    keys(posts).forEach(function (k) { p[k] = posts[k].slice(); });
    v.votes.forEach(function (x) { if (realDay(x[1])) (p[x[0]] = p[x[0]] || []).push(x[1]); });   // a vote is a post
    days[first] = 1;
    keys(p).forEach(function (k) { p[k].forEach(function (d) { days[d] = days[daysAfter(d, ACTIVE_DAYS)] = 1; }); });
    var order = v.votes.slice().sort(function (a, b) { return cmp(a[1], b[1]); }), list = keys(days).sort();
    for (var i = 0; i < list.length; i++) {
      var day = list[i], latest = {};
      if (day < first || day > asOf) continue;
      order.forEach(function (x) { if (x[1] <= day) latest[x[0]] = x[2]; });
      var act = members.filter(function (m) { return active(p, m, day); });
      out = { passed: null, yes: act.filter(function (m) { return latest[m] === 'YES'; }),
        object: act.filter(function (m) { return latest[m] === 'OBJECT'; }) };
      if (out.yes.length >= (act.length >= 5 ? 4 : Math.max(2, act.length)) && out.object.length <= 1) {
        return assign(out, { passed: day });
      }
    }
    return out;
  }

  /* --- the weekly turn: what a pasted week adds to the file ---------------------------------------------------- */

  function review(p, data, now) {
    var out = { add: [], held: [], already: [], answers: [], props: [], opens: [], votes: [], back: [], last: [],
      unread: p.unread, counts: { checks: p.checks.length, proposals: p.proposals.length, yeses: p.yeses.length,
        votes: p.votes.length, answers: p.answers.length } };
    var members = data.members, qs = {}, posts = {};
    data.questions.forEach(function (q) { qs[q.num] = q; });
    keys(data.posts).forEach(function (k) { posts[k] = data.posts[k].slice(); });
    [].concat(p.checks, p.proposals, p.yeses, p.votes, p.answers).forEach(function (x) {   // this week's posts (Member)
      if (realDay(x.date) && x.date <= now) (posts[x.who] = posts[x.who] || []).push(x.date);
    });

    // CHECK posts: SEEN items to add, and where each answer stands after them (rules 4 and 5)
    byDate(p.checks).forEach(function (c) {
      var q = qs[c.q], a = q && q.answers.filter(function (x) { return x.num === c.a; })[0], why = trouble(c, q, a, data);
      if (why) return out.held.push({ post: c, why: why });
      if (a.results.some(function (r) { return r[0] === c.who && r[1] === c.date && r[2] === c.word && same(r[3], c.lines); })) {
        return out.already.push(c);
      }
      var g = out.add.filter(function (x) { return x.answer === a; })[0];
      if (!g) out.add.push(g = { q: q, answer: a, posts: [] });
      g.posts.push(c);
    });
    out.add.forEach(function (g) {
      var a = g.answer, start = data.adopted ? a.start : null;
      g.lines = [];
      g.posts.forEach(function (c, i) {
        g.lines = g.lines.concat(wrap(i === 0 && a.empty ? PAD6 + 'SEEN' + PAD6 : PAD16, seenText(c), PAD18));
      });
      g.before = standing(a.results, a.posters, members, start, a.lines, data.posts);
      g.after = standing(a.results.concat(g.posts.map(resultOf)), a.posters, members, start, a.lines, posts);
      g.moved = g.after.state !== g.before.state || g.after.since !== g.before.since;
      g.samples = g.posts.filter(function (c) { return c.word === 'HOLDS' && !full(c.lines, resultOf(c)[4], a.lines); })
        .map(function (c) { return c.who; });
      g.outsiders = g.posts.filter(function (c) { return !has(members, c.who); }).map(function (c) { return c.who; });
    });
    var states = data.questions.map(function (q) {
      return questionState(q.opened, q.answers.map(function (a) {
        var g = out.add.filter(function (x) { return x.answer === a; })[0];
        return { num: a.num, state: g ? g.after : a.state };
      }), now);
    });
    out.questions = data.questions.map(function (q, i) { return { q: q, was: q.state, now: states[i] }; })
      .filter(function (x) { return x.was.state !== x.now.state; });

    // ANSWER posts: under the open question only (rule 3), numbered in the order posted
    var counts = {};
    byDate(p.answers).forEach(function (n) {
      var q = qs[n.q], st = q && states[data.questions.indexOf(q)];
      if (!q || st.state !== 'OPEN') {
        return out.held.push({ post: n, why: q ? 'Q' + n.q + ' is not open (' + st.state + '), and answers go under the open question (rule 3)'
          : 'the file has no Q' + n.q });
      }
      counts[q.num] = (counts[q.num] || q.answers.length) + 1;
      var said = (n.text.join(' ').match(/\bANSWER\s+(\d+)\./) || [])[1];
      out.answers.push({ post: n, q: q, num: counts[q.num], renumber: said && +said !== counts[q.num] ? +said : null });
    });

    // PROPOSE and YES posts: new proposals numbered in the order posted, every yes, and what rule 2 opens
    var props = data.proposals.map(function (x) {
      return assign(x, { yes: x.yes.map(function (y) { return y.slice(); }), added: [], fresh: false });
    });
    var claimed = {}, next = data.next.proposal;
    byDate(p.proposals).forEach(function (n) {
      if (!has(members, n.who)) return out.held.push({ post: n, why: 'only members propose (rule 2)' });
      if (props.some(function (x) { return x.who === n.who && x.date === n.date && norm(x.asks) === norm(n.asks); })) {
        return out.already.push(n);
      }
      var x = { num: next++, who: n.who, date: n.date, asks: n.asks, yes: [], opened: null, added: [], fresh: true, post: n };
      if (n.said && !(n.said in claimed)) claimed[n.said] = x.num;
      props.push(x);
    });
    byDate(p.yeses).forEach(function (y) {
      var num = y.num in claimed ? claimed[y.num] : y.num, x = props.filter(function (z) { return z.num === num; })[0];
      var why = !x ? 'the file has no P' + y.num + ', and no proposal in what you pasted is numbered P' + y.num
        : !has(members, y.who) ? 'only members say yes (rule 2)'
          : y.who === x.who ? y.who + ' proposed P' + x.num + ', and a proposer\'s own yes counts for nothing (rule 2)'
            : x.opened ? 'P' + x.num + ' opened as Q' + x.opened + ' already' : '';
      if (why) return out.held.push({ post: y, why: why });
      if (x.yes.some(function (z) { return z[0] === y.who && z[1] === y.date; })) return out.already.push(y);
      x.yes.push([y.who, y.date]);
      x.added.push(y);
    });
    props.forEach(function (x) { x.reach = reach(x, members, data.adopted); });
    out.props = props.filter(function (x) { return x.fresh || x.added.length; }).map(function (x) {
      var yes = x.yes.length ? wrap(PAD7 + 'Yes: ', x.yes.map(function (z) { return z[0] + ' ' + z[1]; }).join(', ') + '.', PAD7) : [];
      return { prop: x, lines: (x.fresh ? wrap('  P' + x.num + '. ' + x.who + ', ' + x.date + ': ', x.asks, PAD7) : []).concat(yes),
        had: !x.fresh && data.proposals.filter(function (z) { return z.num === x.num; })[0].yes.length > 0 };
    });
    out.next = next;
    var seq = slot(props, states.map(freed), data.adopted);
    seq.slice(data.questions.length).forEach(function (s, i) {
      var x = props.filter(function (z) { return z.num === s[0]; })[0], num = data.questions.length + i + 1;
      if (s[1] > now) return;
      out.opens.push({ num: num, prop: x, day: s[1],
        lines: ['  Q' + num + '. (opened ' + s[1] + ', from P' + x.num + ')'].concat(wrap(PAD4 + 'ASKS' + pad(8), x.asks, PAD16)) });
    });

    // VOTE posts: the VOTES items to add, and the count under rule 8 as of today
    var subjects = data.votes.map(function (v) { return assign(v, { votes: v.votes.slice(), add: [], fresh: false }); });
    byDate(p.votes).forEach(function (v) {
      if (!has(members, v.who)) return out.held.push({ post: v, why: 'only members vote (rule 8)' });
      var t = subjects.filter(function (s) { return norm(s.subject) === norm(v.subject); })[0];
      if (!t) subjects.push(t = { subject: v.subject, posted: null, votes: [], add: [], fresh: true });
      if (t.votes.some(function (x) { return x[0] === v.who && x[1] === v.date && x[2] === v.say; })) return out.already.push(v);
      t.votes.push([v.who, v.date, v.say]);
      t.add.push(v);
    });
    out.votes = subjects.filter(function (t) { return t.add.length || !t.passed; }).map(function (t) {
      var lines = [].concat.apply([], t.add.map(function (v) {
        return wrap(PAD4 + '- ' + v.who + ', ' + v.date + ': ', v.say === 'YES' ? 'YES.' : 'OBJECT. ' + v.why.join(' '), PAD6);
      }));
      var from = t.posted || t.votes.map(function (x) { return x[1]; }).sort()[0];   // a new text: from its first vote
      return { subject: t.subject, fresh: t.fresh, lines: lines, posted: from, count: voteState({ posted: from, votes: t.votes }, members, posts, now),
        objections: t.add.filter(function (v) { return v.say === 'OBJECT'; }) };
    });

    // LAST POSTS: one line for this turn, each member's last post on or before today (rule 7)
    var row = data.last ? data.last[1] : {};
    out.last = wrap('  - ' + now + ': ', members.map(function (m) {
      var ds = (posts[m] || []).concat(row[m] ? [row[m]] : []).filter(function (d) { return d <= now; }).sort();
      return m + ' ' + (ds.length ? ds[ds.length - 1] : 'none');
    }).join(', ') + '.', PAD4);

    // the other way round (rule 7): items in the file dated in the pasted week with no post in it
    var dates = [].concat(p.checks, p.proposals, p.yeses, p.votes).map(function (x) { return x.date; }).sort();
    out.from = dates[0] || null;
    if (out.from) {
      data.questions.forEach(function (q) {
        q.answers.forEach(function (a) {
          a.results.forEach(function (r) {
            if (r[1] >= out.from && !p.checks.some(function (c) { return c.q === q.num && c.a === a.num && c.who === r[0] && c.date === r[1]; })) {
              out.back.push(answerName(q.num, a.num) + ': SEEN ' + r[0] + ', ' + r[1] + ', ' + r[2]);
            }
          });
        });
      });
      data.proposals.forEach(function (x) {
        if (x.date >= out.from && !p.proposals.some(function (n) { return n.who === x.who && n.date === x.date; })) {
          out.back.push('P' + x.num + ': proposed by ' + x.who + ', ' + x.date);
        }
        x.yes.forEach(function (y) {
          if (y[1] >= out.from && !p.yeses.some(function (n) { return n.who === y[0] && n.date === y[1]; })) {
            out.back.push('P' + x.num + ': yes from ' + y[0] + ', ' + y[1]);
          }
        });
      });
      data.votes.forEach(function (v) {
        v.votes.forEach(function (x) {
          if (x[1] >= out.from && !p.votes.some(function (n) { return norm(n.subject) === norm(v.subject) && n.who === x[0] && n.date === x[1]; })) {
            out.back.push(v.subject + ': ' + x[2] + ' from ' + x[0] + ', ' + x[1]);
          }
        });
      });
    }
    return out;
  }

  if (typeof document === 'undefined') {   // under node, for test_claims.js
    module.exports = { parse: parse, review: review, wrap: wrap, seenText: seenText, standing: standing, full: full,
      active: active, questionState: questionState, reach: reach, slot: slot, voteState: voteState };
    return;
  }

  /* --- every page ---------------------------------------------------------------------------------------------- */

  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function each(sel, fn, root) { [].forEach.call((root || document).querySelectorAll(sel), fn); }

  // The list of every entry starts open on a wide screen and folded on a phone.
  if (window.matchMedia && matchMedia('(min-width: 41em)').matches) {
    each('details[data-open-wide]', function (d) { d.open = true; });
  }

  // A link to something inside a folded window opens the window; a link to a check card opens the card.
  function reveal() {
    var id = location.hash.length > 1 && dec(location.hash.slice(1)), t = id && document.getElementById(id);
    if (!t) return;
    if (t.classList.contains('cc')) openCard(t, true);
    for (var d = t; d; d = d.parentElement) if (d.tagName === 'DETAILS') d.open = true;
    (t.closest('.pick') || t).scrollIntoView();
  }
  window.addEventListener('hashchange', reveal);

  // Hashes and addresses in the text copy with one tap.
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('code.tok');
    if (!t || String(window.getSelection()) || !navigator.clipboard) return;
    navigator.clipboard.writeText(t.textContent).then(function () {
      t.classList.add('copied');
      setTimeout(function () { t.classList.remove('copied'); }, 900);
    }, function () {});
  });

  // A "copy" button puts its post on the clipboard, with today's date where it says {today}.
  function copyText(text) {
    function viaBox() {   // copy out of a temporary text box: older browsers, or a page the clipboard API refuses
      return new Promise(function (ok, no) {
        var box = document.createElement('textarea'), done = false;
        box.value = text;
        box.setAttribute('readonly', '');
        box.style.position = 'fixed';
        box.style.opacity = '0';
        document.body.appendChild(box);
        box.select();
        try { done = document.execCommand('copy'); } catch (err) { done = false; }
        document.body.removeChild(box);
        return done ? ok() : no();
      });
    }
    return navigator.clipboard && window.isSecureContext ? navigator.clipboard.writeText(text).catch(viaBox) : viaBox();
  }
  each('button.copy', function (b) { b.setAttribute('aria-live', 'polite'); });
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('button.copy');
    if (!b || b.disabled || b.classList.contains('copied')) return;
    var label = b.textContent, text = b.dataset.copy.replace(/\{today\}/g, today());
    copyText(text).then(function () {
      b.classList.add('copied');
      b.textContent = 'Copied';
      setTimeout(function () { b.classList.remove('copied'); b.textContent = label; }, 1500);
    }, function () { window.prompt('Copy this post:', text); });
  });

  // A post shown as the chat will show it, its first line (the part the weekly page reads) set apart.
  function showPost(pre, text) {
    var lines = text.split('\n');
    pre.textContent = '';
    pre.appendChild(el('span', 'first', lines[0]));
    if (lines.length > 1) pre.appendChild(document.createTextNode(lines.slice(1).join('\n')));
  }

  // "Still needed: ..." under a post, and its Copy button waiting until nothing is.
  function needs(p, buttons, missing, ready) {
    p.textContent = missing.length ? 'Still needed: ' + missing.join('; ') + '.' : ready;
    p.classList.toggle('ok', !missing.length);
    buttons.forEach(function (b) { b.disabled = missing.length > 0; });
  }

  function nameOf(root) {   // the name picked, or typed under "someone else"
    var who = root.querySelector('.who'), other = root.querySelector('.other');
    other.hidden = who.value !== '*';
    return (who.value === '*' ? other.value : who.value).trim();
  }

  /* --- front page: the check card ------------------------------------------------------------------------------- */

  function openCard(card, on) {
    card.hidden = !on;
    var b = document.querySelector('.cc-open[aria-controls="' + card.id + '"]');
    if (!b) return;
    b.setAttribute('aria-expanded', String(on));
    b.textContent = on ? 'Close the check' : 'Check it here';
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.cc-open');
    if (b) openCard($(b.getAttribute('aria-controls')), b.getAttribute('aria-expanded') !== 'true');
  });

  each('.cc', function (card) {
    var q = card.dataset.q, a = card.dataset.a, n = +card.dataset.lines, copy = card.querySelector('.cc-copy');
    var posters = (card.dataset.posters || '').split('|').filter(Boolean);
    copy.classList.add('copy');
    function write() {
      var ticked = [].filter.call(card.querySelectorAll('.ln-on'), function (b) { return b.checked; });
      each('.ln-on', function (b) {
        var li = b.closest('li');
        li.querySelector('.saw').hidden = li.querySelector('.items').hidden = !b.checked;
      }, card);
      var name = nameOf(card), res = card.querySelector('input[type=radio]:checked');
      var fresh = card.querySelector('.new').value.trim(), opened = card.querySelector('.opened').checked;
      var missing = [], blank = false, odd = false, noItems = false, found = [];
      var head = ['CHECK Q' + q + ' ANSWER ' + a, res ? res.value : '?',
        'lines ' + (ticked.map(function (b) { return b.value; }).join(',') || '?')];
      var post = [head.concat(name || '?', today()).join(DOT)];
      ticked.forEach(function (b) {
        var li = b.closest('li'), saw = li.querySelector('.saw').value.trim(), items = li.querySelector('.items').value.trim();
        var it = itemsOf(+b.value, items);
        blank = blank || !saw;
        noItems = noItems || !items;
        odd = odd || (!!items && it.bad !== undefined);
        if (items && it.bad === undefined) found.push([it.line, it.n, it.of]);
        post.push('Line ' + b.value + ': ' + li.querySelector('.t').textContent, 'Saw: ' + (saw || '?'));
        if (items) post.push('Items: ' + items);
      });
      post.push('New: ' + (fresh || '?'));
      if (opened) post.push('I opened the link myself. No AI wrote this result.');
      if (!ticked.length) missing.push('tick the WRONG IF lines you tested');
      else if (blank) missing.push('what you saw on each line you ticked');
      if (noItems) missing.push('how many of its items you opened, on each line you ticked: "all 1", "all 164" or "20 of 164"');
      else if (odd) missing.push('the items you opened as "all 164" or "20 of 164"');
      if (!fresh) missing.push('one thing on the page that is new');
      if (!res) missing.push('your result');
      if (!name) missing.push('your name');
      else if (has(posters, name)) missing.push('a checker who did not post or change this answer (rule 4)');
      if (!opened) missing.push('a tick to say you opened the link yourself');
      var lines = ticked.map(function (b) { return +b.value; });
      var part = res && res.value === 'HOLDS' && !full(lines, found, n);   // a SEEN item that counts toward nothing
      showPost(card.querySelector('.post'), post.join('\n'));
      copy.dataset.copy = post.join('\n');
      needs(card.querySelector('.need'), [copy], missing, part
        ? 'Ready, but this HOLDS counts toward closing nothing: a HOLDS names every WRONG IF line with "all" for each ' +
          '(Result). It still goes in the file as what you saw.'
        : 'Ready. Copy it and paste it in the chat.');
    }
    var key = 'draft5:' + q + ':' + a, fields = card.querySelectorAll('input, select');
    var isTick = function (f) { return f.type === 'checkbox' || f.type === 'radio'; };
    var keep = function (e) {   // an unfinished card survives a reload, until its post is copied
      if (e && !e.isTrusted) return;   // the name picked under "your week" arrives by a made event: not a draft
      store.set(key, JSON.stringify([].map.call(fields, function (f) { return isTick(f) ? f.checked : f.value; })));
    };
    var draft = store.get(key);
    if (draft) {
      try {
        var filled = false;
        JSON.parse(draft).forEach(function (v, i) {
          var f = fields[i];
          if (!f) return;
          if (isTick(f)) f.checked = !!v; else f.value = v;
          if (!f.classList.contains('who') && (v === true || (typeof v === 'string' && v.trim()))) filled = true;
        });
        if (filled) openCard(card, true);
      } catch (err) { store.set(key, null); }
    }
    card.addEventListener('input', write);
    card.addEventListener('change', write);
    card.addEventListener('input', keep);
    card.addEventListener('change', keep);
    copy.addEventListener('click', function () { store.set(key, null); });
    write();
  });

  /* --- front page: your week ------------------------------------------------------------------------------------- */

  var next = $('next');
  if (next) {
    var turn = next.querySelector('.turn'), order = turn.dataset.order.split('|'), from = turn.dataset.from, me = '';
    var iso = function (t) { return new Date(t).toISOString().slice(0, 10); };
    var week = function () {   // rule 7: a week each, in Member order, counted from the first date in STATUS
      var days = Math.floor((Date.parse(today()) - Date.parse(from)) / DAY);
      if (!from || !(days >= 0)) return null;
      var w = Math.floor(days / 7), start = Date.parse(from) + w * 7 * DAY;
      return { w: w, who: order[w % order.length], after: order[(w + 1) % order.length], start: iso(start), end: iso(start + 6 * DAY) };
    };
    var daysLeft = function (d) { return Math.round((Date.parse(d) - Date.parse(today())) / DAY); };
    var left = function (n) { return n < 0 ? 'closed' : n === 0 ? 'today' : n + ' day' + (n === 1 ? '' : 's') + ' left'; };
    each('[data-due]', function (t) { t.insertAdjacentText('beforeend', ' (' + left(daysLeft(t.dataset.due)) + ')'); });
    var post = $('due-post'), copyBtn = post && post.parentNode.querySelector('button.copy');
    var fill = function (text, t) {   // the reminder's dates: days left, and this week's turn
      return text.replace(/\{days\}/g, post.dataset.by ? left(daysLeft(post.dataset.by)) : '')
        .replace(/\{turn\}/g, t ? t.who : 'see the site').replace(/\{turnend\}/g, t ? t.end : 'the end of the week')
        .replace(/\{next\}/g, t ? t.after : 'the next in order');
    };
    var showTurn = function () {
      var t = week();
      if (t) {
        turn.querySelector('.turn-now').textContent = 'This week, ' + t.start + ' to ' + t.end + ': ' + t.who +
          '. Next week: ' + t.after + '. A turn not done by the end of its week passes to the next member. Weeks are ' +
          'counted from ' + from + ', the date in STATUS, in Member order.';
      }
      each('.due-turn', function (s) { if (t) s.textContent = t.who + ', to ' + t.end; });
      each('.turn-me', function (p) {   // each member's own week: this one, or k weeks on
        if (!t) return;
        var k = ((order.indexOf(p.dataset.name) - t.w % order.length) + order.length) % order.length;
        var s = Date.parse(t.start) + k * 7 * DAY, chip = next.querySelector('.turn-chip[data-name="' + p.dataset.name + '"]');
        p.textContent = k ? 'Yours in ' + k + ' week' + (k === 1 ? '' : 's') + ': ' + iso(s) + ' to ' + iso(s + 6 * DAY) + '.'
          : 'Yours this week, to ' + t.end + '.';
        if (chip) { chip.textContent = k ? 'in ' + k + ' week' + (k === 1 ? '' : 's') : 'this week: you'; chip.classList.toggle('you', !k); }
      });
      each('.turn-you', function (p) { p.hidden = !(t && me === t.who); }, next);
      if (post) { post.textContent = fill(post.dataset.text || (post.dataset.text = post.textContent), t).replace(/\{today\}/g, today()); }
      if (copyBtn) { copyBtn.dataset.copy = fill(copyBtn.dataset.text || (copyBtn.dataset.text = copyBtn.dataset.copy), t); }
    };
    next.addEventListener('change', function (e) {
      if (e.target.name !== 'me') return;
      me = e.target.value;
      store.set('me', me);
      each('.moves', function (p) { p.hidden = p.dataset.who !== me; }, next);
      next.querySelector('.moves-none').hidden = true;
      each('.cc .who', function (s) {   // the check cards start from the name picked here
        if (s.value) return;
        s.value = me;
        s.dispatchEvent(new Event('change', { bubbles: true }));
      });
      showTurn();
    });
    showTurn();
    var pick = function (name) {   // #me=Name in the address, else the name this device remembers
      var r = [].filter.call(next.querySelectorAll('input[name=me]'), function (i) { return i.value === name; })[0];
      if (!r) return false;
      r.checked = true;
      r.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    };
    var fromUrl = (location.hash.match(/me=([^&]+)/) || [])[1];
    if (fromUrl && pick(dec(fromUrl))) next.scrollIntoView();
    else if (store.get('me')) pick(store.get('me'));
    window.addEventListener('hashchange', function () {
      var m = (location.hash.match(/me=([^&]+)/) || [])[1];
      if (m) pick(dec(m));
    });
  }
  /* --- weekly.html ---------------------------------------------------------------------------------------------- */

  var chat = $('chat');
  if (chat) {
    var data = JSON.parse($('ledger-data').textContent);
    var box = function (id) { var b = $(id + '-out'); b.textContent = ''; return b; };
    var head = function (to, text) { return to.appendChild(el('h3', 'wk-h', text)); };
    var para = function (to, text, cls) { return to.appendChild(el('p', cls || '', text)); };
    var list = function (to, rows) {
      var ul = to.appendChild(el('ul', 'wk-list'));
      rows.forEach(function (r) { ul.appendChild(el('li', '', r)); });
      return ul;
    };
    var block = function (to, text, button) {
      to.appendChild(el('pre', 'lit keep', text));
      var b = el('button', 'btn copy', button);
      b.type = 'button';
      b.dataset.copy = text;
      to.appendChild(el('p', 'acts')).appendChild(b);
    };
    var plural = function (n, w) { return n + ' ' + w + (n === 1 ? '' : 's'); };
    var postName = function (x) {
      return x.type === 'check' ? answerName(x.q, x.a) : x.type === 'yes' ? 'yes to P' + x.num : x.type === 'vote' ?
        'vote on ' + x.subject : x.type === 'answer' ? 'answer to Q' + x.q : 'proposal';
    };
    var STEPS = ['w-seen', 'w-back', 'w-close', 'w-props', 'w-votes', 'w-last', 'w-unread'];

    var read = function () {
      var filled = /\S/.test(chat.value);
      STEPS.forEach(function (id) { $(id).hidden = !filled; });
      $('w-sum').textContent = '';
      if (!filled) return;
      var now = today(), r = review(parse(chat.value), data, now), c = r.counts, out;
      $('w-sum').textContent = 'Read ' + plural(c.checks, 'CHECK post') + ', ' + plural(c.answers, 'ANSWER post') + ', ' +
        plural(c.proposals, 'PROPOSE post') + ', ' + plural(c.yeses, 'YES post') + ' and ' + plural(c.votes, 'VOTE post') +
        '. ' + plural(r.unread.length, 'line') + ' left for you to read (step 8).';

      out = box('w-seen');
      if (!r.add.length && !r.answers.length) para(out, 'No CHECK or ANSWER post to add.');
      r.add.forEach(function (g) {
        head(out, 'Under ' + answerName(g.q.num, g.answer.num));
        para(out, g.answer.empty ? 'Replace its line "SEEN      nobody yet" with these:' : 'Add these under its last SEEN item:');
        block(out, g.lines.join('\n'), 'Copy these lines');
        list(out, g.posts.map(function (x) {
          return 'Line ' + x.at + ' of what you pasted, posted as ' + x.who + ': check the chat shows ' + x.who + ' sent it.' +
            (has(data.members, x.who) ? '' : ' Not on the Member line: it counts toward keeping open or reopening, not closing (rule 5).');
        }));
      });
      r.answers.forEach(function (n) {
        head(out, 'New answer: ' + answerName(n.q.num, n.num));
        para(out, 'Put it under Q' + n.q.num + ', after its last answer, lined up like the answers above it.' +
          (n.renumber ? ' The post numbers it ' + n.renumber + '; the file\'s next number is ' + n.num + ': answers are ' +
            'numbered in the order posted.' : ''));
        if (n.post.text.length) block(out, n.post.text.join('\n'), 'Copy the answer');
      });
      if (r.held.length) {
        head(out, 'Posts for you to read yourself');
        list(out, r.held.map(function (t) {
          return 'Line ' + t.post.at + ', ' + postName(t.post) + ' from ' + t.post.who + ': ' + t.why + '.';
        }));
        para(out, 'None of these is in the blocks on this page. Read each in the chat and add it by hand if it should count.', 'hint');
      }
      if (r.already.length) {
        para(out, 'Already in the file, so not repeated: ' + r.already.map(function (x) {
          return postName(x) + ' from ' + x.who + ', ' + x.date;
        }).join('; ') + '.', 'hint');
      }

      out = box('w-back');
      if (!r.from) para(out, 'No dated CHECK, PROPOSE, YES or VOTE post in what you pasted, so nothing to match.');
      else if (!r.back.length) para(out, 'Every SEEN item, proposal, yes and vote in the file dated ' + r.from + ' or later has its post in what you pasted.');
      else {
        para(out, 'These are in the file, dated ' + r.from + ' or later, and nothing in what you pasted matches them. ' +
          'Find each one\'s post in the chat (rule 7), or tell the group it is missing.');
        list(out, r.back);
      }

      out = box('w-close');
      if (!r.add.length) para(out, 'No new results, so nothing new to close.');
      r.add.forEach(function (g) {
        var st = g.after, was = g.before, row = el('p', 'wk-close');
        row.appendChild(el('strong', '', answerName(g.q.num, g.answer.num) + ' '));
        var text;
        if (!g.moved && st.state !== 'OPEN') {
          text = 'was closed already: ' + st.state + linesText(st.lines) + ' on ' + st.since + ', by ' + st.by.join(', ') + '.';
        } else if (st.state !== 'OPEN') {
          row.classList.add('ok');
          text = 'closes ' + st.state + linesText(st.lines) + ' on ' + st.since + ': ' + st.by.join(', ') + ', members ' +
            'other than its posters, active that day, posted the same result, at least one of them by hand (rule 4).';
        } else if (g.moved && was.state !== 'OPEN') {
          text = 'reopens on ' + st.since + ': it was ' + was.state + ', and two people other than its posters have now ' +
            'posted the other result. From here only posts after that day count (rule 5).';
        } else if (g.moved && st.both.length) {
          text = 'is kept open on ' + st.since + ': two people posted HOLDS and two others DOESN\'T HOLD. From here only ' +
            'posts after that day count (rule 5).';
        } else {
          text = 'stays open. It closes when three members other than its posters, active that day, post the same result, ' +
            'one of them by hand; fewer if fewer than four are active (rule 4).';
        }
        row.appendChild(document.createTextNode(text));
        out.appendChild(row);
        if (g.samples.length) para(out, 'Not counted toward HOLDS: ' + g.samples.join(', ') + ' (not every WRONG IF line, or ' +
          'not "all" items on each; it stays a SEEN item, Result).', 'hint');
        if (g.outsiders.length) para(out, 'Not counted toward closing: ' + g.outsiders.join(', ') + ' (not on the Member line).', 'hint');
      });
      r.questions.forEach(function (x) {
        para(out, 'Q' + x.q.num + ' is now ' + x.now.state + ' (since ' + x.now.since + ')' + (x.now.state === 'CLOSED'
          ? ': answer ' + x.now.answer + ' closed HOLDS (rule 4).' : ': it did not close within its 30 days (rule 5).') +
          ' The slot is free: step 5 says what opens.', 'wk-close ok');
      });
      if (!data.adopted) para(out, 'STATUS says Proposed: nothing closes yet, and posts are the dry run.', 'hint');

      out = box('w-props');
      if (!r.props.length && !r.opens.length) para(out, 'No new proposal or yes, and nothing opens.');
      r.props.forEach(function (x) {
        var p = x.prop;
        head(out, (p.fresh ? 'New proposal: P' : 'P') + p.num);
        para(out, p.fresh ? 'Add it under PROPOSED QUESTIONS, above "The next proposal is P' + (p.num) + '.", and raise ' +
          'that number to P' + r.next + '.' + (p.post.said && p.post.said !== p.num ? ' The post numbers it P' +
            p.post.said + '; proposals are numbered in the order posted.' : '')
          : x.had ? 'Replace its Yes: line with this one:' : 'Add this line under it:');
        block(out, x.lines.join('\n'), 'Copy ' + (p.fresh ? 'the proposal' : 'the Yes: line'));
        para(out, p.reach ? 'It has three yeses from members other than ' + p.who + ' since adoption: on ' + p.reach + ' (rule 2).'
          : 'Not yet three yeses that count (rule 2).', 'hint');
      });
      r.opens.forEach(function (o) {
        head(out, 'Opens: Q' + o.num + ', from P' + o.prop.num + ', on ' + o.day + ' (rule 2)');
        para(out, 'Add this under THE QUESTIONS, above "The next question is Q' + o.num + '.", and raise that number to Q' +
          (o.num + 1) + '. Under P' + o.prop.num + ', add the line "Opened as Q' + o.num + '."');
        block(out, o.lines.join('\n'), 'Copy the question');
      });

      out = box('w-votes');
      if (!r.votes.length) para(out, 'Nothing in VOTES is open, and no VOTE post in what you pasted.');
      r.votes.forEach(function (t) {
        head(out, t.subject);
        if (t.fresh) para(out, 'New in VOTES. Its first line, with the day the text was posted and the SHA-256 of the text ' +
          'voted on:  ' + t.subject + ', posted YYYY-MM-DD, SHA-256 <hash>', 'hint');
        if (t.lines.length) block(out, t.lines.join('\n'), 'Copy the votes');
        var n = t.count;
        list(out, ['Yes, from members active that day: ' + (n.yes.join(', ') || 'none yet'),
          'Object: ' + (n.object.join(', ') || 'none') + ' (at most one)']);
        t.objections.forEach(function (v) { if (v.why.length) para(out, v.who + ': ' + v.why.join(' '), 'wk-why'); });
        para(out, n.passed ? 'Passes on ' + n.passed + ' (rule 8).' : 'Counted from ' + daysAfter(t.posted, 7) +
          ': it has not passed on these counts.', 'wk-close' + (n.passed ? ' ok' : ''));
      });
      if (r.votes.length) para(out, 'Each member\'s latest vote stands, counted at the end of each day from the 7th after ' +
        'the post. It needs four active members\' yes (every active member if fewer than five) and at most one object.', 'hint');

      out = box('w-last');
      para(out, 'Add this line under LAST POSTS. Each date is the member\'s last post the file or what you pasted shows; ' +
        'check any "none" against the chat.');
      block(out, r.last.join('\n'), 'Copy the line');

      out = box('w-unread');
      if (!r.unread.length) para(out, 'Nothing: every line belonged to a post this page reads.');
      else {
        para(out, 'Names and times from the chat, replies, results written another way: read them yourself. A result ' +
          'here counts as much as one above.');
        out.appendChild(el('pre', 'lit unread', r.unread.map(function (u) {
          return (new Array(6).join(' ') + u.at).slice(-5) + '  ' + u.text;
        }).join('\n')));
      }
    };
    chat.addEventListener('input', read);
    read();
  }

  /* --- write.html: the answer form ------------------------------------------------------------------------------ */

  var wf = document.querySelector('.wf');
  if (wf) {
    var wis = wf.querySelector('.wis'), spare = wis.firstElementChild.cloneNode(true);
    var copies = [].slice.call(document.querySelectorAll('.w-copy-chat, .w-copy-entry'));
    copies.forEach(function (b) { b.classList.add('copy'); });
    var renumber = function () {
      [].forEach.call(wis.children, function (li, i) {
        li.querySelector('.n').textContent = i + 1;
        li.querySelector('.wi-t').setAttribute('aria-label', 'WRONG IF line ' + (i + 1));
        li.querySelector('.wi-x').setAttribute('aria-label', 'Remove WRONG IF line ' + (i + 1));
        li.querySelector('.wi-x').hidden = wis.children.length === 1;
      });
    };
    var write = function () {
      var name = nameOf(wf), q = wf.dataset.q, n = wf.dataset.next, date = today(), missing = [];
      var says = wf.querySelector('.says').value.replace(/\s+/g, ' ').trim();
      var links = wf.querySelector('.link').value.split('\n').map(function (s) { return s.trim(); }).filter(Boolean);
      var lines = [].map.call(wis.querySelectorAll('.wi-t'), function (i) {
        return i.value.replace(/\s+/g, ' ').trim().replace(/^or\s+/i, '').replace(/[\s.;,]+$/, '');
      });
      [].forEach.call(wis.children, function (li, i) {
        var warn = li.querySelector('.warn'), t = lines[i];
        warn.hidden = !t || (/\d{4}-\d\d-\d\d/.test(t) && !/[;,] or /i.test(t));
        warn.textContent = /[;,] or /i.test(t) ? 'This line holds ", or": the ledger counts each part after it as a WRONG ' +
          'IF line of its own. Make it two lines.' : 'No date in this line. Could a stranger make it true later, with a ' +
          'transfer or a new post? End-date it: "by the end of ' + date + '".';
      });
      lines = lines.filter(Boolean);
      var answer = [PAD4 + 'ANSWER ' + n + '.   (' + (name || '?') + ', ' + date + ')']
        .concat(wrap(PAD6 + 'SAYS' + PAD6, says || '?', PAD16));
      links.forEach(function (l, i) {
        answer = answer.concat(i === 0 ? wrap(PAD6 + 'LINK' + PAD6, l, PAD16) : /^https?:\/\//i.test(l) ? [PAD18 + l] : wrap(PAD16, l, PAD16));
      });
      if (!links.length) answer.push(PAD6 + 'LINK      ?');
      answer = answer.concat(wrap(PAD6 + 'WRONG IF  ', lines.length ? lines.join('; or ') + '.' : '?', PAD16),
        PAD6 + 'SEEN      nobody yet');
      var text = answer.join('\n'), post = ['ANSWER Q' + (q || '?'), name || '?', date].join(DOT) + '\n```\n' + text + '\n```';
      if (!q) missing.push('an open question to answer');
      if (!name) missing.push('your name');
      if (!says) missing.push('what it SAYS');
      if (!links.some(function (l) { return /^https?:\/\/\S+$/i.test(l); })) missing.push('a LINK, on a line of its own, starting https://');
      if (!lines.length) missing.push('a WRONG IF line');
      showPost(document.querySelector('.chat-out'), post);
      document.querySelector('.entry-out').textContent = text;
      document.querySelector('.w-copy-chat').dataset.copy = post;
      document.querySelector('.w-copy-entry').dataset.copy = text;
      needs($('need-w'), copies, missing, 'Ready. Read it once more against SAYS: every part of it needs a WRONG IF line.');
    };
    wf.querySelector('.wi-add').addEventListener('click', function () {
      var li = wis.appendChild(spare.cloneNode(true));
      renumber();
      li.querySelector('.wi-t').focus();
      write();
    });
    wis.addEventListener('click', function (e) {
      var x = e.target.closest('.wi-x');
      if (!x) return;
      x.closest('li').remove();
      renumber();
      write();
    });
    wf.addEventListener('input', write);
    wf.addEventListener('change', write);
    renumber();
    write();
  }

  reveal();

  /* --- ledger.html: the files and their SHA-256 ---------------------------------------------------------------- */

  var printed = [].slice.call(document.querySelectorAll('code[data-sha-of]'));
  if (!printed.length) return;
  var said = function (code, text) { code.parentElement.querySelector('.served').textContent = text; };
  if (!(window.crypto && crypto.subtle)) {
    printed.forEach(function (c) { said(c, 'This browser cannot work out SHA-256 here. Any SHA-256 tool can, on the downloaded file.'); });
    return;
  }

  function sha(bytes) {
    return crypto.subtle.digest('SHA-256', bytes).then(function (d) {
      return Array.prototype.map.call(new Uint8Array(d), function (b) { return b.toString(16).padStart(2, '0'); }).join('');
    });
  }

  printed.forEach(function (code) {
    fetch(code.dataset.shaOf, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.arrayBuffer();
    }).then(sha).then(function (got) {
      said(code, got === code.textContent
        ? 'Your browser just read this file from the site and got this SHA-256.'
        : 'Your browser just read this file from the site and got a different SHA-256: ' + got + '. Tell the group.');
    }).catch(function () { said(code, 'Your browser could not read this file to check it.'); });
  });

  $('copy-file').addEventListener('change', function () {
    var f = this.files[0], out = $('copy-result');
    if (!f) return;
    f.arrayBuffer().then(function (buf) {
      var bytes = new Uint8Array(buf);
      var unix = bytes.filter(function (b, i) { return !(b === 13 && bytes[i + 1] === 10); });   // Windows line ends made plain
      return Promise.all([sha(bytes), sha(unix)]);
    }).then(function (s) {
      var exact = printed.filter(function (c) { return c.textContent === s[0]; })[0];
      var ends = printed.filter(function (c) { return c.textContent === s[1]; })[0];
      out.className = 'msg ' + (exact || ends ? 'ok' : 'err');
      out.textContent = exact ? 'Same text as ' + exact.dataset.name + ', letter for letter.'
        : ends ? 'Same text as ' + ends.dataset.name + '. Only the line ends differ, which Windows does when it saves a file.'
          : 'Not the same text as any file listed here. Your copy\'s SHA-256 is ' + s[0] + '.';
    });
  });
})();
