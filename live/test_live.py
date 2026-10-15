"""The live record's rules and its export, offline: an in-memory record, fixed times, ledger.txt only read.

    python live/test_live.py
"""
import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import server  # noqa: E402
from server import NotSignedIn, Refused, build, sign_in, standing  # noqa: E402

T0 = dt.datetime(2026, 10, 15, 12, tzinfo=dt.timezone.utc)
MEMBERS = ["Ann", "Bo", "Cy"]


def posts(*pairs, start=T0):
    """[(who, result)] as checks an hour apart."""
    return [{"who": who, "result": r, "at": (start + dt.timedelta(hours=i)).isoformat()} for i, (who, r) in enumerate(pairs)]


def state(*pairs, at=T0 + dt.timedelta(days=1)):
    return standing("Wes", MEMBERS, posts(*pairs), at)[:2]


class Rules3And4(unittest.TestCase):
    def test_nobody_yet_is_open(self):
        self.assertEqual(state(), ("OPEN", []))

    def test_two_members_agreeing_close_it(self):
        self.assertEqual(state(("Ann", "HOLDS"), ("Bo", "HOLDS")), ("CLOSED", ["HOLDS"]))

    def test_a_member_and_someone_else_do_not(self):
        self.assertEqual(state(("Ann", "HOLDS"), ("Stranger", "HOLDS"))[0], "OPEN")

    def test_the_writer_never_counts(self):
        self.assertEqual(state(("Wes", "HOLDS"), ("Ann", "HOLDS"))[0], "OPEN")

    def test_two_and_two_keep_it_open_with_both(self):
        got = state(("Ann", "HOLDS"), ("X", "DOESN'T HOLD"), ("Y", "DOESN'T HOLD"), ("Bo", "HOLDS"))
        self.assertEqual(got, ("SPLIT", ["DOESN'T HOLD", "HOLDS"]))

    def test_split_for_30_days_is_cant_tell(self):
        split = (("Ann", "HOLDS"), ("X", "DOESN'T HOLD"), ("Y", "DOESN'T HOLD"), ("Bo", "HOLDS"))
        split_at = T0 + dt.timedelta(hours=3)
        self.assertEqual(state(*split, at=split_at + dt.timedelta(days=29))[0], "SPLIT")
        self.assertEqual(state(*split, at=split_at + dt.timedelta(days=30))[0], "CAN'T TELL")

    def test_two_rivals_after_closing_reopen_it(self):
        got = state(("Ann", "HOLDS"), ("Bo", "HOLDS"), ("X", "DOESN'T HOLD"), ("Y", "DOESN'T HOLD"))
        self.assertEqual(got, ("SPLIT", ["HOLDS", "DOESN'T HOLD"]))

    def test_a_reopened_entry_closes_on_later_posts_only(self):
        reopened = (("Ann", "HOLDS"), ("Bo", "HOLDS"), ("X", "DOESN'T HOLD"), ("Y", "DOESN'T HOLD"))
        self.assertEqual(state(*reopened, ("Cy", "HOLDS"))[0], "SPLIT")
        self.assertEqual(state(*reopened, ("Cy", "HOLDS"), ("Ann", "HOLDS")), ("CLOSED", ["HOLDS"]))


