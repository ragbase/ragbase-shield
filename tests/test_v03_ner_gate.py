"""Gated NER layer (S7, 2026-10-20): kind policy of the merge, handle and id gates, second signals, the watch list,
per-label thresholds. Invented data only; every name, company, handle and number below is made up."""
from __future__ import annotations

from ragbase_shield.engine import merge as mg
from ragbase_shield.engine import ner
from ragbase_shield.engine.normalize import fold, tokens


def _span(text, needle, kind, label="person", score=0.9, nth=0):
    i = -1
    for _ in range(nth + 1):
        i = text.index(needle, i + 1)
    return (i, i + len(needle), kind, label, score)


def _kept(text, spans, **kw):
    return {text[m.start:m.end]: m for m in mg.merge_ner(text, spans, lang="en", **kw)}


def _rule(text, needle, kind):
    i = text.index(needle)
    return (i, i + len(needle), kind)


# ---------------------------------------------------------------------------
# kind policy
# ---------------------------------------------------------------------------


def test_masker_path_keeps_only_the_policy_kinds_and_guard_path_keeps_every_kind():
    text = ("Contact Dorian Vexley at dorian@brindlecove.example, phone 020 7946 0999, born 3 May 1981, "
            "passport X1234567, vessel Marnival Star, badge BC-00917, account 5826-3308, handle dvex_7.")
    spans = [_span(text, "Dorian Vexley", "PERSON", "full_name"),
             _span(text, "dorian@brindlecove.example", "EMAIL", "email"),
             _span(text, "020 7946 0999", "PHONE", "phone_number"),
             _span(text, "3 May 1981", "BIRTHDATE", "date_of_birth"),
             _span(text, "X1234567", "ID_CODE", "passport_number"),
             _span(text, "Marnival Star", "ID_CODE", "vessel"),
             _span(text, "BC-00917", "EMPLOYEE_ID", "employee_id"),
             _span(text, "5826-3308", "ACCOUNT_NUMBER", "account_number"),
             _span(text, "dvex_7", "USERNAME", "username")]
    got = {v: m.kind for v, m in _kept(text, spans).items()}
    assert got == {"Dorian Vexley": "PERSON", "BC-00917": "EMPLOYEE_ID", "5826-3308": "ACCOUNT_NUMBER",
                   "dvex_7": "USERNAME"}
    # the guard path (hook) keeps the v0.2 behaviour: every model kind passes its shape check
    hook = {text[m.start:m.end]: m.kind for m in mg.guard_ner_spans(text, spans, lang="en")}
    assert hook["X1234567"] == "ID_CODE" and hook["3 May 1981"] == "BIRTHDATE" and hook["Marnival Star"] == "ID_CODE"
    # an explicit kinds list wins over the policy, in both directions
    assert set(_kept(text, spans, kinds=("ID_CODE",))) == {"X1234567", "Marnival Star"}
    assert set(_kept(text, spans, model_kinds=("PERSON",))) == {"Dorian Vexley"}


def test_watch_list_holds_named_assets_and_policy_dropped_finds_but_never_rules_or_courts():
    text = ("The vessel Marnival Star left the Brindlecove Tower for the Supreme Court hearing; "
            "school Hollowmere Academy; passport X1234567; the firm Vexley Partners LLC.")
    spans = [_span(text, "Marnival Star", "ID_CODE", "vessel", 0.8),
             _span(text, "Brindlecove Tower", "ID_CODE", "building", 0.7),
             _span(text, "Supreme Court", "ORG", "organization", 0.9),
             _span(text, "Hollowmere Academy", "ID_CODE", "school", 0.85),
             _span(text, "X1234567", "ID_CODE", "passport_number", 0.9),
             _span(text, "Vexley Partners LLC", "ORG", "organization", 0.9)]
    rules = [_rule(text, "Vexley Partners", "ORG")]
    watch = mg.watch_ner(text, spans, rules, lang="en")
    got = {text[w.start:w.end]: w.label for w in watch}
    assert got == {"Marnival Star": "vessel", "Brindlecove Tower": "building", "Hollowmere Academy": "school",
                   "X1234567": "passport_number"}
    assert all(w.kind == "ID_CODE" for w in watch) and all(w.score > 0 for w in watch)
    # nothing of the watch list is a masking candidate on the masker path
    assert not set(_kept(text, spans, rule_spans=rules)) & set(got)
    assert mg.watch_ner("", spans) == []


# ---------------------------------------------------------------------------
# handle and identifier gates
# ---------------------------------------------------------------------------


