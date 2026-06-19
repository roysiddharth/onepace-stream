"""Build episodes.json from the downloaded One Pace files on disk."""
import json
import os
import re
import sys

VIDEO_EXT = (".mkv", ".mp4")


def parse_entry(relpath, arcs):
    """Return (arc, number, label) for a One Pace video file, or None to skip.

    Skips non-video files, 'Extended' cuts, and files whose arc is not in `arcs`.
    Matches the longest arc name first so multi-word arcs aren't shadowed by a
    shorter arc name that happens to be a substring.

    Most arcs ship as one file per episode named "<Arc> <number>" — `number`
    is the episode number and `label` is its zero-padded form. A few arcs
    (no 1080p release exists for them) only ship as a single whole-arc 720p
    bundle whose files are named "Chapter <start>[-<end>]" instead, with the
    arc name only present in the parent folder; for those, `number` is the
    starting chapter (used for ordering) and `label` is the chapter range.
    """
    name = os.path.basename(relpath)
    if not name.lower().endswith(VIDEO_EXT):
        return None
    if "extended" in name.lower():
        return None

    sorted_arcs = sorted(arcs, key=len, reverse=True)

    for arc in sorted_arcs:
        m = re.search(r"\b" + re.escape(arc) + r"\s+(\d+)\b", name)
        if m:
            number = int(m.group(1))
            return (arc, number, f"{number:02d}")

    cm = re.search(r"Chapter\s+(\d+)(?:-(\d+))?", name, re.IGNORECASE)
    if cm:
        dirname = os.path.basename(os.path.dirname(relpath))
        for arc in sorted_arcs:
            if re.search(r"\b" + re.escape(arc) + r"\b", dirname):
                start, end = cm.group(1), cm.group(2)
                label = f"{start}-{end}" if end else start
                return (arc, int(start), label)

    return None


def build_ledger(relpaths, arcs):
    """Turn a list of relative file paths into an ordered ledger list."""
    order = {a: i for i, a in enumerate(arcs)}
    entries = []
    for rel in relpaths:
        parsed = parse_entry(rel, arcs)
        if parsed is None:
            continue
        arc, number, label = parsed
        entries.append({
            "arc": arc, "number": number, "label": label,
            "relpath": rel, "watched": False,
        })
    entries.sort(key=lambda e: (order[e["arc"]], e["number"]))
    return entries


def _scan(root):
    rels = []
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            full = os.path.join(dirpath, f)
            rels.append(os.path.relpath(full, root))
    return rels


def main(argv):
    if len(argv) != 4:
        print("usage: build_ledger.py <download-root> <arc_order.txt> <out.json>")
        return 2
    root, arc_file, out = argv[1], argv[2], argv[3]
    arcs = [l.strip() for l in open(arc_file) if l.strip()]
    led = build_ledger(_scan(root), arcs)
    with open(out, "w") as f:
        json.dump(led, f, indent=2)
    print(f"wrote {len(led)} episodes to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
