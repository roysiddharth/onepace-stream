from onepace.build_ledger import parse_entry, build_ledger

ARCS = ["Dressrosa", "Zou", "Whole Cake Island", "Reverie", "Wano", "Egghead"]

def test_parse_basic():
    rel = "[One Pace] Wano [1080p]/[One Pace] Wano 03 [1080p][AB12].mkv"
    assert parse_entry(rel, ARCS) == ("Wano", 3, "03")

def test_parse_two_digit_and_mp4():
    rel = "[One Pace] Egghead 12 [1080p][CD34].mp4"
    assert parse_entry(rel, ARCS) == ("Egghead", 12, "12")

def test_parse_multiword_arc():
    rel = "[One Pace] Whole Cake Island 05 [1080p][GH78].mkv"
    assert parse_entry(rel, ARCS) == ("Whole Cake Island", 5, "05")

def test_parse_skips_extended():
    rel = "[One Pace] Egghead 01 Extended [1080p][EF56].mkv"
    assert parse_entry(rel, ARCS) is None

def test_parse_skips_unknown_arc_and_nonvideo():
    assert parse_entry("[One Pace] Loguetown 01 [1080p].mkv", ARCS) is None
    assert parse_entry("[One Pace] Wano 01 [1080p].txt", ARCS) is None

def test_parse_chapter_bundle_range():
    # Dressrosa/Zou/Whole Cake Island only ship as whole-arc 720p bundles,
    # with per-file names like "Chapter 700-701" instead of an episode number.
    rel = "[One Pace][700-800] Dressrosa [720p]/[One Pace] Chapter 700-701 [720p][2A35B710].mkv"
    assert parse_entry(rel, ARCS) == ("Dressrosa", 700, "700-701")

def test_parse_chapter_bundle_single():
    rel = "[One Pace][801-822] Zou [720p]/[One Pace] Chapter 805 [720p][ABCDEF12].mkv"
    assert parse_entry(rel, ARCS) == ("Zou", 805, "805")

def test_parse_chapter_bundle_multiword_arc():
    rel = "[One Pace][823-902] Whole Cake Island [720p][ENG-ESP]/[One Pace] Chapter 850-851 [720p][11223344].mkv"
    assert parse_entry(rel, ARCS) == ("Whole Cake Island", 850, "850-851")

def test_build_orders_by_arc_then_number():
    files = [
        "[One Pace][801-822] Zou [720p]/[One Pace] Chapter 802 [720p].mkv",
        "[One Pace][700-800] Dressrosa [720p]/[One Pace] Chapter 710-711 [720p].mkv",
        "[One Pace][700-800] Dressrosa [720p]/[One Pace] Chapter 700-701 [720p].mkv",
        "junk.nfo",
    ]
    led = build_ledger(files, ARCS)
    assert [(e["arc"], e["number"]) for e in led] == [
        ("Dressrosa", 700), ("Dressrosa", 710), ("Zou", 802)
    ]
    assert all(e["watched"] is False for e in led)
    assert led[0]["label"] == "700-701"
    assert led[0]["relpath"] == "[One Pace][700-800] Dressrosa [720p]/[One Pace] Chapter 700-701 [720p].mkv"