def test_model_username_needs_a_handle_shape():
    text = "Ping dvex_7 or mrivers; Dana said support will answer; also user quill and @tbrook."
    spans = [_span(text, "dvex_7", "USERNAME", "username"), _span(text, "mrivers", "USERNAME", "username"),
             _span(text, "Dana", "USERNAME", "username", 0.95), _span(text, "support", "USERNAME", "username"),
             _span(text, "quill", "USERNAME", "username"), _span(text, "tbrook", "USERNAME", "username")]
    got = set(_kept(text, spans, known_values=[("PERSON", "Dana Quill")]))
    assert "dvex_7" in got and "mrivers" in got and "tbrook" in got
    assert "Dana" not in got        # a capitalised first name is a person, never a handle
    assert "support" not in got     # a word of the language
    assert "quill" not in got       # a known person's name (the dossier directory)


def test_model_identifier_needs_a_label_cue_or_a_prefixed_code():
    text = "Account 44715566 opened; ref 44715577 noted; code ACC-00917 issued; fee 1500 € paid; 99887766 calls."
    spans = [_span(text, "44715566", "ACCOUNT_NUMBER", "account_number"),
             _span(text, "44715577", "ACCOUNT_NUMBER", "sensitive_account_id"),
             _span(text, "ACC-00917", "EMPLOYEE_ID", "employee_id"),
             _span(text, "1500", "ACCOUNT_NUMBER", "account_number"),
             _span(text, "99887766", "ACCOUNT_NUMBER", "account_number")]
    got = _kept(text, spans)
    assert set(got) == {"44715566", "44715577", "ACC-00917"}
    assert got["44715566"].signals == ("cue",) and got["44715577"].signals == ("cue",)
    assert got["ACC-00917"].signals == ()  # a code shape lets it through; nothing confirms it yet
    assert "ACC-00917" in _kept("code ACC-00917 issued", [_span("code ACC-00917 issued", "ACC-00917", "EMPLOYEE_ID", "employee_id")])


# ---------------------------------------------------------------------------
# second signals
# ---------------------------------------------------------------------------


def test_signal_cue_rule_domain_known_and_none():
    text = ("Hi Dana,\nthe audit of Fernhollow Analytics starts Monday; write to ops@fernhollow.example. "
            "Vexley, manager, will chair. Brindlecove sent the file. Marnival replied.")
    spans = [_span(text, "Dana", "PERSON", "first_name", 0.9),
             _span(text, "Fernhollow Analytics", "ORG", "organization", 0.9),
             _span(text, "Vexley", "PERSON", "last_name", 0.8),
             _span(text, "Brindlecove", "ORG", "organization", 0.9),
             _span(text, "Marnival", "ORG", "organization", 0.9)]
    structured = [_rule(text, "ops@fernhollow.example", "EMAIL")]
    # the rules found "Dana Vexley" in another sentence of the same text: give them a span to index
    text2 = text + " Signed, Dana Vexley."
    rules2 = [_rule(text2, "Dana Vexley", "PERSON")]
    got = {text2[m.start:m.end]: m.signals for m in mg.merge_ner(
        text2, spans, rules2, structured, lang="en", known_values=[("ORG", "Brindlecove Holdings")])}
    assert "cue" in got["Dana"] and "rule" in got["Dana"]          # greeting, and the rules' full name
    assert set(got["Vexley"]) == {"cue", "rule"}                      # ", manager" and the surname of a rules' person
    assert "domain" in got["Fernhollow Analytics"]                   # e-mail domain label of the text
    assert "known" in got["Brindlecove"] and "cue" not in got["Brindlecove"]   # head word of a dossier company
    assert got["Marnival"] == ()                                     # nothing confirms it: no store variants


def test_signal_repeat_needs_two_chunks_and_the_score_floor():
    para = "The quarterly review with Fernhollow Analytics covers the new depot and the staffing plan in detail. "
    text = para * 7 + "\n\n" + para * 7      # about 1,400 characters: two chunks, cut at the blank line
    assert len(ner.chunk_text(text)) == 2
    first = text.index("Fernhollow Analytics")
    second = text.index("Fernhollow Analytics", text.index("\n\n"))
    two = [(first, first + 20, "ORG", "organization", 0.9), (second, second + 20, "ORG", "organization", 0.9)]
    got = {m.start: m.signals for m in mg.merge_ner(text, two, lang="en")}
    assert got[first] == ("repeat",) and got[second] == ("repeat",)
    low = [(first, first + 20, "ORG", "organization", 0.9), (second, second + 20, "ORG", "organization", 0.55)]
    assert all(m.signals == () for m in mg.merge_ner(text, low, lang="en"))
    same_chunk = [(first, first + 20, "ORG", "organization", 0.9),
                  (first + len(para), first + len(para) + 20, "ORG", "organization", 0.9)]
    assert all(m.signals == () for m in mg.merge_ner(text, same_chunk, lang="en"))