class Record(unittest.TestCase):
    def setUp(self):
        self.raw = build.raw_text(build.LEDGER).decode("utf-8")
        self.members, found = server.read_ledger(self.raw.rstrip("\n"))
        self.conn = server.connect(":memory:")
        server.seed(self.conn, found)

    def tearDown(self):
        self.conn.close()

    def second(self, num, who, at=T0, **body):
        return server.second(self.conn, self.members, num, dict({"who": who, "tests": True}, **body), at)

    def check(self, num, who, at=T0, **body):
        post = {"who": who, "result": "HOLDS", "saw": "the phrase, in the archived script",
                "tested": "the phrase is not in that copy", "new": "new thing from " + who, "minutes": 4, "opened": True}
        return server.check(self.conn, self.members, num, dict(post, **body), at)

    def test_a_fresh_record_exports_the_ledger_unchanged(self):
        self.assertEqual(server.export_text(self.conn, self.raw), self.raw)

    def test_a_second_and_checks_export_as_lines_the_ledger_reads(self):
        self.second(3, "Laura")
        self.check(3, "Ksizzle")
        once = server.export_text(self.conn, self.raw)
        self.assertIn("    SECONDED  Laura, 2026-10-15", once)
        self.assertIn("    SEEN      - Ksizzle, 2026-10-15: HOLDS. Saw: the phrase", once)
        fields = self.fields(once, "3")
        self.assertTrue(build.checked(fields))
        self.check(3, "Merc", at=T0 + dt.timedelta(hours=1))
        twice = server.export_text(self.conn, once)          # the earlier export is kept, not refused
        self.assertIn("Merc, 2026-10-15: HOLDS", twice)
        self.assertEqual(server.view(self.conn, self.members, 3, T0)["state"], "CLOSED")   # two members agreed
        after = self.check(3, "Laura", at=T0 + dt.timedelta(hours=2))  # who seconded may check too
        self.assertEqual((after["state"], len(after["checks"])), ("CLOSED", 3))

    def test_a_hand_written_seen_line_stops_the_export(self):
        lines = self.raw.split("\n")
        at = lines.index("  FACT 3. (Zurandol, 2026-10-12)")
        seen = next(i for i in range(at, len(lines)) if lines[i] == server.NOBODY)
        lines[seen] = "    SEEN      Laura, 2026-10-15: HOLDS, saw it in the chat."
        with self.assertRaises(SystemExit):
            server.export_text(self.conn, "\n".join(lines))

    def test_what_the_rules_turn_away(self):
        refused = {
            "the writer seconding": lambda: self.second(3, "Zurandol"),
            "a second without the tick": lambda: self.second(3, "Laura", tests=False),
            "a check before any second": lambda: self.check(3, "Laura"),
            "a promise with no date": lambda: self.check(7, "Laura"),
        }
        for what, act in refused.items():
            with self.subTest(what), self.assertRaises(Refused):
                act()
        self.second(3, "Laura")
        refused = {
            "the writer checking": lambda: self.check(3, "Zurandol"),
            "no opened tick": lambda: self.check(3, "Merc", opened=False),
            "minutes out of range": lambda: self.check(3, "Merc", minutes=0),
            "a result for the other kind": lambda: self.check(3, "Merc", result="KEPT"),
            "notation kept off the pages": lambda: self.check(3, "Merc", saw="balance went -1"),
        }
        for what, act in refused.items():
            with self.subTest(what), self.assertRaises(Refused):
                act()
        self.check(3, "Merc")
        with self.assertRaises(Refused):
            self.check(3, "merc", new="something else")      # the same person twice, any case
        with self.assertRaises(Refused):
            self.second(3, "laura")
        with self.assertRaises(Refused):
            self.check(3, "Ksizzle", new="NEW THING FROM MERC")  # a copied new thing

    def test_nothing_in_the_record_is_rewritten_or_removed(self):
        self.second(3, "Laura")
        for sql in ("UPDATE seconds SET who='Merc'", "DELETE FROM seconds"):
            with self.subTest(sql), self.assertRaises(server.sqlite3.IntegrityError):
                self.conn.execute(sql)

    @staticmethod
    def fields(text, num):
        secs = build.sections(text.rstrip("\n"))[1]
        return next(it[4] for it in build.entries(build.entries_section(secs)[1]) if it[0] == "entry" and it[2] == num)


