# papers/: the Assembly's working papers

Thinking, not the experiment. The experiment is the ledger (`ledger.txt`). Nothing here is a rule: a paper reaches the
ledger only as an entry, or as a rule change under rule 7 (a new ledger version). Like everything in the repo root, these
files are served as static files; no page links to them.

## Where each thing lives

| It is... | Home |
|---|---|
| Something a member can check, or a rule | `ledger.txt` (an entry, or a rule change) |
| The ledger in plain words, with the picture | `how.txt` and `assets/how-it-works.svg`, shown as the "how it works" tab. One source: don't copy it here. |
| Reading for the group: a study, an answer to a question | `findings.md`, `tests.txt`, `process.md`: served pages, no tab |
| A design, a review, an audit, a chat-post draft | here |
| A simulation, the chain captures, the group's chat and call transcripts | not published; kept with Z's private investigation notes |

## Files here

| File | What it is |
|---|---|
| `design/ASSEMBLY_SYSTEM_OUTLINE_20261014.md` | The design, sections 1-12. Sections 6-8 and 10 (pay, CTO, fee vault) are the options considered. **Section 9 decides: no treasury, forfeits only.** Section 11 is the answer version 3 carries: $FEBU is the bond. Section 12 is the one line for Witness (the Bitcoin contrast); the site's one sentence is in `how.txt`. |
| `design/ASSEMBLY_IDEAL_SYSTEM_20261014.md` | Theory after Witness's halving tweet and offer to fund experiments: payment only for resolvers (scripts anyone can run) that pass a held-out case, a halving ladder capped at the funder's total, the dev wallet as subject and never purse, and six experiments with their failure numbers. Fits version 3 without a rule change; untested. |
| `reviews/review_20261014/` | The four review reports behind section 9: `facts.md`, `prior_art.md`, `red_team.md`, `architecture.md`. Model output; the chain numbers in `facts.md` are RPC reads of 2026-10-14. |
| `reviews/AUDIT_20261015.md` | The audit of the version 3 release and the V3 post: findings marked RAN, READ or NOT CHECKED, with the commands to reproduce the RAN ones. The script it recommends is `checks/release.py`. |
| `posts/POST_REFRESH_20261015.txt` | The current draft of the chat post for the version 3 vote: the hash of `ledger.txt` as it stands, the vote date, what changed since the first post. |
| `posts/ASSEMBLY_POST_20261014_V3.txt` | The first V3 post. **Superseded** (first v3 hash, vote by 10-21); kept as it was, with a header saying so. |
| `posts/ASSEMBLY_REWARD_POST_20261014.txt` | The earlier reward-layer draft, folded into section 4 of the first V3 post. |

## Reading the 10-14 papers

The papers dated 2026-10-14 were written beside Z's private investigation notes and are kept as written; a dated paper is
not edited to follow later changes. Their paths read as follows:

- `docs/assembly/...` is `papers/...` here, and `febu-assembly/ledger.txt` is `ledger.txt`.
- `P187`, `P190`, `P191`, `tools/exp_stance` and `captures/...` name the private notes, the reward simulations and the
  chain captures. They are not published. The numbers the papers take from them are stated in the papers.
- "The chat as pasted in" and "the 10-08 voice call" are the group's own words and stay private.

## How to present it

One sentence, one picture, one page: all three are the how tab. Lead with the empty slot (febu never ran the check),
not with the rules. Say the limits before anyone asks. Never show a total, a score, or a price: rule 5 forbids any
post in the group's name from stating or implying one, and that includes "demand" and "supply" for $FEBU.