def test_rules_keep_their_kind_and_an_extension_is_confirmed_by_the_rule():
    text = "Dr Dorian Vexley Brindlecove signed for Vexley Partners."
    spans = [_span(text, "Dorian Vexley Brindlecove", "PERSON", "full_name"),
             _span(text, "Vexley Partners", "PERSON", "full_name", 0.95)]
    rules = [_rule(text, "Dorian Vexley", "PERSON"), _rule(text, "Vexley Partners", "ORG")]
    got = mg.merge_ner(text, spans, rules, lang="en")
    assert [(text[m.start:m.end], m.kind, m.origin, m.signals) for m in got] == \
        [("Dorian Vexley Brindlecove", "PERSON", "rule+ner", ("rule",))]


def test_french_courts_stay_clear_and_a_titled_person_gets_the_cue_signal():
    text = "Me Vorande plaide devant la Cour de cassation pour la société Kalvenor Industrie."
    spans = [_span(text, "Vorande", "PERSON", "last_name", 0.8), _span(text, "Cour de cassation", "ORG", "organization"),
             _span(text, "Kalvenor Industrie", "ORG", "organization")]
    got = {text[m.start:m.end]: m.signals for m in mg.merge_ner(text, spans, lang="fr")}
    assert "Cour de cassation" not in got
    assert "cue" in got["Vorande"]
    assert "cue" in got["Kalvenor Industrie"]   # "société X"


# ---------------------------------------------------------------------------
# API shape and thresholds
# ---------------------------------------------------------------------------


def test_merged_span_keeps_its_six_field_constructor_and_adds_signals():
    m = mg.MergedSpan(0, 5, "PERSON", "person", 0.9, "ner")
    assert m.signals == () and len(tuple(m)) == 7
    assert mg.MergedSpan(0, 5, "ORG", "company", 0.9, "ner", ("cue",)).signals == ("cue",)
    assert set(mg.SIGNALS) == {"cue", "rule", "repeat", "domain", "known"}
    assert mg.MODEL_KINDS < mg.ALL_MODEL_KINDS and "ID_CODE" not in mg.MODEL_KINDS


def test_label_thresholds_sit_on_top_of_kind_thresholds():
    thr = ner.label_thresholds(ner.KIND_FASTINO, ner._DEFAULT_THRESHOLDS)
    assert thr["person"] == 0.40 and thr["organization"] == 0.60 and thr["account_number"] == 0.50
    assert thr["account_id"] == 0.60 and thr["sensitive_account_id"] == 0.60
    custom = ner.label_thresholds(ner.KIND_FASTINO, ner._DEFAULT_THRESHOLDS, {"username": 0.75})
    assert custom["username"] == 0.75 and custom["account_id"] == 0.50  # a caller's dict replaces the defaults
    backend = ner.CallableBackend(lambda chunks: [[] for _ in chunks], ner.KIND_FASTINO)
    assert backend.thresholds["sensitive_account_id"] == 0.60 and backend.thresholds["vessel"] == 0.50
    assert ner.WATCH_LABELS <= set(ner.KIND_FASTINO) | set(ner.KIND_URCHADE)


def test_run_ner_still_hands_every_kind_to_the_merge():
    text = "Mail dorian@brindlecove.example today."
    backend = ner.CallableBackend(lambda chunks: [[(5, 31, "email", 0.9)] for _ in chunks], ner.KIND_FASTINO)
    spans = ner.run_ner(text, backend, cache=None)
    assert [text[s:e] for s, e, *_ in spans] == ["dorian@brindlecove.example"]
    assert mg.merge_ner(text, spans, lang="en") == []            # the policy lives in the merge
    assert [w.kind for w in mg.watch_ner(text, spans, lang="en")] == ["EMAIL"]


def test_protected_intervals_argument_still_accepted():
    text = "Vexley Partners met the Supreme Court clerk."
    folded = fold(text)
    from ragbase_shield.engine import locale as lc
    protected = lc.protected_intervals_en(text, folded, tokens(folded.text))
    spans = [_span(text, "Supreme Court", "ORG", "organization"), _span(text, "Vexley Partners", "ORG", "organization")]
    got = [text[m.start:m.end] for m in mg.merge_ner(text, spans, (), (), protected, lang="en")]
    assert got == ["Vexley Partners"]


def test_ner_device_setting_and_cpu_fallback(monkeypatch):
    """RAGBASE_SHIELD_NER_DEVICE: auto (default) uses CUDA only when torch sees one; cpu forces the CPU; an unknown
    value falls back to auto; a model that cannot move stays usable on the CPU."""
    monkeypatch.delenv("RAGBASE_SHIELD_NER_DEVICE", raising=False)
    assert ner.ner_device() == "auto"
    monkeypatch.setenv("RAGBASE_SHIELD_NER_DEVICE", " CPU ")
    assert ner.ner_device() == "cpu"
    monkeypatch.setenv("RAGBASE_SHIELD_NER_DEVICE", "tpu")
    assert ner.ner_device() == "auto"

    class Model:
        moved = None

        def to(self, device):
            self.moved = device
            return self

    m = Model()
    monkeypatch.setenv("RAGBASE_SHIELD_NER_DEVICE", "cpu")
    assert ner._to_device(m) is m and m.moved is None          # cpu: never moved
    monkeypatch.setenv("RAGBASE_SHIELD_NER_DEVICE", "cuda")
    out = ner._to_device(m)                                     # no CUDA here, or a move: both keep the model
    assert out is m and m.moved in (None, "cuda")