class Strangers(Record):
    """The stranger lane: no claim, a check only, a name that is not a member's, and rule 3's limits."""

    def stranger(self, num, who, via, at=T0, result="HOLDS", **body):
        post = {"who": who, "result": result, "saw": "the phrase, in the archived script",
                "tested": "the phrase is not in that copy", "new": "new thing from " + who, "minutes": 4, "opened": True}
        return server.check(self.conn, self.members, num, dict(post, **body), at, via=via)

    def close(self, num, result="HOLDS"):
        self.second(num, "Laura")
        self.check(num, "Merc", result=result)
        return self.check(num, "Ksizzle", result=result, at=T0 + dt.timedelta(hours=1))

    def test_strangers_never_close_an_entry(self):
        self.second(3, "Laura")
        self.stranger(3, "Rook", "a")
        e = self.stranger(3, "Pawn", "b")
        self.assertEqual(e["state"], "OPEN")
        e = self.check(3, "Merc")                                   # one member with two strangers is still not two members
        self.assertEqual(e["state"], "OPEN")

    def test_two_strangers_reopen_a_closed_entry(self):
        self.assertEqual(self.close(3)["state"], "CLOSED")
        e = self.stranger(3, "Rook", "a", result="DOESN'T HOLD")
        self.assertEqual(e["state"], "CLOSED")                      # one is a NOTE, not a reopening
        e = self.stranger(3, "Pawn", "b", result="DOESN'T HOLD", at=T0 + dt.timedelta(hours=3))
        self.assertEqual(e["state"], "SPLIT")

    def test_a_stranger_cannot_take_a_members_name(self):
        self.second(3, "Laura")
        for who in ("Laura", "laura", "L a u r a", "LAURA.", "crypto-fish", "Laurа", "x"):
            with self.subTest(who), self.assertRaises(Refused):
                self.stranger(3, who, "a")

    def test_a_name_the_build_would_refuse_is_refused(self):
        self.second(3, "Laura")
        for n, who in enumerate(("Trit", "Rook -1")):
            with self.subTest(who), self.assertRaises(Refused):
                self.stranger(3, who, "a" + str(n))
        with self.assertRaises(Refused):                            # the typed-name mode has the same door
            self.check(3, "Trit")

    def test_a_name_that_holds_a_members_name_is_refused(self):
        self.second(3, "Laura")
        for n, who in enumerate(("Laura B", "Merc Hunter", "the Crypto Fish", "Crypto-Fish Jr")):
            with self.subTest(who), self.assertRaises(Refused):
                self.stranger(3, who, "a" + str(n))
        self.stranger(3, "Mercedes", "m")                           # only a whole word counts
        self.stranger(3, "Laurana", "l")

    def test_the_export_stops_before_writing_what_the_build_refuses(self):
        with self.assertRaises(SystemExit):
            server.refuse_banned("    SEEN      - Trit, 2026-10-15: HOLDS.")
        server.refuse_banned(self.raw)                              # the ledger as it stands is fine

    def test_one_source_posts_once_per_entry(self):
        self.second(3, "Laura")
        self.stranger(3, "Rook", "a")
        with self.assertRaises(Refused):
            self.stranger(3, "Rook2", "a")                          # the same source under another name
        self.stranger(3, "Pawn", "b")                               # another source is not held back

    def test_one_source_posts_only_so_many_a_day(self):
        facts = (1, 2, 3, 4, 5, 6)
        for n in facts:
            self.second(n, "Laura")
        for n in facts[:server.STRANGER_PER_DAY]:
            self.stranger(n, "Day%d" % n, "c")
        with self.assertRaises(Refused):
            self.stranger(facts[-1], "Late", "c")
        self.stranger(facts[-1], "Late", "c", at=T0 + dt.timedelta(days=1, minutes=1))

    def test_an_entry_takes_only_so_many_from_outside(self):
        self.second(3, "Laura")
        for n in range(server.STRANGER_PER_ENTRY):
            self.stranger(3, "Guest%d" % n, "s%d" % n)
        with self.assertRaises(Refused):
            self.stranger(3, "OneMore", "late")

    def test_the_source_never_leaves_the_record(self):
        self.second(3, "Laura")
        out = self.stranger(3, "Rook", "secret-source")
        self.assertNotIn("via", out["checks"][0])
        self.assertNotIn("secret-source", repr(server.listing(self.conn, self.members, T0)))

    def test_the_source_is_a_hash_that_depends_on_the_address(self):
        server.SALT = Path(__file__).resolve().parent / "test-salt.tmp"
        try:
            a, b = server.source_of("203.0.113.5"), server.source_of("203.0.113.6")
        finally:
            server.SALT.unlink(missing_ok=True)
        self.assertEqual(len(a), 16)
        self.assertNotEqual(a, b)
        self.assertNotIn("203.0.113", a)


