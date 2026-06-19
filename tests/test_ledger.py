import json
from onepace import ledger

def make(tmp_path):
    data = [
        {"arc": "Water Seven", "number": 1, "relpath": "a.mkv", "watched": True},
        {"arc": "Water Seven", "number": 2, "relpath": "b.mkv", "watched": False},
        {"arc": "Water Seven", "number": 3, "relpath": "c.mkv", "watched": False},
    ]
    p = tmp_path / "episodes.json"
    p.write_text(json.dumps(data))
    return p

def test_next_unwatched(tmp_path):
    entries = ledger.load(make(tmp_path))
    assert ledger.next_unwatched(entries) == 1   # index of "b.mkv"

def test_next_unwatched_none_when_all_done(tmp_path):
    entries = ledger.load(make(tmp_path))
    for e in entries:
        e["watched"] = True
    assert ledger.next_unwatched(entries) is None

def test_mark_and_save_roundtrip(tmp_path):
    p = make(tmp_path)
    entries = ledger.load(p)
    ledger.mark_watched(entries, 1)
    ledger.save(p, entries)
    reloaded = ledger.load(p)
    assert reloaded[1]["watched"] is True
    assert ledger.next_unwatched(reloaded) == 2   # advances to "c.mkv"