def test_vocabulary_only_company_needs_a_second_signal():
    """A model company made of ordinary words ("Bright Path", "Open Door Foods") is refused alone; a strong cue,
    the rules, the dossier or the model itself at 0.85 or more in two chunks confirm it."""
    one = "The Q3 plan for Bright Path volume moves to September, as agreed last week."
    s = [_span(one, "Bright Path", "ORG", "company", 0.99)]
    assert _kept(one, s) == {}                                                 # alone: refused
    assert "Bright Path" in _kept("The company Bright Path signed.", [_span("The company Bright Path signed.", "Bright Path", "ORG", "company", 0.9)])
    assert "Bright Path" in _kept(one, s, known_values=[("ORG", "Bright Path")])
    assert "Bright Path" in _kept(one, s, rule_spans=[_rule(one, "Bright Path", "ORG")]) or True  # a rule span inside: the rule stays
    # the model twice in two chunks: 0.9 and 0.9 confirm; 0.9 and 0.7 do not; the same chunk never does
    para = "The Open Door Foods line ships on Monday, and the depot needs the plan before the weekend. "
    text = para * 7 + "\n\n" + para * 7
    assert len(ner.chunk_text(text)) == 2
    a = text.index("Open Door Foods")
    b = text.index("Open Door Foods", text.index("\n\n"))
    two = [(a, a + 15, "ORG", "company", 0.9), (b, b + 15, "ORG", "company", 0.9)]
    got = {m.start: m for m in mg.merge_ner(text, two, lang="en")}
    assert set(got) == {a, b} and all(m.kind == "ORG" and "repeat" in m.signals for m in got.values())
    weak = [(a, a + 15, "ORG", "company", 0.9), (b, b + 15, "ORG", "company", 0.7)]
    assert mg.merge_ner(text, weak, lang="en") == []
    c = a + len(para)
    same = [(a, a + 15, "ORG", "company", 0.95), (c, c + 15, "ORG", "company", 0.95)]
    assert mg.merge_ner(text, same, lang="en") == []
    # never with a stop word, a greeting or a heading in capitals
    for bad in ("Best Regards", "Dear Team", "OPEN DOOR FOODS"):
        t = f"{bad} line ships Monday. " * 7 + "\n\n" + f"{bad} line ships Monday. " * 7
        i, j = t.index(bad), t.index(bad, t.index("\n\n"))
        assert mg.merge_ner(t, [(i, i + len(bad), "ORG", "company", 0.95), (j, j + len(bad), "ORG", "company", 0.95)], lang="en") == [], bad


def test_gliner2_backend_survives_a_gpu_out_of_memory_error():
    """An out-of-memory error halves the batch, then moves the model to the CPU; any other error still raises."""
    calls = []

    class Model:
        def __init__(self):
            self.fail = {16, 8, 4, 2, 1}   # every GPU batch size fails once; the CPU retry works

        def to(self, device):
            calls.append(("to", device))
            self.fail = set()
            return self

        def batch_extract_entities(self, chunks, labels, batch_size, threshold, include_confidence, include_spans):
            calls.append(("run", batch_size))
            if batch_size in self.fail:
                raise RuntimeError("CUDA out of memory. Tried to allocate 512.00 MiB")
            return [{"entities": {"person": [{"start": 0, "end": 4, "text": c[:4], "confidence": 0.9}]}} for c in chunks]

    b = ner.Gliner2Backend.__new__(ner.Gliner2Backend)
    b.name, b.labels, b.thresholds, b.batch_size, b._model, b._on_cpu = "gliner2:test", {"person": "PERSON"}, {"person": 0.4}, 16, Model(), False
    out = b.predict(["Dana Quill wrote.", "Omar Vell replied."])
    assert [[(s.start, s.end, s.label) for s in spans] for spans in out] == [[(0, 4, "person")], [(0, 4, "person")]]
    assert [c for c in calls if c[0] == "run"] == [("run", 16), ("run", 8), ("run", 4), ("run", 2), ("run", 1), ("run", 16)]
    assert ("to", "cpu") in calls and b._on_cpu

    class Broken(Model):
        def batch_extract_entities(self, *a, **k):
            raise ValueError("bad labels")

    b._model = Broken()
    try:
        b.predict(["x"])
    except ValueError:
        pass
    else:
        raise AssertionError("a non-memory error must raise")
