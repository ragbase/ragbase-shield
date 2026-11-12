"""S6 (2026-10-20): account and staff identifier cue rules, keyed lines, in-text layouts and tail lists, table
columns, and street-level address edges (``engine/detectors_ids.py``, registered from ``detectors.py``).
Every number, name, company and address here is invented."""
from __future__ import annotations

from ragbase_shield.engine import detectors as det
from ragbase_shield.engine import detectors_ids as ids


def found(text, lang="en", kinds=("ACCOUNT_NUMBER", "EMPLOYEE_ID")):
    out = []
    for c in det._select(c for c in det.detect_candidates(text, lang=lang) if c.valid):
        if c.kind in kinds:
            out.append((c.kind, text[c.start:c.end], c.detector))
    return out


def addresses(text):
    return [(text[c.start:c.end], c.detector)
            for c in det._select(c for c in det.detect_candidates(text, lang="en") if c.valid) if c.kind == "ADDRESS"]


def test_registered_last_in_the_detector_registry():
    assert det.DETECTORS[-len(ids.DETECTORS_IDS):] == ids.DETECTORS_IDS  # v0.4 (T8): five rules since T8
    assert ids.find_street_addresses.langs == ("en",)


# ---------------------------------------------------------------------------
# cue values and keyed lines
# ---------------------------------------------------------------------------


def test_bare_label_nouns_take_an_id_shaped_value():
    assert found("Owner: Dana Quill, employee TQ-604183, dana@example.test") == [("EMPLOYEE_ID", "TQ-604183", "labelled_id")]
    assert found("Profit sharing plan 6614-2297 has a transfer pending.") == [("ACCOUNT_NUMBER", "6614-2297", "labelled_id")]
    assert found("the Roth IRA ****-5106 and the joint account ****-5107") == \
        [("ACCOUNT_NUMBER", "****-5106", "labelled_id"), ("ACCOUNT_NUMBER", "****-5107", "labelled_id")]
    assert found("badge 00123456 issued") == [("EMPLOYEE_ID", "00123456", "labelled_id")]
    assert found("Account: 1234567890") == [("ACCOUNT_NUMBER", "1234567890", "labelled_id")]


def test_grouped_numbers_need_an_explicit_marker():
    assert found("member #: 12 345 678") == [("ACCOUNT_NUMBER", "12 345 678", "labelled_id")]
    assert found("plan 12 345 678 units") == []


def test_keyed_line_with_a_holder_name_between_label_and_value():
    text = "Registration  Holder Family Revocable Trust 5826-3307\nAcquired 2004-06-15\nShares 14,000.000"
    assert found(text) == [("ACCOUNT_NUMBER", "5826-3307", "labelled_id")]
    assert found("REGISTRATION: Marnival Trust 5826-3307") == [("ACCOUNT_NUMBER", "5826-3307", "labelled_id")]
    assert found("Employee of record  Dorian Vexley  BC-00917") == [("EMPLOYEE_ID", "BC-00917", "labelled_id")]
    assert found("Registration of the 2024 series was 5826-3307") == []   # a number in between: not a keyed line


def test_cue_values_carry_the_detector_name_the_shape_memory_reads():
    cands = [c for c in det.detect_candidates("employee TQ-604183 and account 5826-3308", lang="en") if c.valid]
    assert {c.detector for c in cands if c.kind in ("EMPLOYEE_ID", "ACCOUNT_NUMBER")} == {"labelled_id"}
    assert det.shape_template("TQ-604183") == "TQ-dddddd"   # the masker learns it for the whole dossier


# ---------------------------------------------------------------------------
# layouts and tails
# ---------------------------------------------------------------------------


def test_confirmed_layout_propagates_in_the_text_but_plain_digits_do_not():
    text = ("Account 5826-3308 is primary. The sibling numbers are 5826-3307 and 6352-4417; "
            "the 2024-2025 budget and build 4.2.3 are not accounts. Account: 1234567890 and later 0987654321.")
    got = found(text)
    assert ("ACCOUNT_NUMBER", "5826-3308", "labelled_id") in got
    assert ("ACCOUNT_NUMBER", "5826-3307", "layout_id") in got
    assert ("ACCOUNT_NUMBER", "6352-4417", "layout_id") in got
    assert ("ACCOUNT_NUMBER", "1234567890", "labelled_id") in got
    assert all(v not in ("2024-2025", "4.2.3", "0987654321") for _k, v, _d in got)


def test_tail_lists_after_a_value_give_one_id_per_tail():
    text = "$48,200,000 across 4 registrations (5826-3306, -3307, -3308 and -3309) | next"
    assert found(text) == [("ACCOUNT_NUMBER", "5826-3306", "labelled_id"), ("ACCOUNT_NUMBER", "3307", "layout_id"),
                           ("ACCOUNT_NUMBER", "3308", "layout_id"), ("ACCOUNT_NUMBER", "3309", "layout_id")]


def test_id_layout_helper():
    assert ids.id_layout("5826-3308") == "dddd-dddd"
    assert ids.id_layout("TQ-604183") == "TQ-dddddd"
    assert ids.id_layout("ACC 001917") == "ACC dddddd"
    assert ids.id_layout("1234567890") is None       # a plain digit run never propagates
    assert ids.id_layout("12 345 678") is None       # spaces without a letter prefix never propagate
    assert ids.id_layout("****-5106") is None
    assert ids.id_layout("12-34") is None            # under six digits