class Serving(unittest.TestCase):
    """The record's own server shows pages, never its salt, its database or its source."""

    def test_only_pages_and_their_assets_are_served(self):
        for path in ("/ledger.html", "/assets/ledger.css", "/assets/claims.js", "/live/live.js", "/live/live.css", "/ledger.txt"):
            with self.subTest(path):
                self.assertTrue(server.servable(path))
        for path in ("/live/salt", "/live/record.db", "/live/server.py", "/live/%73alt", "/.git/config", "/claims.py",
                     "/claims.sql", "/%2e%2e/x.html", "/live/../live/salt", "/live/"):
            with self.subTest(path):
                self.assertFalse(server.servable(path))

    def test_only_this_machine_may_be_the_host(self):
        for host in ("127.0.0.1:%d" % server.PORT, "localhost:%d" % server.PORT):
            self.assertTrue(server.host_ok(host))
        for host in (None, "", "evil.example", "127.0.0.1", "evil.example:%d" % server.PORT, "127.0.0.1:1"):
            self.assertFalse(server.host_ok(host))


class SourceHash(unittest.TestCase):
    def setUp(self):
        self.old, server.SALT = server.SALT, Path(__file__).resolve().parent / "test-salt.tmp"

    def tearDown(self):
        server.SALT.unlink(missing_ok=True)
        server.SALT = self.old

    def test_an_ipv6_network_is_one_source(self):
        a, b = server.source_of("2001:db8:1:2::1"), server.source_of("2001:db8:1:2:ffff:ffff:ffff:ffff")
        self.assertEqual(a, b)                                      # one /64 is one connection, not 2^64
        self.assertNotEqual(a, server.source_of("2001:db8:1:3::1"))
        self.assertNotEqual(server.source_of("203.0.113.5"), server.source_of("203.0.113.6"))


class SignIn(unittest.TestCase):
    """The name comes from the claim endpoint's answer for the token, never from what was typed."""

    @staticmethod
    def claim(status, body=None):
        return lambda token: (status, dict(body or {}, token=token))

    def test_the_claimed_name_replaces_the_typed_one(self):
        out = sign_in({"who": "Merc", "tests": True}, "Bearer abc", self.claim(200, {"name": "Laura", "mine": True}))
        self.assertEqual(out, {"who": "Laura", "tests": True})

    def test_no_token_or_an_unknown_one_is_not_signed_in(self):
        for what, auth, ask in (("no header", None, self.claim(200, {"name": "Laura"})),
                                ("empty bearer", "Bearer  ", self.claim(200, {"name": "Laura"})),
                                ("unknown token", "Bearer abc", self.claim(401))):
            with self.subTest(what), self.assertRaises(NotSignedIn):
                sign_in({"who": "Laura"}, auth, ask)

    def test_a_claim_service_that_fails_is_refused_not_trusted(self):
        def down(token):
            raise OSError("offline")
        for what, ask in (("offline", down), ("server error", self.claim(503)), ("no name", self.claim(200, {}))):
            with self.subTest(what), self.assertRaises(Refused) as ctx:
                sign_in({"who": "Laura"}, "Bearer abc", ask)
            self.assertNotIsInstance(ctx.exception, NotSignedIn)


if __name__ == "__main__":
    unittest.main()
