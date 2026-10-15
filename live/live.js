/* The ledger page wired to the live record (live/server.py). Each entry's SECONDED and SEEN lines come from the
   record, and anyone can second an entry or post a check from the page. Where there is no record, as on the
   published site, the first request fails and the page stays exactly as built. Everything a person typed is put
   on the page as text, never as markup. */
(() => {
  "use strict";
  const NAME_KEY = "assembly-name";
  const VERDICTS = ["v-open", "v-yes", "v-no", "v-part"];
  const RESULT_CLASS = { "HOLDS": "v-yes", "KEPT": "v-yes", "DOESN'T HOLD": "v-no", "BROKEN": "v-no" };
  const RESULTS = { FACT: ["HOLDS", "DOESN'T HOLD"], PROMISE: ["KEPT", "BROKEN"] };
  const MOST_MINUTES = 600;
  const TOKEN_KEY = "assembly:token";                  // what the front page's name claim leaves on this device
  let opener = null;                                   // the button that opened the form, to return focus to
  let signin = false;                                  // the record names you from your claim, not from a typed name
  let strangers = false;                               // and takes a check from a device with no claim (rule 3's "member or not")

  const recalled = () => { try { return localStorage.getItem(NAME_KEY) || ""; } catch (e) { return ""; } };
  const remember = name => { try { localStorage.setItem(NAME_KEY, name); } catch (e) { /* asked again next time */ } };
  const token = () => { try { return localStorage.getItem(TOKEN_KEY) || ""; } catch (e) { return ""; } };
  const today = () => new Date().toISOString().slice(0, 10);
  const day = at => at.slice(0, 10);
  const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
  const label = e => `${e.kind.toLowerCase()} ${e.num}`;
  const test = e => (e.kind === "FACT" ? "WRONG IF lines" : "KNOWN BY link");

  function el(tag, attrs, ...kids) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === false || v == null) continue;
      if (k === "text") node.textContent = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? "" : v);
    }
    node.append(...kids.filter(k => k != null && k !== false));
    return node;
  }

  // Where the entry stands, as the mark beside it says it, and the colour that goes with it.
  function standing(e) {
    if (e.state === "CLOSED") return [e.results[0], RESULT_CLASS[e.results[0]]];
    if (e.state === "SPLIT") return ["kept open: " + e.results.join(" and "), "v-part"];
    if (e.state === "CAN'T TELL") return ["CAN'T TELL", "v-part"];
    if (!e.seconds.length) return ["needs a second", "v-open"];
    return [e.checks.length ? `open, ${plural(e.checks.length, "check")} posted` : "seconded, waiting for checks", "v-open"];
  }

  // What happens next, in a sentence; when it names something missing, posting a check waits for it.
  function nextStep(e, on) {
    if (e.kind === "PROMISE" && !e.due) return ["This promise has no date yet, so nobody can check it.", true];
    if (e.kind === "PROMISE" && on < e.due) return [`This promise can be checked on or after ${e.due}.`, true];
    if (!e.seconds.length) {
      return [`Needs a second: someone other than ${e.writer} says its ${test(e)} test what it says and they want it ` +
              "checked. Nobody can post a check until then.", true];
    }
    if (e.state === "CLOSED") return [`Closed. Two people posting the other result reopen it.`, false];
    if (e.state === "SPLIT") {
      return ["Two people posted each result. It closes if two members agree in posts from here on, or is " +
              "CAN'T TELL 30 days after the split.", false];
    }
    if (e.state === "CAN'T TELL") return ["Split for 30 days without closing.", false];
    return [`Closes when two members other than ${e.writer} post the same result.`, false];
  }

  // The row of the entry's fields with this label, made (before `before`, or last) if the page has none.
  function row(fields, name, before) {
    let r = [...fields.children].find(d => d.firstElementChild && d.firstElementChild.textContent === name);
    if (!r) {
      r = el("div", {}, el("dt", { text: name }), el("dd"));
      if (before) before.before(r); else fields.append(r);
    }
    return r.lastElementChild;
  }

  // The posted checks, folded: HOW TO CHECK step 2 is to look at the link before reading anyone else's post.
  function seenList(e) {
    return el("details", { class: "seen-list" },
      el("summary", { text: `Show the ${plural(e.checks.length, "posted check")}` }),
      el("p", { class: "hint", text: "Checking it yourself? Open the link before you read these." }),
      el("ul", {}, ...e.checks.map(c => el("li", {},
        el("p", { class: "head" }, el("strong", { text: `${c.who}, ${day(c.at)}` }), " ",
          el("span", { class: "res " + (RESULT_CLASS[c.result] || ""), text: c.result })),
        el("p", {}, el("span", { class: "q", text: "Saw" }), c.saw),
        el("p", {}, el("span", { class: "q", text: "Tested" }), c.tested),
        el("p", {}, el("span", { class: "q", text: "New" }), c.new),
        el("p", { class: "mins", text: plural(c.minutes, "minute") })))));
  }

  function render(e, note) {
    const art = document.getElementById(`${e.kind.toLowerCase()}-${e.num}`);
    if (!art) return null;
    const [said, cls] = standing(e);
    for (const node of [art, document.querySelector(`.strip a[href="#${art.id}"]`)]) {
      if (node) { node.classList.remove(...VERDICTS); node.classList.add(cls); }
    }
    const verdict = art.querySelector(".mark .verdict");
    if (verdict) verdict.textContent = said;
    const cite = [...art.querySelectorAll(".meta span")].find(s => s.textContent.startsWith("cite as:"));
    if (cite) cite.textContent = `cite as: ledger ${label(e)}, ${e.checks.length ? "checks posted, see SEEN" : "not yet checked"}`;

    const fields = art.querySelector("dl.fields");
    const seen = row(fields, "SEEN");
    if (e.seconds.length) {
      row(fields, "SECONDED", seen.parentElement)
        .replaceChildren(el("p", { text: e.seconds.map(s => `${s.who}, ${day(s.at)}`).join("; ") }));
    }
    seen.replaceChildren(e.checks.length ? seenList(e) : el("p", { text: "nobody yet" }));

    let panel = art.querySelector(".live");
    if (!panel) { panel = el("div", { class: "live" }); fields.after(panel); }
    const [step, waits] = nextStep(e, today());
    const stepId = `live-step-${e.num}`;
    const settled = e.state === "CLOSED" || e.state === "CAN'T TELL";
    const unclaimed = signin && !token();
    const claim = el("a", { href: "/febu-assembly.html" }, "claim your name on the front page");
    panel.replaceChildren(...[
      unclaimed && !strangers ? el("p", { class: "next" }, "To second or check, ", claim, " first, from this device.")
      : el("div", { class: "acts" },
        settled || unclaimed ? null : el("button", { type: "button", class: "btn", onclick: ev => open(e, "second", ev.currentTarget) },
          e.seconds.length ? "Second it too" : "Second it"),
        el("button", { type: "button", class: "btn primary", disabled: waits, "aria-describedby": stepId,
          onclick: ev => open(e, "check", ev.currentTarget) }, "Post a check")),
      el("p", { class: "next", id: stepId, text: step }),
      unclaimed && strangers && el("p", { class: "hint" }, "Not one of the seven? Post a check under a name of your own. It can keep an entry " +
        "open, or reopen it with a second person, and never close it (rule 3). Seconding needs a member. Members: ",
        claim, "."),
      note && el("p", { class: "msg ok", role: "status", tabindex: "-1", text: note })].filter(Boolean));
    return panel;
  }

  function field(text, help, input) {
    return el("label", { class: "field" }, el("span", { class: "name", text }),
      help ? el("span", { class: "help", text: help }) : null, input);
  }

  function tick(name, text) {
    return el("label", { class: "tick" }, el("input", { type: "checkbox", name, required: true }), el("span", { text }));
  }

  function form(e, kind) {
    const outside = signin && !token();                  // a stranger names themself; a member's name comes from the claim
    const who = signin && !outside ? null : field(outside ? "A name to post under" : "Your name",
      outside ? "Not a member's name. Letters A to Z, numbers, spaces or . _ ' - only." : null,
      el("input", { type: "text", name: "who", list: outside ? null : "assembly-members",
        autocomplete: "nickname", maxlength: "40", required: true, value: recalled() }));
    if (kind === "second") {
      return el("form", {}, who, tick("tests", `Its ${test(e)} test what it says, and I want it checked.`));
    }
    const promise = e.kind === "PROMISE";
    return el("form", {}, who,
      field("What you saw", "The number, the words or the date, as the page shows them.",
        el("textarea", { name: "saw", rows: "3", maxlength: "1000", required: true })),
      field(promise ? "What the KNOWN BY link showed" : "WRONG IF lines you tested",
        promise ? "What you opened, and what it says about the promise." : "Which of them you looked for, and what you found.",
        el("textarea", { name: "tested", rows: "3", maxlength: "1000", required: true })),
      field("One thing nobody has written yet", "Something on the page that is not in the entry or in any check before yours.",
        el("input", { type: "text", name: "new", maxlength: "1000", required: true })),
      el("fieldset", {}, el("legend", { text: "Your result" }),
        ...RESULTS[e.kind].map(r => el("label", { class: "choice" },
          el("input", { type: "radio", name: "result", value: r, required: true }), el("span", { text: r })))),
      field("Minutes it took", null, el("input", { type: "number", name: "minutes", min: "1", max: String(MOST_MINUTES),
        step: "1", inputmode: "numeric", required: true })),
      tick("opened", "I opened the link myself. An AI may have helped me look; it did not write this."));
  }

  function body(kind, data) {
    if (kind === "second") return { who: data.who, tests: data.tests === "on" };
    return { who: data.who, result: data.result, saw: data.saw, tested: data.tested, new: data.new,
             minutes: Number(data.minutes), opened: data.opened === "on" };
  }

  function open(e, kind, button) {
    const panel = document.getElementById(`${e.kind.toLowerCase()}-${e.num}`).querySelector(".live");
    panel.querySelector(".dialog")?.remove();
    panel.querySelector(".msg.ok")?.remove();
    opener = button;
    const titleId = `live-title-${e.num}`;
    const msg = el("p", { class: "msg", role: "alert" });
    const submit = el("button", { type: "submit", class: "btn primary" }, kind === "second" ? "Second it" : "Post check");
    const close = () => { box.remove(); if (opener && opener.isConnected) opener.focus(); };
    const f = form(e, kind);
    f.append(msg, el("div", { class: "acts" }, submit, el("button", { type: "button", class: "btn", onclick: close }, "Cancel")));
    const box = el("section", { class: "dialog", "aria-labelledby": titleId },
      el("div", { class: "bar" }, el("span", { id: titleId, text: kind === "second" ? `Second ${label(e)}` : `Post a check on ${label(e)}` }),
        el("button", { type: "button", class: "x", "aria-label": "Close", onclick: close }, "×")),
      f);
    box.addEventListener("keydown", ev => { if (ev.key === "Escape") close(); });
    f.addEventListener("submit", async ev => {
      ev.preventDefault();
      const sent = body(kind, Object.fromEntries(new FormData(f)));
      submit.disabled = true;
      msg.className = "msg";
      msg.textContent = "";
      try {
        const r = await fetch(`/api/entries/${e.num}/${kind}`, { method: "POST", cache: "no-store",
          headers: Object.assign({ "Content-Type": "application/json" },
            signin && token() ? { Authorization: "Bearer " + token() } : {}), body: JSON.stringify(sent) });
        const out = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(out.error || "The record did not take it. Post again.");
        if (sent.who) remember(sent.who);
        const done = render(out, kind === "second" ? `Seconded by ${out.seconds[out.seconds.length - 1].who}.`
          : "Check posted. It is in the record now, and in ledger.txt after the next export.");
        done?.querySelector(".msg.ok")?.focus();
      } catch (err) {
        msg.className = "msg err";
        msg.textContent = err instanceof TypeError
          ? "The record is not running. Start it with python live/server.py, then post again." : err.message;
        submit.disabled = false;
      }
    });
    panel.append(box);
    const first = [...box.querySelectorAll("input[type=text], textarea")].find(i => !i.value);
    (first || box.querySelector("input[type=checkbox]")).focus();
  }

  fetch("/api/entries", { cache: "no-store" })
    .then(r => (r.ok ? r.json() : null))
    .then(data => {
      if (!data || !Array.isArray(data.entries)) return;
      signin = data.signin === true;
      strangers = data.strangers === true;
      document.body.append(el("datalist", { id: "assembly-members" }, ...data.members.map(m => el("option", { value: m }))));
      document.getElementById("status")?.after(el("p", { class: "live-note",
        text: "Live record: second an entry or post a check under it. It goes into the record at once, and into " +
              "ledger.txt at the next export." }));
      data.entries.forEach(e => render(e));
    })
    .catch(() => { /* no record here: the page stays as built */ });
})();