# ---------------------------------------------------------------------------
# controls
# ---------------------------------------------------------------------------


def test_controls_are_never_identifiers():
    text = ("Call +1-802-555-0163 or 802-555-0164, fax 555-0165; plan 2025; build 4.2.3 released 2025-09-14 "
            "at 21:40; version 10.20.30; account balance $12,400.00; fee 1,839,540.00 USD; 15% share; "
            "employee count 1200; staff 2019-2024; policy 2024-25; SSN 123-45-6789; zip 33701-1234; "
            "loan 5 000 000 EUR; account 802-555-0163; member 8025550163.")
    assert found(text) == []
    phones = found(text, kinds=("PHONE",))
    assert len(phones) >= 2 and all(k == "PHONE" for k, _v, _d in phones)


def test_year_like_and_date_values_are_refused_by_the_helper():
    for v in ("2024", "21:40", "2025-09-14", "14/02/2024", "2024-2025", "4.2.3", "555-0163", "123-45-6789", "33701-1234"):
        assert ids.value_refused(v, 0, len(v)), v
    assert not ids.value_refused("5826-3308", 0, 9)
    assert ids.value_refused("12 345 678", 0, 10) and not ids.value_refused("12 345 678", 0, 10, explicit=True)
    text = "total 5826-3308 €"
    assert ids.value_refused(text, 6, 15)   # an amount


# ---------------------------------------------------------------------------
# table columns
# ---------------------------------------------------------------------------


def test_pipe_table_columns_with_underscore_headers_and_trailing_values():
    csv_like = ("report_id | generated_at | account_number | household_name | accounts_count\n"
                "R-1 | 2025-09-14T21:40Z | 6352-4417 | Marnival Household | 4\n"
                "R-2 | 2025-09-14T21:40Z | 6352-4433 | Vexley Trust | 2\n")
    assert found(csv_like) == [("ACCOUNT_NUMBER", "6352-4417", "table_id"), ("ACCOUNT_NUMBER", "6352-4433", "table_id")]
    staff = "Legal name | Employee ID | Role\nDana Quill | TQ-604183 | Manager\nOmar Vell | TQ-711952 | Analyst\n"
    assert found(staff) == [("EMPLOYEE_ID", "TQ-604183", "table_id"), ("EMPLOYEE_ID", "TQ-711952", "table_id")]
    pdf_table = "Lot | Security | Registration | Acquired\nL1 | Fund X | Holder Family Trust 5826-3306 | 2016-04-19\n"
    assert found(pdf_table) == [("ACCOUNT_NUMBER", "5826-3306", "table_id")]
    dates = "Name | Account\nDana | 2024-05-01\n"
    assert found(dates) == []


# ---------------------------------------------------------------------------
# street-level addresses
# ---------------------------------------------------------------------------


def test_street_name_holding_a_street_type_word_keeps_its_suffix_and_unit():
    text = "Mail to Fernhollow Development Group, 7120 Grove Street West, Suite 470, St. Petersburg, FL 33701 by Friday."
    got = addresses(text)
    assert ("7120 Grove Street West, Suite 470", "address_street") in got
    assert not any(v == "7120 Grove Street" for v, _d in got)


def test_wrapped_pdf_addresses_are_found_whole():
    assert addresses("The office is at 4030 Summit\nBoulevard, Suite 1200, Tampa, FL 33607. Two of them") == \
        [("4030 Summit\nBoulevard, Suite 1200, Tampa, FL 33607", "address_street")]
    got = addresses("QUARMBY & VEXLEY · Counsel · 318 South Clifford Street,\nSuite 1500, Tampa, FL 33606 · T +1-802-555-0178")
    assert got == [("318 South Clifford Street,\nSuite 1500, Tampa, FL 33606", "address_street")]
    got = addresses("Brindlecove Inc. — Analytics | 6215 Atlantic Boulevard, Suite 330, Westminster, CO\n80031\nNext line")
    assert got == [("6215 Atlantic Boulevard, Suite 330, Westminster, CO\n80031", "address_street")]


def test_street_rule_refuses_a_number_at_a_line_end_without_more_evidence():
    assert addresses("Page 4\nMain Street Office hours") == []
    mine = [c for c in ids.find_street_addresses("In 2019 Main Street was renamed.")]
    assert mine == []   # a year-like number with no tail (the base detector decides on its own)
    assert addresses("5 Street") == []


def test_french_identifier_rules_are_unchanged_by_the_new_module():
    text = "Le salarié matricule 00123456 et le compte client 12 345 678 90 ; SIREN 552 100 554 ; tél. 01 45 67 89 10"
    got = found(text, lang="fr")
    assert ("EMPLOYEE_ID", "00123456", "labelled_id") in got
    assert ("ACCOUNT_NUMBER", "12 345 678 90", "labelled_id") in got
    others = found(text, lang="fr", kinds=("SIREN", "PHONE"))
    assert ("SIREN", "552 100 554", "siren") in others and ("PHONE", "01 45 67 89 10", "phone_fr") in others
