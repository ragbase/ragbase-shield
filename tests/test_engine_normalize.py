"""Engine: folding with offsets, phrase matcher, lexicons."""
from ragbase_shield.engine import lexicon as lx
from ragbase_shield.engine.normalize import PhraseMatcher, fold, fold_word, normalize, phrase_tokens, tokens


def test_normalize_case_accents_spaces():
    assert normalize("  Hélène   VASSEUR-Garnier ") == "helene vasseur-garnier"
    assert normalize("Œuvre Æther straße") == "oeuvre aether strasse"
    assert normalize("Conseil d’État") == "conseil d'etat"
    assert normalize("Jean–Pierre") == "jean-pierre"


def test_fold_collapses_all_white_space_and_line_breaks():
    f = fold("Jean-Pierre\n\n  Dupont  SAS\tfin")
    assert f.text == "jean-pierre dupont sas fin"


def test_fold_drops_zero_width_and_soft_hyphen():
    assert fold("Du­po​nt﻿").text == "dupont"


def test_fold_offsets_map_back_to_original():
    text = "M. Hélène  VASSEUR’s Œuvre"
    f = fold(text)
    i = f.text.index("vasseur")
    s, e = f.span(i, i + len("vasseur"))
    assert text[s:e] == "VASSEUR"
    j = f.text.index("oeuvre")
    s, e = f.span(j, j + len("oeuvre"))
    assert text[s:e] == "Œuvre"
    k = f.text.index("helene")
    s, e = f.span(k, k + len("helene"))
    assert text[s:e] == "Hélène"


def test_fold_offsets_cover_collapsed_spaces():
    text = "a \n\t b"
    f = fold(text)
    assert f.text == "a b"
    assert f.span(0, 3) == (0, len(text))


def test_confusables_only_on_request():
    assert fold("Dup0nt l1ly").text == "dup0nt l1ly"
    assert fold("Dup0nt", confusables=True).text == fold("Dupont", confusables=True).text == "dupont"
    assert fold_word("Il1|", confusables=True) == fold_word("llll", confusables=True)


def test_tokens_and_phrase_tokens():
    assert phrase_tokens("J.-P. Dupont") == ("j", "p", "dupont")
    assert [t for t, _, _ in tokens(fold("d'Estaing, N'Dongo").text)] == ["d", "estaing", "n", "dongo"]


def test_phrase_matcher_gap_rules():
    pm = PhraseMatcher()
    pm.add(("jean", "pierre", "dupont"), "JPD")
    for ok in ("Jean-Pierre Dupont", "JEAN PIERRE\nDUPONT", "jean-pierre  dupont"):
        f = fold(ok)
        assert [p for _, _, p in pm.find_all(f.text, tokens(f.text))] == ["JPD"], ok
    for bad in ("Jean-Pierre, Dupont", "Jean-Pierre (Dupont)"):
        f = fold(bad)
        assert list(pm.find_all(f.text, tokens(f.text))) == [], bad


def test_lexicons_load_and_are_folded():
    fn = lx.first_names()
    assert len(fn) > 8000
    assert {"jean", "helene", "karim", "jean-pierre"} <= lx.all_first_names()
    assert "helene" in fn and "hélène" not in fn
    assert "paris" not in fn and "france" not in fn  # place names are not first-name signals
    assert "attendu" in lx.stopwords()
    assert "president" in lx.legal_terms()
    assert "blanc" in lx.common_words()
    wl = lx.whitelist_phrases()
    assert "cour de cassation" in wl and "conseil d'etat" in wl and "cnil" in wl
    assert "janvier" in wl and "lundi" in wl


def test_lexicon_files_have_attribution():
    from importlib import resources

    text = resources.files("ragbase_shield.engine.lexicon").joinpath("first_names_fr.txt").read_text(encoding="utf-8")
    head = "\n".join(line for line in text.splitlines() if line.startswith("#"))
    assert "INSEE" in head and "Licence Ouverte" in head
