"""Build the English holdout corpus: ten fictional company exports in the style of a workspace de-identification
benchmark (e-mails as .eml, a Slack-style export, documents as docx / xlsx / csv / pdf), each with an answer key.

    python evaluation/holdout-en/make_holdout.py [--out evaluation/holdout-en] [--sets 10] [--force]

Written blind: from the public description of the task only (file formats, ten labels, native coordinates, one
roster per export). Every person, company, address, number and handle below is invented for this corpus. The
generator is deterministic (one seed per export), so the corpus can be rebuilt byte for byte.

Layout (same as the public benchmark, so the same runner and scorer conventions apply):

    tasks/<set>/email/<id>.eml                  RFC 5322, text/plain 8bit, CRLF; attachments as base64 parts (embed sets)
    tasks/<set>/slack/users.json, channels.json, <channel>/<day>.json, <channel>/attachments/<id>-<name>
    tasks/<set>/drive/files.json, drive/<name>  (drive sets)
    ground_truth/<set>/ground_truth.jsonl       one row per e-mail body, Slack message and document, with
                                                ``ground_truth_spans`` in native coordinates (card shape)
    ground_truth/<set>/characters.json          the roster (people and organisation groups)

The locations are produced with the same adapters the Shield runner uses (``evaluation/public/privacybench/
run_shield.py``: ``load_units`` and ``native_locations``), after the files are written: a gold span is located
exactly where a prediction on the same text would be. PDFs are rendered with ``cupsfilter`` (macOS); the
generator stops with a clear message when it is missing.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import random
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "evaluation" / "public" / "privacybench"))
import run_shield as rs  # noqa: E402  (the adapters: load_units, native_locations)

LABELS = ("NAME_GIVEN", "NAME_FAMILY", "EMAIL_ADDRESS", "USERNAME", "ORGANIZATION", "PHONE_NUMBER",
          "LOCATION_ADDRESS", "EMPLOYEE_ID", "ACCOUNT_NUMBER", "URL")

# ---------------------------------------------------------------------------------------------------- inventories
# Invented for this corpus. Given names mix common and rare English names; family names are invented or rare.
GIVEN_F = ["Isolde", "Theodora", "Imogen", "Marguerite", "Philippa", "Rosalind", "Tabitha", "Verity", "Xanthe",
           "Zelda", "Beatrix", "Delphine", "Felicity", "Harriet", "Juniper", "Lorelei", "Nerissa", "Perpetua",
           "Sabrina", "Ursula", "Winifred", "Bronwyn", "Dorothea", "Fenella", "Henrietta", "Jocelyn", "Matilda",
           "Octavia", "Rhiannon", "Tamsin", "Vivienne", "Wilhelmina", "Yvette", "Anneliese", "Clementine",
           "Eleanora", "Gwendolyn", "Ingrid", "Katarina", "Marisol", "Ophelia", "Seraphina", "Valentina",
           "Yolanda", "Hazel", "Iris", "Nina", "Cora", "Mae", "Tess", "Ada", "Lola", "Bea", "Ivy", "June", "Elsa",
           "Nell", "Greta", "Pearl", "Maude", "Edith", "Sylvie", "Odette", "Leonie", "Ramona", "Celeste", "Dagny",
           "Elowen", "Freya", "Giselle", "Hilde", "Ione", "Kerensa", "Liesl", "Mirabel", "Noor", "Oriana", "Petra",
           "Quinlan", "Romilly", "Saoirse", "Thea", "Una", "Vesna", "Wren", "Ximena", "Yara", "Zara"]
GIVEN_M = ["Rowan", "Caspar", "Bartholomew", "Lucian", "Osric", "Quentin", "Silas", "Ulysses", "Wendell", "Yannick",
           "Ambrose", "Cormac", "Everett", "Gideon", "Ignatius", "Kieran", "Magnus", "Orson", "Rupert", "Thaddeus",
           "Vaughn", "Alaric", "Cedric", "Ezra", "Gareth", "Isidore", "Leopold", "Percival", "Sebastian", "Uriah",
           "Zachariah", "Barnaby", "Desmond", "Fitzgerald", "Horatio", "Jasper", "Lysander", "Niall", "Peregrine",
           "Rafferty", "Tobias", "Wesley", "Owen", "Miles", "Hugo", "Felix", "Jude", "Rhys", "Finn", "Hal", "Otis",
           "Reid", "Cyrus", "Boyd", "Amos", "Clyde", "Alder", "Perrin", "Lachlan", "Emrys", "Dashiell", "Caius",
           "Bram", "Anselm", "Florian", "Gustav", "Hamish", "Ivo", "Joaquin", "Kasimir", "Lorcan", "Matthias",
           "Nikolai", "Oswin", "Piers", "Quill", "Roderick", "Soren", "Tristan", "Ulric", "Valerian", "Wilfred",
           "Xavier", "Yusef", "Zane"]
FAMILY = ["Kestrelbury", "Brannick", "Winterhalde", "Finchwood", "Ostrowicz", "Quillanbrook", "Vauclerc",
          "Tregarec", "Halvorsen", "Ashcombe", "Thornquist", "Pembrook", "Ravelston", "Abernathy", "Blackwood",
          "Calloway", "Dunmore", "Ellsworth", "Fairweather", "Galbraith", "Hawthorne", "Ironside", "Jessup",
          "Kingsley", "Lockhart", "Merriweather", "Northcott", "Oakhurst", "Pendergast", "Quarrington",
          "Rutherford", "Stanhope", "Thistlewood", "Underhill", "Vandermeer", "Whitlock", "Yardley", "Zimmerlin",
          "Ashby", "Bellweather", "Cranston", "Daventry", "Edgecombe", "Farrow", "Grimshaw", "Holloway",
          "Inchbald", "Kettering", "Marlowe", "Nettleton", "Osgood", "Prendergast", "Quayle", "Ridgewell",
          "Sallow", "Tennant", "Upton", "Vickery", "Wainwright", "Yelverton", "Barrowcliffe", "Cottrell",
          "Dashwood", "Eastwick", "Fenwick", "Gresham", "Hartigan", "Iverson", "Joubert", "Kincaid", "Lanchester",
          "Mortlake", "Nightingale", "Orrell", "Pickering", "Rowntree", "Sedgwick", "Tallis", "Umber", "Verlaine",
          "Westbrook", "Yeardley", "Adegoke", "Chowdhury", "Nakashima", "Petrov", "Schneider", "Fernandes",
          "Haddad", "Ivanova", "Kowalchuk", "Lindgren", "Moreau", "Okafor", "Papadakis", "Ramaswamy", "Santoro",
          "Takahashi", "Varga", "Yilmaz", "Zielinski", "Bergstrom", "Castellanos", "Dimitriou", "Esposito",
          "Fontaine", "Guerrero", "Horvath", "Jansen", "Kovacs", "Laurent", "Mabaso", "Novak", "Oduya", "Pereira",
          "Quiroga", "Rasmussen", "Sorensen", "Tanaka", "Uribe", "Villanueva", "Wozniak", "Yamamoto", "Brightmoor"]
NICKNAMES = {"Theodora": "Teddy", "Bartholomew": "Bart", "Marguerite": "Margo", "Philippa": "Pip", "Rosalind": "Roz",
             "Sebastian": "Bas", "Henrietta": "Hettie", "Wilhelmina": "Billie", "Fitzgerald": "Fitz", "Gwendolyn": "Wendy",
             "Clementine": "Clem", "Eleanora": "Nora", "Isidore": "Izzy", "Leopold": "Leo", "Matilda": "Tilly",
             "Octavia": "Tavi", "Peregrine": "Perry", "Thaddeus": "Tad", "Ignatius": "Nash", "Dorothea": "Thea",
             "Percival": "Percy", "Zachariah": "Zach", "Anneliese": "Annie", "Desmond": "Des", "Winifred": "Winnie",
             "Katarina": "Kat", "Valentina": "Val", "Nikolai": "Nik", "Roderick": "Rod", "Magnus": "Mags"}
STREETS = ["Larkspur Avenue", "Juniper Hollow Road", "Thistle Lane", "Copperfield Street", "Marrowbone Drive",
           "Wexford Court", "Pinecrest Boulevard", "Harbor Mist Way", "Old Mill Terrace", "Ridgeback Trail",
           "Candlewick Road", "Foxglove Street", "Quarry Bend", "Saltmarsh Avenue", "Tanager Lane", "Umberline Way",
           "Vesper Street", "Willowmere Road", "Ashgrove Place", "Birchmount Drive"]
CITIES = [("Pellbrook", "OR", "97201"), ("Carverton", "OH", "43215"), ("New Harrow", "NJ", "07030"),
          ("Lindell Falls", "MN", "55401"), ("Port Avery", "WA", "98101"), ("Sagemont", "AZ", "85004"),
          ("Westlake Hollow", "TX", "78701"), ("Dunmere", "VT", "05401"), ("Marlow Heights", "MD", "20748"),
          ("Kessler City", "CO", "80202")]
MAIL_HOSTS = ["postwave.test", "mailharbor.test", "quietinbox.test", "lettercloud.test"]

# Ten exports: protagonist (given, family, sex), home organisation (name, legal form, short form, domain), industry words.
SETS = [
    dict(slug="isolde_halvorsen_dynamics", given="Isolde", family="Brannick", sex="F", org="Halvorsen Dynamics",
         form="Inc.", short="Halvorsen", domain="halvorsen-dynamics.test", prefix="HD", industry="drone surveying",
         mode="embed"),
    dict(slug="rowan_pellbrook_freight", given="Rowan", family="Kestrelbury", sex="M", org="Pellbrook Freight",
         form="LLC", short="Pellbrook Freight", domain="pellbrookfreight.test", prefix="PF", industry="freight",
         mode="drive"),
    dict(slug="theodora_thornquist_dental", given="Theodora", family="Pendergast", sex="F", org="Thornquist Dental Group",
         form="", short="Thornquist", domain="thornquistdental.test", prefix="TDG", industry="dental clinics",
         mode="embed"),
    dict(slug="caspar_sunmarrow_solar", given="Caspar", family="Winterhalde", sex="M", org="Sunmarrow Solar",
         form="Co.", short="Sunmarrow", domain="sunmarrow.test", prefix="SMS", industry="solar installation",
         mode="drive"),
    dict(slug="imogen_carverton_savings", given="Imogen", family="Ravelston", sex="F", org="Carverton Savings Bank",
         form="", short="Carverton Savings", domain="carvertonsavings.test", prefix="CSB", industry="regional banking",
         mode="embed"),
    dict(slug="lucian_harborlight_hotels", given="Lucian", family="Ashcombe", sex="M", org="Harborlight Hotels",
         form="Ltd", short="Harborlight", domain="harborlighthotels.test", prefix="HBH", industry="hotels",
         mode="drive"),
    dict(slug="verity_quillanbrook_press", given="Verity", family="Okafor", sex="F", org="Quillanbrook Legal Press",
         form="", short="Quillanbrook Press", domain="quillanbrookpress.test", prefix="QLP", industry="legal publishing",
         mode="embed"),
    dict(slug="silas_ember_roasters", given="Silas", family="Galbraith", sex="M", org="Ember & Vale Roasters",
         form="LLC", short="Ember & Vale", domain="embervale.test", prefix="EVR", industry="specialty coffee",
         mode="drive"),
    dict(slug="harriet_tanager_veterinary", given="Harriet", family="Nakashima", sex="F", org="Tanager Veterinary Network",
         form="", short="Tanager", domain="tanagervet.test", prefix="TVN", industry="veterinary clinics",
         mode="embed"),
    dict(slug="everett_westlake_water", given="Everett", family="Castellanos", sex="M", org="Westlake Water Advisory",
         form="LLP", short="Westlake Water", domain="westlakewater.test", prefix="WWA", industry="water utilities",
         mode="drive"),
]
EXTERNAL_ORGS = [("Brightmoor Logistics", "LLC"), ("Thistlewood Analytics", ""), ("Northcott Regional Supply", "Co."),
                 ("Marrowbone Capital Partners", ""), ("Saltmarsh Insurance Group", "Inc."), ("Vesper Print Works", ""),
                 ("Copperfield Technical Services", "Ltd"), ("Ridgeback Security", ""), ("Umberline Media", "LLC"),
                 ("Candlewick Office Interiors", ""), ("Foxglove Catering", "Co."), ("Quarry Bend Engineering", "Inc."),
                 ("Harbor Mist Shipping", ""), ("Old Mill Accounting", "LLP"), ("Birchmount Software", ""),
                 ("Tanager Lane Realty", "LLC"), ("Willowmere Staffing", ""), ("Ashgrove Translation Bureau", "")]
ROLES = ["Operations Manager", "Account Executive", "Field Technician", "Payroll Specialist", "Project Coordinator",
         "Compliance Analyst", "Regional Director", "Customer Success Lead", "Procurement Officer", "IT Administrator",
         "Marketing Associate", "Finance Controller", "Dispatcher", "Quality Inspector", "Legal Counsel",
         "Office Manager", "Scheduler", "Data Analyst", "Sales Representative", "Training Coordinator"]
TOPICS = ["the Q3 vendor review", "the onboarding checklist", "the office move", "the audit prep", "the fleet renewal",
          "the new scheduling tool", "the client kickoff", "the budget freeze", "the safety drill", "the holiday roster",
          "the invoice backlog", "the badge system rollout", "the renewal pricing", "the site survey", "the training week"]


# ---------------------------------------------------------------------------------------------------- roster

class Person:
    def __init__(self, cid: str, given: str, family: str, sex: str, nick: Optional[str], org: "Org", role: str,
                 email: str, personal_email: Optional[str], handle: str, uid: str, phone: str, phone2: Optional[str],
                 emp_id: Optional[str], account: Optional[str], address: str, city: tuple):
        self.cid, self.given, self.family, self.sex, self.nick = cid, given, family, sex, nick
        self.org, self.role, self.email, self.personal_email = org, role, email, personal_email
        self.handle, self.uid, self.phone, self.phone2 = handle, uid, phone, phone2
        self.emp_id, self.account, self.address, self.city = emp_id, account, address, city

    @property
    def full(self) -> str:
        return f"{self.given} {self.family}"

    @property
    def quoted(self) -> str:
        return f'{self.given} "{self.nick}" {self.family}' if self.nick else self.full


class Org:
    def __init__(self, oid: str, name: str, form: str, short: str, domain: str):
        self.oid, self.name, self.form, self.short, self.domain = oid, name, form, short, domain
        self.contacts: list[Person] = []
        self.address = ""
        self.city = ("", "", "")
        self.url = f"https://www.{domain}"
        self.account = ""

    @property
    def legal(self) -> str:
        return f"{self.name} {self.form}" if self.form else self.name


def phone_fmt(rng: random.Random, npa: str, line: str) -> str:
    styles = [f"({npa}) 555-{line}", f"{npa}-555-{line}", f"+1 {npa} 555 {line}", f"{npa}.555.{line}"]
    return rng.choice(styles)


def build_roster(cfg: dict, rng: random.Random) -> tuple[list[Person], list[Org], Org]:
    home = Org("org_home", cfg["org"], cfg["form"], cfg["short"], cfg["domain"])
    orgs = [home]
    for i, (name, form) in enumerate(rng.sample(EXTERNAL_ORGS, 6)):
        domain = re.sub(r"[^a-z]", "", name.lower().split()[0]) + ".test"
        o = Org(f"org_{i + 1}", name, form, name.split()[0], domain)
        orgs.append(o)
    # one deliberate homonym: a company named after a person's family name (person and organisation collide)
    homonym_family = rng.choice([f for f in FAMILY if f not in ("Halvorsen", "Brightmoor")])
    orgs.append(Org("org_homonym", f"{homonym_family} & Associates", "LLP", homonym_family, f"{homonym_family.lower()}law.test"))
    for o in orgs:
        o.city = rng.choice(CITIES)
        o.address = f"{rng.randint(100, 9800)} {rng.choice(STREETS)}"
        o.account = f"{rng.randint(10 ** 9, 10 ** 10 - 1)}"
    givens_f = [g for g in GIVEN_F if g != cfg["given"]]
    givens_m = [g for g in GIVEN_M if g != cfg["given"]]
    rng.shuffle(givens_f)
    rng.shuffle(givens_m)
    families = [f for f in FAMILY if f not in (cfg["family"], homonym_family, "Halvorsen", "Brightmoor")]
    rng.shuffle(families)
    people: list[Person] = []
    npa = rng.choice(["415", "312", "206", "617", "720", "503", "213", "646", "303", "512"])
    used_lines: set[str] = set()

    def line() -> str:
        while True:
            s = f"01{rng.randint(0, 99):02d}"
            if s not in used_lines:
                used_lines.add(s)
                return s

    def make(idx: int, given: str, family: str, sex: str, org: Org, internal: bool) -> Person:
        nick = NICKNAMES.get(given) if rng.random() < 0.8 else None
        handle_style = rng.choice(["gf", "g.f", "fg", "g_f", "gfam"])
        g, f = given.lower(), family.lower()
        handle = {"gf": g[0] + f, "g.f": f"{g}.{f}", "fg": f + g[0], "g_f": f"{g}_{f}", "gfam": g + f[:3]}[handle_style]
        email_style = rng.choice(["g.f", "gf", "f.g", "g"])
        local = {"g.f": f"{g}.{f}", "gf": g[0] + f, "f.g": f"{f}.{g}", "g": g}[email_style]
        email = f"{local}@{org.domain}"
        personal = f"{g}.{f}{rng.randint(2, 99)}@{rng.choice(MAIL_HOSTS)}" if rng.random() < 0.35 else None
        uid = f"U{rng.randint(0, 9)}{''.join(rng.choice('ABCDEFGHJKLMNPQRSTUVWXYZ0123456789') for _ in range(7))}"
        phone = phone_fmt(rng, npa, line())
        phone2 = phone_fmt(rng, rng.choice(["415", "312", "206"]), line()) if rng.random() < 0.3 else None
        emp_id = f"{cfg['prefix']}-{rng.randint(10000, 99999)}" if internal else None
        account = (f"ACCT-{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}" if rng.random() < 0.5
                   else f"{rng.randint(10 ** 7, 10 ** 8 - 1)}") if rng.random() < 0.45 else None
        city = rng.choice(CITIES)
        address = f"{rng.randint(10, 9800)} {rng.choice(STREETS)}"
        return Person(f"p{idx:02d}", given, family, sex, nick, org, rng.choice(ROLES), email, personal, handle, uid,
                      phone, phone2, emp_id, account, address, city)

    people.append(make(0, cfg["given"], cfg["family"], cfg["sex"], home, True))
    n_internal, n_external = rng.randint(11, 14), rng.randint(6, 9)
    for i in range(1, n_internal + n_external + 1):
        sex = rng.choice("FM")
        given = (givens_f if sex == "F" else givens_m).pop()
        family = families.pop()
        org = home if i <= n_internal else rng.choice(orgs[1:])
        people.append(make(i, given, family, sex, org, org is home))
    # the homonym person: a colleague whose family name is the homonym firm's name
    sex = rng.choice("FM")
    people.append(make(len(people), (givens_f if sex == "F" else givens_m).pop(), homonym_family, sex, home, True))
    for p in people:
        p.org.contacts.append(p)
    return people, orgs, home


# ---------------------------------------------------------------------------------------------------- text builder

class Piece:
    """A text with PII segments recorded as it is built."""

    def __init__(self):
        self.parts: list[str] = []
        self.spans: list[tuple[int, int, str, str, list[str]]] = []  # start, end, label, text, characters
        self.n = 0

    def t(self, s: str) -> "Piece":
        self.parts.append(s)
        self.n += len(s)
        return self

    def p(self, s: str, label: str, chars: list[str]) -> "Piece":
        self.spans.append((self.n, self.n + len(s), label, s, chars))
        return self.t(s)

    def name(self, p: Person, style: str = "full") -> "Piece":
        if style == "full":
            self.p(p.given, "NAME_GIVEN", [p.cid]).t(" ").p(p.family, "NAME_FAMILY", [p.cid])
        elif style == "quoted" and p.nick:
            self.p(p.given, "NAME_GIVEN", [p.cid]).t(' "').p(p.nick, "NAME_GIVEN", [p.cid]).t('" ') \
                .p(p.family, "NAME_FAMILY", [p.cid])
        elif style == "given":
            self.p(p.given, "NAME_GIVEN", [p.cid])
        elif style == "nick" and p.nick:
            self.p(p.nick, "NAME_GIVEN", [p.cid])
        elif style == "lower":
            self.p(p.given.lower(), "NAME_GIVEN", [p.cid])
        elif style == "lowernick" and p.nick:
            self.p(p.nick.lower(), "NAME_GIVEN", [p.cid])
        elif style == "family":
            self.p(p.family, "NAME_FAMILY", [p.cid])
        elif style == "lastfirst":
            self.p(p.family, "NAME_FAMILY", [p.cid]).t(", ").p(p.given, "NAME_GIVEN", [p.cid])
        elif style == "initial":
            self.p(p.given[0] + ".", "NAME_GIVEN", [p.cid]).t(" ").p(p.family, "NAME_FAMILY", [p.cid])
        elif style == "upper":
            self.p(p.given.upper(), "NAME_GIVEN", [p.cid]).t(" ").p(p.family.upper(), "NAME_FAMILY", [p.cid])
        else:
            return self.name(p, "full")
        return self

    def org(self, o: Org, style: str = "legal") -> "Piece":
        if style == "legal" and o.form:
            return self.p(o.legal, "ORGANIZATION", [o.oid])
        if style == "short":
            return self.p(o.short, "ORGANIZATION", [o.oid])
        if style == "lower":
            return self.p(o.short.lower(), "ORGANIZATION", [o.oid])
        if style == "upper":
            return self.p(o.name.upper(), "ORGANIZATION", [o.oid])
        return self.p(o.name, "ORGANIZATION", [o.oid])

    def email(self, p: Person, personal: bool = False) -> "Piece":
        return self.p(p.personal_email if personal and p.personal_email else p.email, "EMAIL_ADDRESS", [p.cid])

    def phone(self, p: Person, second: bool = False) -> "Piece":
        return self.p(p.phone2 if second and p.phone2 else p.phone, "PHONE_NUMBER", [p.cid])

    def mention(self, p: Person) -> "Piece":
        return self.p(f"<@{p.uid}>", "USERNAME", [p.cid])

    def handle(self, p: Person) -> "Piece":
        return self.p("@" + p.handle, "USERNAME", [p.cid])

    def address(self, p: Person) -> "Piece":
        return self.p(p.address, "LOCATION_ADDRESS", [p.cid]).t(f", {p.city[0]}, {p.city[1]} {p.city[2]}")

    def org_address(self, o: Org) -> "Piece":
        return self.p(o.address, "LOCATION_ADDRESS", [o.oid]).t(f", {o.city[0]}, {o.city[1]} {o.city[2]}")

    def emp(self, p: Person) -> "Piece":
        return self.p(p.emp_id, "EMPLOYEE_ID", [p.cid])

    def account(self, p: Person) -> "Piece":
        return self.p(p.account, "ACCOUNT_NUMBER", [p.cid])

    def org_account(self, o: Org) -> "Piece":
        return self.p(o.account, "ACCOUNT_NUMBER", [o.oid])

    def url(self, o: Org, path: str = "") -> "Piece":
        return self.p(o.url + path, "URL", [o.oid])

    def text(self) -> str:
        return "".join(self.parts)


# ---------------------------------------------------------------------------------------------------- e-mails

def email_bodies(rng: random.Random, people: list[Person], orgs: list[Org], home: Org, cfg: dict) -> list[dict]:
    """Returns dicts: sender, to (list), cc, subject, piece (body), attach (doc name or None)."""
    out = []
    internal = [p for p in people if p.org is home]
    external = [p for p in people if p.org is not home]
    me = people[0]

    def pick(pool, k):
        return rng.sample(pool, min(k, len(pool)))

    def signature(b: Piece, p: Person, long: bool = True) -> Piece:
        b.t("\n\n").t(rng.choice(["Best,", "Thanks,", "Regards,", "Cheers,"])).t("\n").name(p).t("\n")
        b.t(p.role).t(" | ").org(p.org, rng.choice(["legal", "plain"])).t("\n")
        if long:
            b.phone(p).t(" | ").email(p).t("\n")
            if p.emp_id and rng.random() < 0.5:
                b.t("Employee ID ").emp(p).t("\n")
            if rng.random() < 0.5:
                b.org_address(p.org).t("\n")
            if rng.random() < 0.4:
                b.url(p.org).t("\n")
        return b

    topics = rng.sample(TOPICS, 8)
    # 1. kickoff mail with a roster
    a, b_, c = pick(internal[1:], 3)
    ext = rng.choice(external)
    b = Piece()
    b.t("Hi all,\n\nKicking off ").t(topics[0]).t(" this week. Roles for the record:\n\n")
    for p in (a, b_, c):
        b.t("- ").name(p, "full").t(" (").t(p.role).t(", ").email(p).t(")\n")
    b.t("- ").name(ext, "full").t(" from ").org(ext.org, "legal").t(", our contact at the vendor (").phone(ext).t(")\n")
    b.t("\nThe shared folder is at ").url(home, "/projects/" + topics[0].split()[-1]).t(". ")
    b.t("Ping ").name(a, "given").t(" or me if a line item looks wrong.")
    signature(b, me)
    out.append(dict(sender=me, to=[a, b_, c], cc=[ext], subject=f"Kickoff: {topics[0]}", piece=b,
                    attach="kickoff_notes.docx"))
    # 2. reply from a colleague, quoting
    b = Piece()
    b.t("Thanks ").name(me, "given").t("! One correction: ").name(c, "family").t("'s extension changed, it is now ")
    b.phone(c, second=True).t(". Also ").name(b_, "nick" if b_.nick else "given").t(" is out until Thursday.\n\n")
    b.t("> Kicking off ").t(topics[0]).t(" this week.\n> Ping ").name(a, "given").t(" or me if a line item looks wrong.")
    signature(b, a, long=False)
    out.append(dict(sender=a, to=[me], cc=[b_, c], subject=f"Re: Kickoff: {topics[0]}", piece=b, attach=None))
    # 3. vendor invoice mail
    vendor = rng.choice([o for o in orgs[1:] if o.contacts])
    vp = rng.choice(vendor.contacts)
    fin = rng.choice(internal[1:])
    b = Piece()
    b.t("Dear ").name(fin, "given").t(",\n\nPlease find attached our statement for ").org(home, "plain")
    b.t(". The account reference on your side is ").org_account(vendor).t(". Remit to ")
    b.org(vendor, "legal").t(", ").org_address(vendor).t(".\n\nFor questions call me at ").phone(vp)
    b.t(" or write to ").email(vp).t(".")
    signature(b, vp)
    out.append(dict(sender=vp, to=[fin], cc=[], subject="Statement attached", piece=b, attach="statement.pdf"))
    # 4. HR mail with employee ids
    hr = rng.choice(internal[1:])
    newbie = rng.choice([p for p in internal if p is not hr and p.emp_id])
    b = Piece()
    b.t("Hello ").name(newbie, "given").t(",\n\nWelcome to ").org(home, "legal").t(". Your employee ID is ").emp(newbie)
    b.t(" and your badge will be ready at reception on Monday. Your workspace handle is ").handle(newbie)
    b.t(" and your mailbox ").email(newbie).t(" is active.\n\nIf anything is missing, ").name(hr, "given")
    b.t(" (").email(hr).t(") can help. Our office is at ").org_address(home).t(".")
    signature(b, hr)
    out.append(dict(sender=hr, to=[newbie], cc=[], subject="Welcome aboard", piece=b, attach=None))
    # 5. chatty internal mail with lower-case names and a personal address
    x, y = pick(internal[1:], 2)
    b = Piece()
    b.t("hey ").name(y, "lower").t(",\n\nquick one: can you send the slides for ").t(topics[1]).t(" to my personal mail (")
    b.email(x, personal=True if x.personal_email else False).t(") before friday? ").name(me, "lower")
    b.t(" wants to review them over the weekend.\n\nalso ").org(rng.choice(orgs[1:]), "lower")
    b.t(" called again about the renewal.\n\n").name(x, "lower")
    out.append(dict(sender=x, to=[y], cc=[], subject=f"slides for {topics[1]}", piece=b, attach=None))
    # 6. client escalation with the homonym firm
    hom = orgs[-1]
    homp = [p for p in people if p.family == hom.short][0]
    cl = rng.choice(external)
    b = Piece()
    b.t("Hi ").name(me, "given").t(",\n\n").org(hom, "legal").t(" sent the engagement letter; ")
    b.name(homp, "full").t(" from our team (no relation to the firm) will coordinate. ")
    b.t("The counterparty contact is ").name(cl, "quoted" if cl.nick else "full").t(" at ").org(cl.org, "plain")
    b.t(", reachable at ").phone(cl).t(".\n\nTheir portal: ").url(cl.org, "/portal").t(".")
    signature(b, rng.choice(internal[1:]))
    out.append(dict(sender=out[-1]["sender"], to=[me], cc=[homp], subject="Engagement letter", piece=b, attach=None))
    # 7. roster spreadsheet mail
    b = Piece()
    b.t("Team,\n\nThe updated contact roster is attached (").t("contact_roster.xlsx").t("). ")
    b.t("Please check your own row: name, employee ID, phone. ").name(rng.choice(internal[1:]), "lastfirst")
    b.t(" already flagged a wrong number.")
    signature(b, me)
    out.append(dict(sender=me, to=internal[1:5], cc=[], subject="Contact roster", piece=b, attach="contact_roster.xlsx"))
    # 8. finance mail with account numbers
    f1 = rng.choice([p for p in internal if p.account] or internal)
    b = Piece()
    b.t("Hi,\n\nReimbursement for ").name(f1, "full").t(" (employee ID ").p(f1.emp_id or "n/a", "EMPLOYEE_ID", [f1.cid]) \
        if f1.emp_id else b.t("Hi,\n\nReimbursement for ").name(f1, "full").t(" (")
    if f1.account:
        b.t(", account ").account(f1).t(")")
    else:
        b.t(")")
    b.t(" goes out Friday. The vendor list with account numbers is in ").t("vendor_accounts.csv").t(".\n\n")
    b.t("Questions to ").name(rng.choice(internal), "initial").t(".")
    signature(b, rng.choice(internal[1:]))
    out.append(dict(sender=out[-1]["sender"], to=[me], cc=[], subject="Reimbursements", piece=b,
                    attach="vendor_accounts.csv"))
    # 9. memo forward (pdf)
    b = Piece()
    b.t("Forwarding the memo from ").org(rng.choice(orgs[1:]), "plain").t(" about ").t(topics[2]).t(". ")
    b.t("Read page 2, ").name(rng.choice(external), "family").t(" quotes our old address ").org_address(home).t(".")
    signature(b, me, long=False)
    out.append(dict(sender=me, to=pick(internal[1:], 2), cc=[], subject=f"FW: memo on {topics[2]}", piece=b,
                    attach="site_memo.pdf"))
    # 10-14. short threads
    for k in range(5):
        s, r = pick(people, 2)
        b = Piece()
        b.t(rng.choice(["Hi ", "Hello ", "Dear "])).name(r, rng.choice(["given", "full"])).t(",\n\n")
        b.t(rng.choice(["Following up on ", "Quick note on ", "Status for "])).t(topics[3 + k]).t(": ")
        b.t(rng.choice(["we are on track.", "two items slipped.", "the vendor needs a PO.", "all signed off."]))
        if rng.random() < 0.6:
            b.t(" ").name(rng.choice(people), "full").t(" of ").org(rng.choice(orgs), rng.choice(["legal", "plain", "short"]))
            b.t(rng.choice([" will join the call.", " sent the revised quote.", " asked for the invoice."]))
        if rng.random() < 0.5:
            b.t(" Call me on ").phone(s).t(".")
        signature(b, s, long=rng.random() < 0.6)
        out.append(dict(sender=s, to=[r], cc=pick(people, rng.randint(0, 2)), subject=f"{topics[3 + k]}", piece=b,
                        attach=None))
    return out


# ---------------------------------------------------------------------------------------------------- slack

def slack_messages(rng: random.Random, people: list[Person], orgs: list[Org], home: Org) -> dict[str, list[dict]]:
    """channel -> list of dicts(sender, piece, file)"""
    internal = [p for p in people if p.org is home]
    external = [p for p in people if p.org is not home]
    me = people[0]
    chans: dict[str, list[dict]] = {"general": [], "ops": [], "finance": [], f"dm-{me.handle}": []}
    topics = rng.sample(TOPICS, 6)

    def say(chan: str, p: Person, piece: Piece, file: Optional[str] = None):
        chans[chan].append(dict(sender=p, piece=piece, file=file))

    # general: greetings, mentions, lower-case names, handles
    for i in range(rng.randint(14, 18)):
        s = rng.choice(internal)
        o = rng.choice([q for q in internal if q is not s])
        b = Piece()
        style = rng.choice(["mention", "lower", "handle", "nick", "plain"])
        if style == "mention":
            b.mention(o).t(" ").t(rng.choice(["can you look at ", "any update on ", "thanks for "])).t(rng.choice(topics)).t("?")
        elif style == "lower":
            b.t(rng.choice(["thanks ", "cc ", "morning ", "agreed with "])).name(o, "lower").t(", ").t(rng.choice(["ship it", "let's sync at 3", "i'll take it", "good catch"]))
        elif style == "handle":
            b.handle(o).t(" ").t(rng.choice(["owns this one", "is on PTO", "has the doc", "will post the recap"]))
        elif style == "nick" and o.nick:
            b.t("ask ").name(o, "lowernick").t(" about ").t(rng.choice(topics))
        else:
            b.t(rng.choice(["heads up: ", "fyi ", "reminder: "])).org(rng.choice(orgs[1:]), rng.choice(["plain", "short"])).t(rng.choice([" visit tomorrow", " invoice is due", " signed the renewal", " moved offices"]))
        if rng.random() < 0.25:
            b.t(" &amp; ").t(rng.choice(["keep it short", "no slides please", "bring numbers"]))
        say("general", s, b)
    # a URL message, wrapped in <> as Slack does
    b = Piece()
    b.t("the vendor portal moved: &lt;").url(rng.choice(orgs[1:]), "/login").t("&gt;")
    say("general", rng.choice(internal), b)
    # ops: coordination with an external, phone numbers and addresses
    for i in range(rng.randint(12, 16)):
        s = rng.choice(internal)
        ext = rng.choice(external)
        b = Piece()
        kind = rng.choice(["phone", "address", "name", "mention2", "org", "emp"])
        if kind == "phone":
            b.t("call ").name(ext, "given").t(" at ").phone(ext).t(" before you send the crew")
        elif kind == "address":
            b.t("delivery goes to ").org_address(ext.org).t(" (ask for ").name(ext, "family").t(")")
        elif kind == "name":
            b.name(ext, "full").t(" from ").org(ext.org, rng.choice(["plain", "legal"])).t(" confirmed ").t(rng.choice(topics))
        elif kind == "mention2":
            b.mention(rng.choice(internal)).t(" ").mention(rng.choice(internal)).t(" please review ").t(rng.choice(topics))
        elif kind == "org":
            b.t(rng.choice(["quote from ", "PO raised for ", "meeting with "])).org(ext.org, rng.choice(["plain", "upper", "short"])).t(" is in the folder")
        else:
            p = rng.choice([q for q in internal if q.emp_id])
            b.t("badge for ").name(p, "full").t(" (").emp(p).t(") reprinted")
        say("ops", s, b)
    b = Piece()
    b.t("site memo uploaded, see attachment")
    say("ops", me, b, file="site_memo.pdf")
    # finance: accounts, roster mentions
    for i in range(rng.randint(8, 12)):
        s = rng.choice(internal)
        b = Piece()
        kind = rng.choice(["acct", "orgacct", "roster", "lastfirst", "email"])
        if kind == "acct":
            p = rng.choice([q for q in people if q.account] or people)
            if p.account:
                b.t("reimbursement to ").name(p, "full").t(", account ").account(p).t(", approved")
            else:
                b.t("reimbursement to ").name(p, "full").t(" approved")
        elif kind == "orgacct":
            o = rng.choice(orgs[1:])
            b.t("pay ").org(o, "legal").t(" against ").org_account(o)
        elif kind == "roster":
            b.t("roster v2 is up: ").name(rng.choice(internal), "lastfirst").t(" and ").name(rng.choice(internal), "lastfirst").t(" moved teams")
        elif kind == "lastfirst":
            b.name(rng.choice(people), "lastfirst").t(" still has no cost centre")
        else:
            p = rng.choice(people)
            b.t("send the statement to ").email(p).t(" (").name(p, "given").t(")")
        say("finance", s, b)
    b = Piece()
    b.t("vendor accounts csv attached")
    say("finance", rng.choice(internal), b, file="vendor_accounts.csv")
    # dm: casual, personal emails, nicknames
    other = rng.choice(internal[1:])
    for i in range(rng.randint(6, 9)):
        s = rng.choice([me, other])
        r = other if s is me else me
        b = Piece()
        kind = rng.choice(["lower", "personal", "nick", "plain"])
        if kind == "lower":
            b.t(rng.choice(["hey ", "thx ", "ok "])).name(r, "lower").t(rng.choice([", lunch?", " see you at 2", " i sent it"]))
        elif kind == "personal" and s.personal_email:
            b.t("use my personal one: ").email(s, personal=True)
        elif kind == "nick" and r.nick:
            b.name(r, "lowernick").t(rng.choice([" you around?", " call me", " the doc is wrong"]))
        else:
            b.t(rng.choice(["did ", "has "])).name(rng.choice(people), "family").t(rng.choice([" reply?", " signed?", " called back?"]))
        say(f"dm-{me.handle}", s, b)
    return chans


# ---------------------------------------------------------------------------------------------------- documents

def doc_kickoff_docx(rng: random.Random, people: list[Person], orgs: list[Org], home: Org, path: Path) -> list[tuple]:
    """Returns the planted PII (text, label, chars) list; the gold is located in the extracted text afterwards."""
    import docx

    planted: list[tuple] = []
    d = docx.Document()
    internal = [p for p in people if p.org is home]
    d.add_heading(f"Kickoff notes", 0)
    lead = people[0]
    d.add_paragraph(f"Prepared by {lead.full} ({lead.email}) for {home.legal}.")
    planted += [(lead.given, "NAME_GIVEN", [lead.cid]), (lead.family, "NAME_FAMILY", [lead.cid]),
                (lead.email, "EMAIL_ADDRESS", [lead.cid]), (home.legal, "ORGANIZATION", [home.oid])]
    ext = rng.sample([p for p in people if p.org is not home], 3)
    d.add_paragraph("Attendees")
    tbl = d.add_table(rows=1, cols=4)
    tbl.style = "Table Grid"
    for i, h in enumerate(("Name", "Role", "Email", "Phone")):
        tbl.rows[0].cells[i].text = h
    for p in internal[1:6] + ext:
        row = tbl.add_row().cells
        row[0].text, row[1].text, row[2].text, row[3].text = p.full, p.role, p.email, p.phone
        planted += [(p.given, "NAME_GIVEN", [p.cid]), (p.family, "NAME_FAMILY", [p.cid]),
                    (p.email, "EMAIL_ADDRESS", [p.cid]), (p.phone, "PHONE_NUMBER", [p.cid])]
    d.add_paragraph("Decisions")
    v = ext[0]
    d.add_paragraph(f"{v.org.legal} delivers the first batch to {home.address}, {home.city[0]}, {home.city[1]} "
                    f"{home.city[2]}. Contact on their side: {v.family}, {v.given} ({v.phone}).")
    planted += [(v.org.legal, "ORGANIZATION", [v.org.oid]), (home.address, "LOCATION_ADDRESS", [home.oid]),
                (v.family, "NAME_FAMILY", [v.cid]), (v.given, "NAME_GIVEN", [v.cid]), (v.phone, "PHONE_NUMBER", [v.cid])]
    w = internal[2]
    d.add_paragraph(f"{w.given} (employee ID {w.emp_id}) owns the budget tracker at {home.url}/budget.")
    planted += [(w.given, "NAME_GIVEN", [w.cid]), (w.emp_id, "EMPLOYEE_ID", [w.cid]), (home.url + "/budget", "URL", [home.oid])]
    o2 = rng.choice(orgs[1:-1])
    d.add_paragraph(f"Open question: does {o2.short} still invoice through {o2.legal}? {internal[3].given} to confirm.")
    planted += [(o2.short, "ORGANIZATION", [o2.oid]), (o2.legal, "ORGANIZATION", [o2.oid]),
                (internal[3].given, "NAME_GIVEN", [internal[3].cid])]
    d.core_properties.created = d.core_properties.modified = BUILD_TIME  # byte-for-byte rebuilds
    d.save(str(path))
    _pin_zip(path)
    return planted


def doc_roster_xlsx(rng: random.Random, people: list[Person], home: Org, path: Path) -> list[tuple]:
    import openpyxl

    planted: list[tuple] = []
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Roster"
    ws.append(["Name", "Title", "Organisation", "Email", "Phone", "Employee ID", "Account"])
    for p in [q for q in people if q.org is home]:
        ws.append([p.full, p.role, p.org.name, p.email, p.phone, p.emp_id or "", p.account or ""])
        planted += [(p.given, "NAME_GIVEN", [p.cid]), (p.family, "NAME_FAMILY", [p.cid]), (p.org.name, "ORGANIZATION", [home.oid]),
                    (p.email, "EMAIL_ADDRESS", [p.cid]), (p.phone, "PHONE_NUMBER", [p.cid])]
        if p.emp_id:
            planted.append((p.emp_id, "EMPLOYEE_ID", [p.cid]))
        if p.account:
            planted.append((p.account, "ACCOUNT_NUMBER", [p.cid]))
    ws2 = wb.create_sheet("Handles")
    ws2.append(["Handle", "Last, First", "Personal email"])
    for p in [q for q in people if q.org is home][:8]:
        ws2.append(["@" + p.handle, f"{p.family}, {p.given}", p.personal_email or ""])
        planted += [("@" + p.handle, "USERNAME", [p.cid]), (p.family, "NAME_FAMILY", [p.cid]), (p.given, "NAME_GIVEN", [p.cid])]
        if p.personal_email:
            planted.append((p.personal_email, "EMAIL_ADDRESS", [p.cid]))
    wb.properties.created = wb.properties.modified = BUILD_TIME  # byte-for-byte rebuilds
    wb.save(str(path))
    _pin_zip(path)
    return planted


def doc_vendors_csv(rng: random.Random, people: list[Person], orgs: list[Org], home: Org, path: Path) -> list[tuple]:
    planted: list[tuple] = []
    with path.open("w", encoding="utf-8", newline="") as h:
        w = csv.writer(h)
        w.writerow(["vendor", "contact", "contact_email", "contact_phone", "account_number", "remit_address", "website"])
        for o in orgs[1:]:
            c = o.contacts[0] if o.contacts else None
            w.writerow([o.legal, c.full if c else "", c.email if c else "", c.phone if c else "", o.account,
                        f"{o.address}, {o.city[0]}, {o.city[1]} {o.city[2]}", o.url])
            planted += [(o.legal, "ORGANIZATION", [o.oid]), (o.account, "ACCOUNT_NUMBER", [o.oid]),
                        (o.address, "LOCATION_ADDRESS", [o.oid]), (o.url, "URL", [o.oid])]
            if c:
                planted += [(c.given, "NAME_GIVEN", [c.cid]), (c.family, "NAME_FAMILY", [c.cid]),
                            (c.email, "EMAIL_ADDRESS", [c.cid]), (c.phone, "PHONE_NUMBER", [c.cid])]
    return planted


#: cupsfilter wraps a text line at 80 columns, in the middle of a word: every line of a PDF stays shorter, so that no
#: planted value is ever cut (the gold locator needs the exact string in the extracted text).
PDF_MAX_LINE = 74
#: One fixed timestamp for every document property, so that a rebuild gives the same bytes (the text, the names and
#: the offsets are seeded; without this the docx/xlsx writers and the PDF renderer stamp the build time).
BUILD_TIME = datetime(2026, 3, 2, 9, 0, 0)
_PDF_DATE_RE = re.compile(rb"/(CreationDate|ModDate) \(D:\d{14}")
_PDF_ID_RE = re.compile(rb"/ID \[ <([0-9a-fA-F]{32})>\s*<([0-9a-fA-F]{32})> \]")


def _pin_zip(path: Path) -> None:
    """Rewrite an OOXML container (docx, xlsx) with one fixed timestamp on every entry: the writers stamp the build
    time into the zip headers, which would change the bytes of every rebuild."""
    import zipfile

    src = path.read_bytes()
    stamp = BUILD_TIME.strftime("%Y-%m-%dT%H:%M:%SZ")
    with zipfile.ZipFile(io.BytesIO(src)) as zin, io.BytesIO() as buf:
        with zipfile.ZipFile(buf, "w") as zout:
            for item in zin.infolist():
                info = zipfile.ZipInfo(item.filename, date_time=BUILD_TIME.timetuple()[:6])
                info.compress_type = item.compress_type
                info.external_attr = item.external_attr
                data = zin.read(item.filename)
                if item.filename == "docProps/core.xml":  # the writers re-stamp "modified" at save time
                    data = re.sub(rb"(<dcterms:(?:created|modified)[^>]*>)[^<]*(</dcterms:(?:created|modified)>)",
                                  lambda m: m.group(1) + stamp.encode("ascii") + m.group(2), data)
                zout.writestr(info, data)
        path.write_bytes(buf.getvalue())


def _pin_pdf(path: Path, text: str) -> None:
    """Replace the renderer's timestamps and document id by values derived from the content, byte length kept, so
    that the cross-reference offsets stay valid and two renders of one text give one file."""
    data = path.read_bytes()
    stamp = BUILD_TIME.strftime("%Y%m%d%H%M%S").encode("ascii")
    data = _PDF_DATE_RE.sub(lambda m: b"/" + m.group(1) + b" (D:" + stamp, data)
    ident = hashlib.sha256(text.encode("utf-8")).hexdigest()[:32].encode("ascii")
    data = _PDF_ID_RE.sub(b"/ID [ <" + ident + b"> <" + ident + b"> ]", data)
    path.write_bytes(data)


def _cups_pdf(text: str, path: Path) -> None:
    long = [(i, len(ln)) for i, ln in enumerate(text.split("\n")) if len(ln) > PDF_MAX_LINE]
    if long:
        raise RuntimeError(f"PDF line too long for cupsfilter (line index, length): {long}, max {PDF_MAX_LINE}")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as h:
        h.write(text)
        tmp = h.name
    try:
        with path.open("wb") as out:
            r = subprocess.run(["cupsfilter", "-i", "text/plain", "-m", "application/pdf", tmp], stdout=out,
                               stderr=subprocess.DEVNULL)
        if r.returncode != 0 or path.stat().st_size == 0:
            raise RuntimeError("cupsfilter failed")
        _pin_pdf(path, text)
    finally:
        Path(tmp).unlink(missing_ok=True)


def doc_statement_pdf(rng: random.Random, people: list[Person], orgs: list[Org], home: Org, path: Path) -> list[tuple]:
    vendor = rng.choice([o for o in orgs[1:] if o.contacts])
    vp = vendor.contacts[0]
    to = rng.choice([p for p in people if p.org is home])
    lines = [f"{vendor.legal}", f"{vendor.address}", f"{vendor.city[0]}, {vendor.city[1]} {vendor.city[2]}", "",
             "STATEMENT OF ACCOUNT", "", f"Bill to: {home.legal}", f"Attn: {to.full} ({to.role})",
             f"{home.address}, {home.city[0]}, {home.city[1]} {home.city[2]}", "",
             f"Customer account: {vendor.account}", f"Your reference: {to.emp_id or 'n/a'}", "",
             "Date        Description                 Amount", ]
    for i in range(5):
        lines.append(f"2026-0{rng.randint(1, 9)}-{rng.randint(10, 28)}  Service visit, week {i + 1:>2}          ${rng.randint(200, 4800)}.00")
    lines += ["", f"Questions: {vp.full}", f"Phone: {vp.phone}", f"E-mail: {vp.email}",
              f"Online: {vendor.url}/statements", "", f"Prepared by {vp.given} for {vendor.short}."]
    _cups_pdf("\n".join(lines) + "\n", path)
    planted = [(vendor.legal, "ORGANIZATION", [vendor.oid]), (vendor.address, "LOCATION_ADDRESS", [vendor.oid]),
               (home.legal, "ORGANIZATION", [home.oid]), (to.given, "NAME_GIVEN", [to.cid]), (to.family, "NAME_FAMILY", [to.cid]),
               (home.address, "LOCATION_ADDRESS", [home.oid]), (vendor.account, "ACCOUNT_NUMBER", [vendor.oid]),
               (vp.given, "NAME_GIVEN", [vp.cid]), (vp.family, "NAME_FAMILY", [vp.cid]), (vp.phone, "PHONE_NUMBER", [vp.cid]),
               (vp.email, "EMAIL_ADDRESS", [vp.cid]), (vendor.url + "/statements", "URL", [vendor.oid]),
               (vendor.short, "ORGANIZATION", [vendor.oid])]
    if to.emp_id:
        planted.append((to.emp_id, "EMPLOYEE_ID", [to.cid]))
    return planted


def doc_memo_pdf(rng: random.Random, people: list[Person], orgs: list[Org], home: Org, path: Path) -> list[tuple]:
    o = rng.choice(orgs[1:-1])
    author = o.contacts[0] if o.contacts else rng.choice(people)
    internal = [p for p in people if p.org is home]
    a, b = rng.sample(internal, 2)
    lines = [f"{o.name}", "MEMORANDUM", "", f"To: {a.full}, {home.name}", f"Cc: {b.family}, {b.given}",
             f"From: {author.full}", f"Re: site visit", "",
             "We visited the premises at",
             f"{home.address}, {home.city[0]}",
             f"on the agreed date. {a.given} walked us through",
             f"the loading area; {b.given.upper()} {b.family.upper()}",
             "joined for the second half.",
             "", "Findings", "1. Access control works; badge readers logged two visitors.",
             f"2. The emergency contact sheet lists {a.phone}",
             f"   for {a.family} and {b.phone} for {b.family}.",
             f"3. Deliveries from {o.legal}",
             "   will use the rear entrance from next month.", "",
             f"Our invoice goes to account {home.account}.",
             f"Your purchase order should quote {o.short}.", "",
             f"{author.full}", f"{author.role}, {o.legal}", f"{author.email} | {author.phone}", f"{o.url}"]
    _cups_pdf("\n".join(lines) + "\n", path)
    planted = [(o.name, "ORGANIZATION", [o.oid]), (a.given, "NAME_GIVEN", [a.cid]), (a.family, "NAME_FAMILY", [a.cid]),
               (home.name, "ORGANIZATION", [home.oid]), (b.family, "NAME_FAMILY", [b.cid]), (b.given, "NAME_GIVEN", [b.cid]),
               (author.given, "NAME_GIVEN", [author.cid]), (author.family, "NAME_FAMILY", [author.cid]),
               (home.address, "LOCATION_ADDRESS", [home.oid]), (b.given.upper(), "NAME_GIVEN", [b.cid]),
               (b.family.upper(), "NAME_FAMILY", [b.cid]), (a.phone, "PHONE_NUMBER", [a.cid]), (b.phone, "PHONE_NUMBER", [b.cid]),
               (o.legal, "ORGANIZATION", [o.oid]), (home.account, "ACCOUNT_NUMBER", [home.oid]), (o.short, "ORGANIZATION", [o.oid]),
               (author.email, "EMAIL_ADDRESS", [author.cid]), (author.phone, "PHONE_NUMBER", [author.cid]), (o.url, "URL", [o.oid])]
    return planted


DOC_BUILDERS = {"kickoff_notes.docx": doc_kickoff_docx, "contact_roster.xlsx": doc_roster_xlsx,
                "vendor_accounts.csv": doc_vendors_csv, "statement.pdf": doc_statement_pdf, "site_memo.pdf": doc_memo_pdf}
MIME = {".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".csv": "text/csv",
        ".pdf": "application/pdf"}


# ---------------------------------------------------------------------------------------------------- writers

def write_eml(path: Path, msg_id: str, sender: Person, to: list[Person], cc: list[Person], subject: str, when: datetime,
              body: str, attachment: Optional[tuple[str, bytes]], in_reply_to: Optional[str]) -> None:
    def addr(p: Person) -> str:
        return f"{p.full} <{p.email}>"

    headers = [f"From: {addr(sender)}", f"To: {', '.join(addr(p) for p in to)}"]
    if cc:
        headers.append(f"Cc: {', '.join(addr(p) for p in cc)}")
    headers += [f"Subject: {subject}", f"Date: {when.strftime('%a, %d %b %Y %H:%M:%S +0000')}",
                f"Message-ID: <{msg_id}@{sender.org.domain}>"]
    if in_reply_to:
        headers.append(f"In-Reply-To: <{in_reply_to}@{sender.org.domain}>")
    headers.append("MIME-Version: 1.0")
    crlf_body = body.replace("\r\n", "\n").replace("\n", "\r\n")
    if attachment is None:
        headers += ["Content-Type: text/plain; charset=utf-8", "Content-Transfer-Encoding: 8bit"]
        raw = "\r\n".join(headers) + "\r\n\r\n" + crlf_body + "\r\n"
        path.write_bytes(raw.encode("utf-8"))
        return
    name, payload = attachment
    boundary = "=_holdout_" + hashlib.sha1(msg_id.encode()).hexdigest()[:16]
    headers.append(f'Content-Type: multipart/mixed; boundary="{boundary}"')
    b64 = base64.encodebytes(payload).decode("ascii").replace("\n", "\r\n")
    raw = ("\r\n".join(headers) + "\r\n\r\n" + f"--{boundary}\r\n" + "Content-Type: text/plain; charset=utf-8\r\n"
           + "Content-Transfer-Encoding: 8bit\r\n\r\n" + crlf_body + "\r\n" + f"--{boundary}\r\n"
           + f'Content-Type: {MIME[Path(name).suffix]}; name="{name}"\r\n' + "Content-Transfer-Encoding: base64\r\n"
           + f'Content-Disposition: attachment; filename="{name}"\r\n\r\n' + b64 + f"--{boundary}--\r\n")
    path.write_bytes(raw.encode("utf-8"))


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


# ---------------------------------------------------------------------------------------------------- gold location

def _find_all(text: str, needle: str) -> list[int]:
    out, i = [], 0
    while True:
        j = text.find(needle, i)
        if j < 0:
            return out
        out.append(j)
        i = j + 1


def _word_bounded(text: str, s: int, e: int, needle: str) -> bool:
    if needle[:1].isalnum() and s > 0 and (text[s - 1].isalnum() or text[s - 1] == "@"):
        return False
    if needle[-1:].isalnum() and e < len(text) and (text[e].isalnum() or text[e] == "@"):
        return False
    return True


def locate_planted(text: str, planted: list[tuple]) -> list[tuple[int, int, str, str, list[str]]]:
    """Every occurrence of every planted string in ``text`` (longest strings first, no overlaps, on word
    boundaries). ``planted`` is in writing order, so when one surface was planted with two labels (the homonym:
    a family name that is also a company's short name) the i-th occurrence in the text takes the i-th planted
    entry; extra occurrences take the last entry of that surface."""
    taken: list[tuple[int, int]] = []
    entries: dict[str, list[tuple[str, list[str]]]] = {}
    for s, label, chars in planted:
        if s:
            entries.setdefault(s, []).append((label, chars))
    starts: dict[str, list[int]] = {}
    for needle in sorted(entries, key=len, reverse=True):
        found = []
        for s in _find_all(text, needle):
            e = s + len(needle)
            if not _word_bounded(text, s, e, needle):
                continue
            if any(s < te and ts < e for ts, te in taken):
                continue
            taken.append((s, e))
            found.append(s)
        starts[needle] = sorted(found)
    spans = []
    for needle, labelled in entries.items():
        for i, s in enumerate(starts[needle]):
            label, chars = labelled[min(i, len(labelled) - 1)]
            spans.append((s, s + len(needle), label, needle, chars))
    spans.sort()
    return spans


def exact_spans(text: str, recorded: list[tuple[int, int, str, str, list[str]]]) -> Optional[list]:
    """The spans a :class:`Piece` recorded while the text was written, when the unit text read back from the
    export is that very text (e-mail bodies and Slack messages); None when it is not."""
    for s, e, _label, surface, _chars in recorded:
        if text[s:e] != surface:
            return None
    return sorted(recorded)


# ---------------------------------------------------------------------------------------------------- one set

def build_set(cfg: dict, out: Path, set_no: int) -> dict:
    rng = random.Random(f"holdout-en-{set_no}-{cfg['slug']}")
    people, orgs, home = build_roster(cfg, rng)
    task = out / "tasks" / cfg["slug"]
    gt_dir = out / "ground_truth" / cfg["slug"]
    for d in (task, gt_dir):
        if d.exists():
            shutil.rmtree(d)
    (task / "email").mkdir(parents=True)
    (task / "slack").mkdir(parents=True)
    embed = cfg["mode"] == "embed"
    # documents first (attachments need the bytes)
    docs: dict[str, tuple[bytes, list[tuple]]] = {}
    with tempfile.TemporaryDirectory() as td:
        for name, builder in DOC_BUILDERS.items():
            p = Path(td) / name
            if name == "kickoff_notes.docx":
                planted = builder(rng, people, orgs, home, p)
            elif name == "contact_roster.xlsx":
                planted = builder(rng, people, home, p)
            else:
                planted = builder(rng, people, orgs, home, p)
            docs[name] = (p.read_bytes(), planted)
    # planted PII per unit key: (kind, path, container part or pointer); message units also keep the exact
    # offsets the Piece recorded
    planted_by_unit: dict[tuple, list[tuple]] = defaultdict(list)
    recorded_by_unit: dict[tuple, list[tuple]] = {}
    meta_by_unit: dict[tuple, dict] = {}
    base = datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)
    # e-mails
    mails = email_bodies(rng, people, orgs, home, cfg)
    attached_in_mail: set[str] = set()
    for i, m in enumerate(mails):
        msg_id = f"m{set_no:02d}{i:03d}{hashlib.sha1(m['subject'].encode()).hexdigest()[:8]}"
        when = base + timedelta(days=i, hours=rng.randint(0, 8), minutes=rng.randint(0, 59))
        attachment = None
        if embed and m["attach"] and m["attach"] not in attached_in_mail:
            attachment = (m["attach"], docs[m["attach"]][0])
            attached_in_mail.add(m["attach"])
        body = m["piece"].text()
        rel = f"email/{msg_id}.eml"
        write_eml(task / rel, msg_id, m["sender"], m["to"], m["cc"], m["subject"], when, body, attachment,
                  in_reply_to=None if i == 0 or not m["subject"].startswith("Re:") else f"m{set_no:02d}{i - 1:03d}"
                  + hashlib.sha1(mails[i - 1]['subject'].encode()).hexdigest()[:8])
        key = ("eml", rel, None)
        planted_by_unit[key] = [(t, l, c) for _s, _e, l, t, c in m["piece"].spans]
        recorded_by_unit[key] = list(m["piece"].spans)
        meta_by_unit[key] = {"row_id": msg_id, "from": {"name": m["sender"].full, "email": m["sender"].email},
                             "to": [{"name": p.full, "email": p.email} for p in m["to"]],
                             "cc": [{"name": p.full, "email": p.email} for p in m["cc"]],
                             "subject": m["subject"], "datetime": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "thread_id": msg_id if not m["subject"].startswith("Re:") else f"thread-{i - 1}"}
        if attachment is not None:
            akey = (rs.DOC_EXT[Path(m["attach"]).suffix], rel, 0)
            planted_by_unit[akey] = docs[m["attach"]][1]
            meta_by_unit[akey] = {"row_id": f"{msg_id}-att0", "filename": m["attach"],
                                  "format": Path(m["attach"]).suffix[1:], "mime_type": MIME[Path(m["attach"]).suffix],
                                  "attached_to": {"kind": "email", "row_id": msg_id}}
    # slack
    chans = slack_messages(rng, people, orgs, home)
    users = [{"id": p.uid, "name": p.handle, "real_name": p.full, "deleted": False,
              "profile": {"real_name": p.full, "display_name": p.handle, "email": p.email, "title": p.role}}
             for p in people if p.org is home]
    (task / "slack" / "users.json").write_text(json.dumps(users, indent=1), encoding="utf-8")
    (task / "slack" / "channels.json").write_text(json.dumps(
        [{"id": f"C{int(hashlib.sha1(c.encode('utf-8')).hexdigest(), 16) % 10 ** 8:08d}", "name": c,
          "members": [u["id"] for u in users]} for c in chans],
        indent=1), encoding="utf-8")
    slack_files_used: set[str] = set()
    for ci, (chan, msgs) in enumerate(chans.items()):
        cdir = task / "slack" / chan
        cdir.mkdir(parents=True, exist_ok=True)
        days: dict[str, list[dict]] = defaultdict(list)
        for mi, m in enumerate(msgs):
            day = (base + timedelta(days=(mi * 3) // max(1, len(msgs)) * 2)).strftime("%Y-%m-%d")
            ts = f"{int((base + timedelta(days=mi)).timestamp()) + mi * 37}.{rng.randint(100000, 999999):06d}"
            p = m["sender"]
            row = {"type": "message", "user": p.uid, "ts": ts, "client_msg_id": hashlib.sha1(ts.encode()).hexdigest()[:36],
                   "text": m["piece"].text(), "user_profile": {"real_name": p.full, "display_name": p.handle},
                   "team": "T0HOLDOUT"}
            if m["file"] and embed and m["file"] not in slack_files_used and m["file"] not in attached_in_mail:
                fid = f"F{hashlib.sha1((chan + m['file']).encode()).hexdigest()[:8].upper()}"
                adir = cdir / "attachments"
                adir.mkdir(exist_ok=True)
                (adir / f"{fid}-{m['file']}").write_bytes(docs[m["file"]][0])
                row["files"] = [{"id": fid, "name": m["file"], "mimetype": MIME[Path(m["file"]).suffix]}]
                slack_files_used.add(m["file"])
                akey = (rs.DOC_EXT[Path(m["file"]).suffix], f"slack/{chan}/attachments/{fid}-{m['file']}", None)
                planted_by_unit[akey] = docs[m["file"]][1]
                meta_by_unit[akey] = {"row_id": fid, "filename": m["file"], "format": Path(m["file"]).suffix[1:],
                                      "mime_type": MIME[Path(m["file"]).suffix],
                                      "attached_to": {"kind": "slack", "row_id": ts, "channel": chan}}
            days[day].append((row, m))
        for day, rows in days.items():
            rel = f"slack/{chan}/{day}.json"
            (cdir / f"{day}.json").write_text(json.dumps([r for r, _m in rows], indent=1, ensure_ascii=False),
                                              encoding="utf-8")
            for i, (r, m) in enumerate(rows):
                key = ("slack", rel, f"/{i}/text")
                planted_by_unit[key] = [(t, l, c) for _s, _e, l, t, c in m["piece"].spans]
                recorded_by_unit[key] = list(m["piece"].spans)
                meta_by_unit[key] = {"row_id": r["ts"], "from": {"user_id": r["user"], "name": m["sender"].full},
                                     "channel": chan, "datetime": day + "T09:00:00Z", "thread_ts": r["ts"]}
    # drive (drive sets: every document; embed sets: the documents no message carried)
    drive_docs = [n for n in docs if not embed or (n not in attached_in_mail and n not in slack_files_used)]
    if drive_docs:
        (task / "drive").mkdir(exist_ok=True)
        listing = []
        for n in drive_docs:
            payload = docs[n][0]
            (task / "drive" / n).write_bytes(payload)
            listing.append({"id": hashlib.sha1(n.encode()).hexdigest()[:24], "name": n, "mimeType": MIME[Path(n).suffix],
                            "size": str(len(payload)), "md5Checksum": md5(payload),
                            "createdTime": base.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "modifiedTime": base.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "owners": [{"displayName": people[0].full, "emailAddress": people[0].email}],
                            "webViewLink": f"https://drive.{home.domain}/file/d/{hashlib.sha1(n.encode()).hexdigest()[:24]}/view"})
            key = (rs.DOC_EXT[Path(n).suffix], f"drive/{n}", None)
            planted_by_unit[key] = docs[n][1]
            meta_by_unit[key] = {"row_id": listing[-1]["id"], "filename": n, "format": Path(n).suffix[1:],
                                 "mime_type": MIME[Path(n).suffix], "attached_to": None}
        (task / "drive" / "files.json").write_text(json.dumps({"kind": "drive#fileList", "files": listing}, indent=1),
                                                   encoding="utf-8")
    # gold: extract with the runner's adapters and locate the planted strings
    warn: Counter = Counter()
    units = rs.load_units(task, warn)
    gt_dir.mkdir(parents=True)
    rows_out = []
    counts: Counter = Counter()
    missing: list[tuple] = []
    for u in units:
        part = u.container.get("part_index") if u.container else None
        key = (u.kind, u.path, u.pointer if u.kind == "slack" else part)
        planted = planted_by_unit.get(key)
        if planted is None:
            raise RuntimeError(f"unit without planted list: {key}")
        spans = exact_spans(u.text, recorded_by_unit[key]) if key in recorded_by_unit else None
        if spans is None:
            spans = locate_planted(u.text, planted)
        else:
            counts["exact_units"] += 1
        found = {(t, l) for _s, _e, l, t, _c in spans}
        for t, l, c in planted:
            if t and (t, l) not in found:
                missing.append((cfg["slug"], key, l, t))
        gt_spans = []
        for s, e, label, text, chars in spans:
            locs = rs.native_locations(u, s, e)
            if not locs:
                missing.append((cfg["slug"], key, label, text + " (no location)"))
                continue
            loc = dict(locs[0])
            if len(locs) > 1:
                loc = {"kind": u.kind, "crosses_parts": True, "fragments": locs}
            loc["status"] = "located"
            gt_spans.append({"text": text, "start": s, "end": e, "label": label, "characters": chars, "location": loc})
            counts[label] += 1
        file = {"kind": u.kind, "path": u.path, "sha256": hashlib.sha256((task / u.path).read_bytes()).hexdigest(),
                "container": u.container}
        rows_out.append({"meta": meta_by_unit[key], "text": u.text, "file": file, "ground_truth_spans": gt_spans})
    with (gt_dir / "ground_truth.jsonl").open("w", encoding="utf-8") as h:
        for r in rows_out:
            h.write(json.dumps(r, ensure_ascii=False) + "\n")
    exact_units = counts.pop("exact_units", 0)
    # roster
    chars: dict[str, dict] = {}
    for p in people:
        chars[p.cid] = {"canonical_name": p.full, "first_names": [p.given], "last_names": [p.family],
                        "nicknames": [p.nick] if p.nick else [],
                        "emails": [{"value": p.email, "category": "professional"}]
                        + ([{"value": p.personal_email, "category": "personal"}] if p.personal_email else []),
                        "slack_handles": [p.uid, p.handle], "phone_numbers_linked": [p.phone] + ([p.phone2] if p.phone2 else []),
                        "employee_ids": [p.emp_id] if p.emp_id else [], "account_numbers": [p.account] if p.account else [],
                        "addresses": [p.address], "organizations": [p.org.name]}
    for o in orgs:
        chars[o.oid] = {"canonical_name": o.name, "organization": True, "organizations": sorted({o.name, o.legal, o.short}),
                        "urls": [o.url], "addresses": [o.address], "account_numbers": [o.account], "domain": o.domain}
    (gt_dir / "characters.json").write_text(json.dumps(chars, indent=1, ensure_ascii=False), encoding="utf-8")
    # the answer key of the export in one file: the same rows and roster (gold.json), for readers that want one
    # object per export; ground_truth.jsonl and characters.json are the card's layout for the benchmark's scorer
    gold = {"set": cfg["slug"], "mode": cfg["mode"], "labels": list(LABELS), "characters": chars, "rows": rows_out}
    (gt_dir / "gold.json").write_text(json.dumps(gold, ensure_ascii=False, indent=0), encoding="utf-8")
    return {"set": cfg["slug"], "mode": cfg["mode"], "people": len(people), "orgs": len(orgs), "units": dict(Counter(u.kind for u in units)),
            "exact_offset_units": exact_units, "spans": dict(counts), "total_spans": sum(counts.values()),
            "missing": missing, "warnings": dict(warn)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(HERE))
    ap.add_argument("--sets", type=int, default=len(SETS))
    ap.add_argument("--force", action="store_true", help="rebuild even when ground_truth/ exists")
    a = ap.parse_args()
    if shutil.which("cupsfilter") is None:
        sys.exit("cupsfilter (macOS CUPS) is needed to render the PDFs")
    out = Path(a.out)
    if (out / "ground_truth").exists() and not a.force:
        sys.exit(f"{out / 'ground_truth'} exists; pass --force to rebuild")
    report = []
    for i, cfg in enumerate(SETS[:a.sets]):
        r = build_set(cfg, out, i)
        report.append(r)
        print(json.dumps({k: v for k, v in r.items() if k != "missing"} | {"missing": len(r["missing"])}), flush=True)
        for m in r["missing"][:20]:
            print("  MISSING", m)
    (out / "build_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    bad = sum(len(r["missing"]) for r in report)
    print(f"sets={len(report)} spans={sum(r['total_spans'] for r in report)} missing={bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
