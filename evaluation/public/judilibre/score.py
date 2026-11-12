"""Classify every mask Shield applied to the Judilibre sample, and count them.

There is no gold annotation for this test and no published metric: the measure is the one fixed for this test
before the run. Every mask Shield applies is counted and classified by what it hit. The parties are already
pseudonymised by the Cour de cassation ("M. [X]", "société [Y]", "X..." in older decisions), so a mask can hit:

- ``court``         a court name or court function ("cour d'appel", "chambre sociale", "JAF");
- ``court_city``    the city of a court or of a bar ("cour d'appel de [Douai]", "barreau de [Lyon]");
- ``law``           a law, a code, an article, a regulation, a named statutory scale;
- ``legal_term``    legal vocabulary used as such ("créancier gagiste", "franchiseur", "syndicat des
                    copropriétaires", a legal form such as "société par actions simplifiée");
- ``case_number``   a case number: pourvoi, RG, Portalis, ECLI, other docket, or the number of another decision
                    cited as case law. Masked BY DESIGN in v0.1 (kind CASE_REF), counted apart;
- ``professional``  the real name of a judge, prosecutor, court clerk, lawyer or law firm, or of another legal
                    professional (court-appointed agent, bailiff, technician). Judilibre does not pseudonymise
                    them: masking them is CORRECT (true positive of the person detector);
- ``placeholder``   a pseudonymisation placeholder only ("Z", "X" of "M. X...");
- ``other``         everything else, in the sub-classes of ``SUBS["other"]`` (party data the pseudonymisation
                    left in clear, companies, public bodies, institutional contact details, places, words...).

Target fixed before the run: 0 masks on court, court_city, law and legal_term.

How a mask is classified: deterministic rules on the masked text and its context (``classify``), then the
manual review decisions of ``review_overrides.json``, keyed by decision id + character offsets, with a reason.
A review decision is written per group of identical masks in one decision, so some of them only confirm the rule
class. The scorer refuses to report while a mask has no class. Every mask with its rule class, its final class
and the reason is written to ``.bench_data/public/judilibre/classified.jsonl``; the counts to ``summary.json``.

The summary also gives denominators found with fixed patterns written for this test (court names, court
cities, article references, codes, laws, placeholders, lawyer and judge names) and how many of those mentions
overlap a mask.

Usage: python evaluation/public/judilibre/score.py [--dump CATEGORY[/SUB]] [--unresolved] [--work NAME]

``--work NAME`` (v0.2): read ``spans.jsonl``, ``docs.jsonl``, ``run_meta.json`` from, and write
``classified.jsonl`` and ``summary.json`` to, the sub-folder NAME of the work folder (a run made with
``run_shield.py --out NAME``). The sample and the classification are the same.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = ROOT / ".bench_data" / "public" / "judilibre"
OUT = WORK  # run files (set by --work)
OVERRIDES = HERE / "review_overrides.json"

CATEGORIES = ("court", "court_city", "law", "legal_term", "case_number", "professional", "placeholder", "other")
MUST_STAY_CLEAR = ("court", "court_city", "law", "legal_term")
SUBS = {
    "court": ("court",),
    "court_city": ("court_city",),
    "law": ("law",),
    "legal_term": ("legal_term",),
    "case_number": ("pourvoi", "rg", "portalis", "ecli", "other_docket", "cited_precedent"),
    "professional": ("magistrate", "lawyer", "other_professional"),
    "placeholder": ("placeholder",),
    "other": ("party_residual", "company", "company_id", "public_body", "institutional_contact", "place",
              "other_person", "lawyer_contact", "reference", "date", "word"),
}
SUB_LABELS = {
    "pourvoi": "pourvoi numbers", "rg": "RG / role numbers", "portalis": "Portalis numbers", "ecli": "ECLI",
    "other_docket": "other docket numbers (decision n°, commercial-court numbers, lower-court numbers)",
    "cited_precedent": "number of ANOTHER decision cited as case law (e.g. 'Soc., 27 avril 2017, pourvoi n° ...')",
    "magistrate": "judges, prosecutors, court clerks", "lawyer": "lawyers and law firms (SCP, SELARL...)",
    "other_professional": "other legal professionals (court-appointed agents, notaries, bailiffs, experts, interpreters)",
    "party_residual": "party data left in clear by the pseudonymisation (first names, birth dates, addresses, plates)",
    "company": "companies, associations, unions, brands and products, and their addresses and websites "
               "(legal persons are not pseudonymised by Judilibre)",
    "company_id": "company identifiers (SIREN / RCS numbers)",
    "public_body": "public bodies and institutions (administrations, social-security bodies)",
    "institutional_contact": "contact details of courts and public services (URL, phone, e-mail, address)",
    "place": "place names that are not a court city (towns, countries, streets, estates)",
    "other_person": "other real people (public figures, authors, staff named in the facts)",
    "lawyer_contact": "lawyers' bar numbers (toque) and office addresses",
    "reference": "business file or contract references (not a court docket)",
    "date": "dates that are not a birth date",
    "word": "ordinary words (not a name, not legal vocabulary)",
}


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().replace("’", "'")


# ----------------------------------------------------------------------------------------------------------
# Rules
# ----------------------------------------------------------------------------------------------------------

PH_TOKEN = r"(?:\[[^\]\n]{1,40}\]|[A-Z](?:\s?\.{1,3}|…)?)"
CIVILITY = r"(?:M\.|Mme|MM\.|Mmes|Mlle|Mlles|Monsieur|Madame|Mademoiselle|Me)"
PLACEHOLDER_ONLY = re.compile(rf"^(?:{CIVILITY}\s*)?{PH_TOKEN}(?:[\s\-,]+(?:et\s+)?{PH_TOKEN})*\.*$")
HAS_PH_LETTER = re.compile(r"(?:^|\s)[A-Z](?:\s?\.{1,3}|…)?$")

COURT_WORDS = re.compile(
    r"\b(?:cour|tribunal|tribunaux|prud'?hom|chambre|juridiction|conseil d'etat|greffe|parquet|tgi|tass|jex|jld|"
    r"jaf|pole social|assises|cassation)\b")
LAW_WORDS = re.compile(
    r"\b(?:articles?|art\.|code|loi|lois|decret|ordonnance n|reglement|directive|convention europeenne|"
    r"constitution|traite)\b|^[lrd]\.?\s?\d")

ROLE_MAGISTRATE = (
    r"(?:1er |premier |premiere )?(?:vice[- ])?presidente?s?|conseill(?:er|ere)s?|referendaires?|doyen|"
    r"avocat(?:e)? general(?:e)?|avocats generaux|procureure?|substitute?|greffier(?:e)?s?|greffe\b|rapporteur|"
    r"juges?\b|magistrat(?:e)?s?|assesseurs?|faisant fonction|auditeur|auditrice|juriste assistante?|"
    r"assistante? de justice|agent du greffe|statuant en qualite de juge|en qualite de juge|juge unique"
)
ROLE_LAWYER = (r"avocat|avocate|avocats|avocates|avoue|avoues|scp|selarl|selas|selafa|aarpi|associes|cabinet|"
               r"societe civile professionnelle|societe d'avocats")
ROLE_OTHER_PRO = (
    r"mandataire|liquidat(?:eur|rice)|administrat(?:eur|rice) judiciaire|commissaire|huissier|huissiere|notaire|"
    r"expert|experte|interprete|syndic a la liquidation|en qualite de syndic|es[- ]qualites|mediat(?:eur|rice)|"
    r"curateur|tuteur|delegue du procureur|enqueteur|enqueteuse|officier de police|brigadier|gardien de la paix"
)
RIGHT_MAGISTRATE = re.compile(rf"^[\s,:;]*(?:\(|-\s*)?(?:{ROLE_MAGISTRATE})")
LEFT_MAGISTRATE = re.compile(
    rf"(?:\b(?:{ROLE_MAGISTRATE})[^\n;]{{0,40}}?(?:\s*:\s*)(?:{CIVILITY.lower()}|m\.|mme|mm\.|mmes|mlle|madame|monsieur)?\s*$"
    rf"|\b(?:{ROLE_MAGISTRATE})\s*,?\s*(?:m\.|mme|mlle|madame|monsieur)\s*$"
    rf"|(?:monsieur|madame|m\.|mme) (?:le|la|l') (?:{ROLE_MAGISTRATE})[^\n,;]{{0,30}}\s$"
    rf"|(?:prononcee? (?:[^\n]{{0,80}})?par|rapport (?:a ete )?(?:presente|fait)[^\n]{{0,30}}par|fait rapport par|"
    rf"signee? par|devant|en presence de|nous,)\s*(?:m\.|mme|mlle|madame|monsieur)?\s*$)"
)
SIGNATURE = re.compile(r"\b(?:le|la) greffi(?:er|ere)\b.{0,40}\b(?:le|la) (?:president|presidente|juge|conseiller)|"
                       r"\b(?:le|la) (?:president|presidente|juge)\b.{0,40}\b(?:le|la) greffi(?:er|ere)", re.S)
RIGHT_REPORT = re.compile(r"^\s*(?:a fait|a presente|fait) (?:le )?rapport")
BENCH_MARK = re.compile(r"etaient presents|composition de la (?:cour|juridiction)|composition du tribunal|"
                        r"debats et (?:au )?delibere|assesseurs?\s*:|en presence de")
LEFT_LAWYER = re.compile(r"(?:\b(?:me|mes|maitre|maitres)\.?\s*$|\b(?:scp|selarl|selas|selafa|aarpi|selurl|seleurl|"
                         r"societe civile professionnelle|societe d'avocats|avocats? aux conseils)\b[^\n;,]{0,40}$)")
RIGHT_LAWYER = re.compile(rf"^[\s,]*(?:\(|-\s*)?(?:{ROLE_LAWYER})\b")
LEFT_OTHER_PRO = re.compile(rf"\b(?:{ROLE_OTHER_PRO})\w*(?: de justice| judiciaires?)?\s*[,:]?\s*(?:m\.|mme|me|maitre|monsieur|madame)?\s*$")
RIGHT_OTHER_PRO = re.compile(
    rf"^[\s,:(\-]*(?:(?:agissant|pris|prise|designee?|nommee?)\s+)?(?:en (?:sa |qualite de |qualite d'|tant que )*|es[- ]qualites?\s*(?:de |d')?)?(?:{ROLE_OTHER_PRO})")

LEGAL_VOCAB = re.compile(
    r"\b(?:franchis(?:e|ee|es|eur|eurs|euse)|gagiste|nanti|nantissement|privilege|creanci(?:er|ere)|debit(?:eur|rice)|"
    r"bailleu?r|bailleresse|preneur|copropriet\w*|judiciaire|anonyme|syndicale libre|ensemble immobilier|liquidation|redressement|sauvegarde|deboutons|condamnons|"
    r"ordonnons|disons|rejetons|constatons|renvoyons|attendu|considerant|par ces motifs|legalement justifie|delits?|"
    r"diffamation|contravention|prevenu|partie civile|ministere public|actions simplifiee|responsabilite limitee|"
    r"societe anonyme|civile immobiliere|en nom collectif|economie mixte|cooperative|exercice liberal|unipersonnelle|"
    r"association syndicale|syndicat des coproprietaires|astreinte|dommages|interets|indemnite|prejudice|"
    r"cassation|appelant|intime|demandeur|defendeur|defenderesse|demanderesse|requerant|refere|jugement|arret)\b"
)

COMPANY_LEFT = re.compile(
    r"(?:\b(?:societe|societes|ste|sas|sasu|sarl|eurl|sa|snc|sci|scea|gaec|selarl|scp|sca|sem|gie|groupe|"
    r"banque|caisse|compagnie|cie|mutuelle|association|syndicat|union|federation|fondation|etablissements?|ets|"
    r"entreprise|enseigne|marque|cabinet|agence|holding|laboratoires?|hotel|clinique|residence|club|"
    r"s\.a\.s\.?|s\.a\.r\.l\.?|s\.a\.?|s\.c\.i\.?|e\.u\.r\.l\.?|s\.n\.c\.?)\b[^\n;,]{0,30}$)")

PUBLIC_BODY = re.compile(
    r"\b(?:cpam|caisse primaire|urssaf|pole emploi|france travail|caf\b|caisse d'allocations|msa\b|carsat|cnav|"
    r"prefet|prefecture|ministere|ministre|tresor public|agent judiciaire|tresorier|unedic|ags\b|cgea|oniam|fgti|"
    r"fonds de garantie|etat\b|republique|departement|region\b|commune|ville de|mairie|conseil general|"
    r"conseil departemental|assistance publique|ap-hp|hopita|centre hospitalier|chu\b|ofii|ofpra|cnil|"
    r"inspection du travail|direction (?:generale|regionale|departementale)|dgfip|douane|police|gendarmerie|"
    r"defenseur des droits|controleur general|insee|banque de france|education nationale|"
    r"universite|rectorat|academie|office public|opac|opha?\b|anah|bpifrance|haute autorite|"
    r"autorite de la concurrence|amf\b|acpr\b)")

FIRST_NAME_TOKEN = r"[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ'’]+(?:-[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ'’]+)*"
RESIDUAL_NAME = re.compile(rf"^(?:{CIVILITY}\s+)?{FIRST_NAME_TOKEN}(?:\s+{FIRST_NAME_TOKEN})*(?:\s+[A-Z]\.?)?$")
RIGHT_PH = re.compile(r"^\s*(?:\.{1,3}|…|(?:[A-Z](?:\s?\.{2,3}|…))|\[[^\]\n]{1,40}\])")
LEFT_PH = re.compile(r"(?:[A-Z](?:\s?\.{2,3}|…)|\[[^\]\n]{1,40}\])[\s,]*$")
CITED = re.compile(r"(?:\bcass\b|cass\.|cassation|\bsoc\b|\bciv\b|\bcom\b|\bcrim\b|\b[123]e?r?e?\s*civ|ass\.?\s*plen|"
                   r"ch\.?\s*mixte)[^\n;]{0,60}\d{4}[^\n;]{0,25}n[°o]s?\.?\s*$")


def case_sub(value: str, left: str) -> str:
    if CITED.search(fold(left[-110:])):
        return "cited_precedent"
    lf = fold(left[-45:])
    if value.upper().startswith("ECLI"):
        return "ecli"
    if "portalis" in lf or re.fullmatch(r"[A-Z0-9]{4}-[A-Z]-[A-Z0-9]{3}-[A-Z0-9]{4,5}", value):
        return "portalis"
    if "pourvoi" in lf or re.fullmatch(r"(?:[A-Z]\s?)?\d{2}-\d{2}\.?\d{3}", value.strip()):
        return "pourvoi"
    if re.search(r"\br\.?\s?g\.?\b|\brg\b|role|repertoire general|no ?rg", lf):
        return "rg"
    return "other_docket"


def classify(s: dict) -> tuple[str, str, str]:
    """(category, sub, rule) for one mask, or ('', '', 'unresolved')."""
    kind, value = s["kind"], s["value"]
    left, right = s.get("wide_left", s["left"]), s.get("wide_right", s["right"])
    fv, fl, fr = fold(value), fold(left), fold(right)

    if kind == "CASE_REF":
        return "case_number", case_sub(value, left), "kind=CASE_REF"
    if kind == "ID_CODE":
        if "toque" in fl[-30:]:
            return "other", "lawyer_contact", "ID_CODE after 'toque'"
        if re.search(r"pourvoi|portalis|\brg\b|minute|parquet|instruction|n°", fl[-30:]):
            return "case_number", case_sub(value, left), "ID_CODE after a docket word"
        return "", "", "unresolved"
    if kind == "BIRTHDATE":
        if re.search(r"\bnee?s?\s+(?:le|en)\s*$", fl[-15:]):
            return "other", "party_residual", "BIRTHDATE after 'né le'"
        return "", "", "unresolved"
    if kind == "SIREN":
        return "other", "company_id", "kind=SIREN"
    if kind in ("ADDRESS", "URL", "PHONE", "EMAIL"):
        return "", "", "unresolved"  # few: all reviewed by hand

    # PERSON / ORG
    if PLACEHOLDER_ONLY.match(value.strip()):
        return "placeholder", "placeholder", "value is placeholders only"
    if COURT_WORDS.search(fv):
        return "court", "court", "court word in the value"
    if LAW_WORDS.search(fv):
        return "law", "law", "law word in the value"
    if LEGAL_VOCAB.search(fv):
        return "legal_term", "legal_term", "legal vocabulary in the value"
    if RIGHT_MAGISTRATE.search(fr[:60]) or LEFT_MAGISTRATE.search(fl[-90:]) or RIGHT_REPORT.search(fr[:40]):
        return "professional", "magistrate", "judicial role next to the name"
    if SIGNATURE.search(fl[-160:]) and "\n\n" in left[-400:]:
        return "professional", "magistrate", "name in the signature block"
    if RIGHT_OTHER_PRO.search(fr[:60]):
        return "professional", "other_professional", "legal-profession role after the name"
    if LEFT_LAWYER.search(fl[-60:]) or RIGHT_LAWYER.search(fr[:30]):
        return "professional", "lawyer", "lawyer cue next to the name"
    if LEFT_OTHER_PRO.search(fl[-80:]):
        return "professional", "other_professional", "legal-profession role before the name"
    if kind == "PERSON":
        m = None
        for m in BENCH_MARK.finditer(fl[-700:]):
            pass
        if m is not None:
            tail = fl[-700:][m.end():]
            if ";" not in tail and "\n\n\n" not in tail and re.search(r"(?:m\.|mme|mm\.|mmes|mlle|monsieur|madame|,|:)\s*$", tail[-12:]):
                return "professional", "magistrate", "name in the bench composition list"
    if kind == "PERSON" and RESIDUAL_NAME.match(value) and (
            HAS_PH_LETTER.search(value) or RIGHT_PH.match(right) or LEFT_PH.search(left[-12:])):
        return "other", "party_residual", "first name next to a placeholder"
    if PUBLIC_BODY.search(fv):
        return "other", "public_body", "public-body word"
    if kind == "ORG" and COMPANY_LEFT.search(fl[-45:]):
        return "other", "company", "company cue before the name"
    return "", "", "unresolved"


# ----------------------------------------------------------------------------------------------------------
# Scoring
# ----------------------------------------------------------------------------------------------------------

WIDE = 600


def add_wide_context(spans: list[dict]) -> None:
    """The run stores 100 characters of context; the rules look further (bench lists, signature blocks)."""
    texts = [json.loads(l)["text"] for l in (WORK / "sample.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    for s in spans:
        t = texts[s["doc"]]
        assert t[s["start"]:s["end"]] == s["value"]
        s["wide_left"] = t[max(0, s["start"] - WIDE):s["start"]]
        s["wide_right"] = t[s["end"]:s["end"] + WIDE]


def key_of(s: dict) -> str:
    return f"{s['id']}:{s['start']}:{s['end']}"


def load_overrides() -> dict[str, dict]:
    if not OVERRIDES.exists():
        return {}
    data = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    out = {}
    for item in data["overrides"]:
        cat, sub = item["category"], item["sub"]
        assert cat in CATEGORIES and sub in SUBS[cat], item
        for k in item["keys"]:
            out[k] = item
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", help="print the masks of CATEGORY or CATEGORY/SUB with context")
    ap.add_argument("--unresolved", action="store_true", help="print the masks no rule or review classified")
    ap.add_argument("--rule-only", action="store_true", help="with --dump: only masks classified by a rule")
    ap.add_argument("--work", default="", help="sub-folder of the work folder holding the run to score")
    args = ap.parse_args()
    global OUT
    OUT = WORK / args.work if args.work else WORK

    spans = [json.loads(l) for l in (OUT / "spans.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    add_wide_context(spans)
    docs = [json.loads(l) for l in (OUT / "docs.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    meta = json.loads((OUT / "run_meta.json").read_text(encoding="utf-8"))
    overrides = load_overrides()

    unresolved = []
    used = set()
    for s in spans:
        cat, sub, rule = classify(s)
        s["rule_category"], s["rule_sub"], s["rule"] = cat, sub, rule
        ov = overrides.get(key_of(s))
        if ov is not None:
            used.add(key_of(s))
            cat, sub = ov["category"], ov["sub"]
            s["review"] = ov["reason"]
        s["category"], s["sub"] = cat, sub
        if not cat:
            unresolved.append(s)
    stale = set(overrides) - used
    if stale:
        print(f"WARNING: {len(stale)} review keys match no mask (first: {sorted(stale)[:3]})", file=sys.stderr)

    if args.unresolved or args.dump:
        sel = unresolved if args.unresolved else [
            s for s in spans if f"{s['category']}/{s['sub']}" == args.dump or s["category"] == args.dump]
        if args.rule_only:
            sel = [s for s in sel if "review" not in s]
        groups = defaultdict(list)
        for s in sel:
            groups[(s["doc"], s["kind"], s["value"])].append(s)
        for (doc, kind, value), ss in sorted(groups.items()):
            s = ss[0]
            lft = s["left"][-70:].replace("\n", "⏎")
            rgt = s["right"][:45].replace("\n", "⏎")
            tag = s.get("review") or s["rule"]
            print(f"{doc:3d} {kind[:6]:6s} x{len(ss):<3d} {s['sub'] or '?':14s} {lft:>70} <<{value}>> {rgt}  [{tag[:40]}]")
        print(f"-- {len(sel)} masks, {len(groups)} groups", file=sys.stderr)
        return 0

    if unresolved:
        print(f"{len(unresolved)} masks have no class yet (run with --unresolved)", file=sys.stderr)
        return 1

    with (OUT / "classified.jsonl").open("w", encoding="utf-8") as f:
        for s in spans:
            f.write(json.dumps({k: v for k, v in s.items() if not k.startswith("wide_")}, ensure_ascii=False) + "\n")

    summary = build_summary(spans, docs, meta, overrides)
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


# Independent check with a denominator: legal content found in the sample by fixed patterns (written for this
# test, not taken from Shield), and how many of those mentions overlap a mask. Patterns only see well-formed
# mentions; the classification above is the complete count of what was masked.
LEGAL_PATTERNS = {
    "court names": re.compile(
        r"(?i)\b(?:cour d['’]appel|cour de cassation|cour d['’]assises|cour administrative d['’]appel|"
        r"tribunal (?:judiciaire|de grande instance|d['’]instance|de commerce|administratif|correctionnel|de police|"
        r"de proximit[ée]|paritaire des baux ruraux|des affaires de s[ée]curit[ée] sociale|pour enfants)|"
        r"conseil de prud['’]?hommes|conseil d['’][ée]tat|chambre (?:sociale|civile|commerciale|criminelle|mixte))\b"),
    "court cities (word after a court name)": re.compile(
        r"(?i)\b(?:cour d['’]appel|tribunal judiciaire|tribunal de grande instance|tribunal d['’]instance|"
        r"tribunal de commerce|conseil de prud['’]?hommes|barreau)\s+(?:de la |de l['’]|de |d['’]|du |des )"
        r"(?-i:(?P<target>(?:L[ae]s? |L['’])?[A-ZÀ-ÖØ-Þ][\w'’]+(?:-[\w'’]+)*))"),
    "article references": re.compile(r"(?i)\barticles?\s+(?:(?-i:[LRDA])\.?\s?)?\d+(?:[\-.]\d+)*"),
    "codes": re.compile(
        r"(?i)\bcode (?:civil|p[ée]nal|du travail|de commerce|de proc[ée]dure (?:civile|p[ée]nale)|de la consommation|"
        r"de la s[ée]curit[ée] sociale|des assurances|de l['’]organisation judiciaire|de l['’]entr[ée]e et du s[ée]jour"
        r"[\w\s'’]{0,40}|de la sant[ée] publique|g[ée]n[ée]ral des imp[ôo]ts|des proc[ée]dures civiles d['’]ex[ée]cution|"
        r"mon[ée]taire et financier|de la construction et de l['’]habitation|de l['’]urbanisme|rural)"),
    "laws and decrees": re.compile(r"(?i)\b(?:loi|d[ée]cret|ordonnance|r[èe]glement|directive)\s+(?:\((?:UE|CE|CEE)\)\s+)?"
                                   r"(?:n[°o]\s*[\d\-/]+|du \d{1,2}(?:er)? \w+ \d{4})"),
}


PLACEHOLDER_PATTERNS = {
    "bracket placeholders ([X], [Adresse 1], [Localité 2]...)": re.compile(r"\[[^\]\n]{1,30}\]"),
    "old-style placeholders (X..., Y..., Z...)": re.compile(r"(?<![\w.])[A-Z](?:\s?\.{2,3}|…)"),
}


# Indicative recall on the real names Judilibre leaves in clear (a pattern sample, not a gold standard).
NAME_PATTERNS = {
    "lawyer names after 'Me' / 'Maître'": re.compile(
        r"\b(?:Me|Maître)\s+(?P<target>(?!\[)[A-ZÀ-ÖØ-Þ][\w'’\-]+(?:[ \t]+(?:de |du |le |la )?[A-ZÀ-ÖØ-Þ][\w'’\-]+){0,3})"),
    "judge or clerk names before ', président / conseiller / greffier / avocat général'": re.compile(
        r"(?:\bM\.|\bMme|\bMadame|\bMonsieur)\s+(?P<target>(?!\[)[A-ZÀ-ÖØ-Þ][\w'’\-]+(?:[ \t]+[A-ZÀ-ÖØ-Þ][\w'’\-]+){0,3})"
        r"\s*,\s*(?:pr[ée]sidente?|conseill[eè]re?|greffi[eè]re?|avocat g[ée]n[ée]ral)\b"),
}


def legal_content_coverage(spans: list[dict], patterns: dict = LEGAL_PATTERNS) -> dict:
    texts = [json.loads(l)["text"] for l in (WORK / "sample.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    masked = defaultdict(list)
    for s in spans:
        masked[s["doc"]].append((s["start"], s["end"]))
    out = {}
    for name, rx in patterns.items():
        found = hit = full = 0
        examples = []
        partial = []
        for i, t in enumerate(texts):
            for m in rx.finditer(t):
                a, b = (m.start("target"), m.end("target")) if "target" in rx.groupindex else (m.start(), m.end())
                found += 1
                if any(s < b and e > a for s, e in masked[i]):
                    hit += 1
                    if len(examples) < 10:
                        examples.append({"doc": i, "mention": t[a:b]})
                # Shield's own bench definition of "covered": every letter and digit of the mention is masked.
                if any(c.isalnum() for c in t[a:b]) and all(
                        not t[k].isalnum() or any(s <= k < e for s, e in masked[i]) for k in range(a, b)):
                    full += 1
                elif len(partial) < 20:
                    partial.append({"doc": i, "mention": t[a:b],
                                    "masked": [t[s:e] for s, e in masked[i] if s < b and e > a]})
        out[name] = {"mentions": found, "mentions_overlapping_a_mask": hit,
                     "mentions_fully_masked": full, "examples": examples, "not_fully_masked": partial}
    return out


def build_summary(spans: list[dict], docs: list[dict], meta: dict, overrides: dict) -> dict:
    strata = ("cour_de_cassation", "cour_d_appel", "tribunal_judiciaire")
    total = len(spans)
    by_cat = Counter(s["category"] for s in spans)
    by_sub = Counter((s["category"], s["sub"]) for s in spans)
    by_cat_stratum = Counter((s["category"], s["stratum"]) for s in spans)
    by_sub_stratum = Counter((s["category"], s["sub"], s["stratum"]) for s in spans)
    by_cat_kind = Counter((s["category"], s["kind"]) for s in spans)
    docs_with = defaultdict(set)
    for s in spans:
        docs_with[s["category"]].add(s["doc"])
    chars_by_stratum = Counter()
    secs_by_stratum = Counter()
    docs_by_stratum = Counter()
    for d in docs:
        chars_by_stratum[d["stratum"]] += d["chars"]
        secs_by_stratum[d["stratum"]] += d["seconds"]
        docs_by_stratum[d["stratum"]] += 1
    masks_by_stratum = Counter(s["stratum"] for s in spans)
    reviewed = sum(1 for s in spans if "review" in s)
    changed = sum(1 for s in spans if "review" in s and (s["rule_category"], s["rule_sub"]) != (s["category"], s["sub"]))
    clear_hits = [s for s in spans if s["category"] in MUST_STAY_CLEAR]
    speeds = sorted(d["chars"] / d["seconds"] for d in docs if d["seconds"] > 0)
    return {
        "decisions": len(docs),
        "chars": sum(d["chars"] for d in docs),
        "masks": total,
        "decisions_with_masks": len({s["doc"] for s in spans}),
        "by_category": {c: by_cat.get(c, 0) for c in CATEGORIES},
        "decisions_with_category": {c: len(docs_with.get(c, ())) for c in CATEGORIES},
        "by_sub": {f"{c}/{sb}": by_sub.get((c, sb), 0) for c in CATEGORIES for sb in SUBS[c]},
        "by_category_stratum": {c: {st: by_cat_stratum.get((c, st), 0) for st in strata} for c in CATEGORIES},
        "by_sub_stratum": {f"{c}/{sb}": {st: by_sub_stratum.get((c, sb, st), 0) for st in strata}
                           for c in CATEGORIES for sb in SUBS[c]},
        "by_category_kind": {c: {k: n for (cc, k), n in sorted(by_cat_kind.items()) if cc == c} for c in CATEGORIES},
        "strata": {st: {"decisions": docs_by_stratum[st], "chars": chars_by_stratum[st], "masks": masks_by_stratum[st],
                        "seconds": round(secs_by_stratum[st], 3),
                        "chars_per_second": round(chars_by_stratum[st] / secs_by_stratum[st]) if secs_by_stratum[st] else None}
                   for st in strata},
        "must_stay_clear_masks": len(clear_hits),
        "must_stay_clear_decisions": len({s["doc"] for s in clear_hits}),
        "must_stay_clear_examples": [{"doc": s["doc"], "id": s["id"], "category": s["category"], "kind": s["kind"],
                                      "value": s["value"], "context": (s["left"][-50:] + "[[" + s["value"] + "]]"
                                                                       + s["right"][:30]).replace("\n", " ")}
                                     for s in clear_hits],
        "review": {"masks_with_review_decision": reviewed, "review_changed_rule_class": changed,
                   "review_entries": len({id(v) for v in overrides.values()})},
        "speed": {"chars_per_second": meta.get("chars_per_second"), "mask_seconds": meta.get("mask_seconds"),
                  "cold_start_seconds": meta.get("cold_start_seconds"),
                  "per_decision_chars_per_second_p10": round(speeds[len(speeds) // 10]) if speeds else None,
                  "per_decision_chars_per_second_median": round(speeds[len(speeds) // 2]) if speeds else None,
                  "per_decision_chars_per_second_p90": round(speeds[(9 * len(speeds)) // 10]) if speeds else None,
                  "per_decision_chars_per_second_min": round(speeds[0]) if speeds else None,
                  "slowest_decision_seconds": max(d["seconds"] for d in docs),
                  "slowest_decision_chars": max(docs, key=lambda d: d["seconds"])["chars"]},
        "legal_content_found_by_pattern": legal_content_coverage(spans),
        "placeholders_found_by_pattern": legal_content_coverage(spans, PLACEHOLDER_PATTERNS),
        "professional_names_found_by_pattern": legal_content_coverage(spans, NAME_PATTERNS),
        "run_meta": meta,
    }


if __name__ == "__main__":
    sys.exit(main())
