"""Read/write helpers for episodes.json. The only module that touches state."""
import json


def load(path):
    with open(path) as f:
        return json.load(f)


def save(path, entries):
    with open(path, "w") as f:
        json.dump(entries, f, indent=2)


def next_unwatched(entries):
    """Index of the first not-yet-watched episode, or None if all watched."""
    for i, e in enumerate(entries):
        if not e["watched"]:
            return i
    return None


def mark_watched(entries, index):
    """Mark the episode at `index` watched, in place."""
    entries[index]["watched"] = True


def toggle_watched(entries, index):
    """Flip the watched state of the episode at `index`, in place."""
    entries[index]["watched"] = not entries[index]["watched"]


def merge_watched(old_entries, new_entries):
    """Carry `watched` over from old_entries into new_entries by relpath.

    Used when refreshing the ledger from a rescan: rescans always produce
    fresh entries with watched=False, so without this merge every refresh
    would silently erase watch progress.
    """
    watched_by_relpath = {e["relpath"]: e["watched"] for e in old_entries}
    for e in new_entries:
        if watched_by_relpath.get(e["relpath"]):
            e["watched"] = True
    return new_entries
