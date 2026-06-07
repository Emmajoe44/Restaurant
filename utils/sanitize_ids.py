def safe_int_ids(ids):
    """Return a list of integers from `ids`, ignoring non-integer values like 'virtual_123'."""
    if not ids:
        return []
    out = []
    for i in ids:
        try:
            out.append(int(i))
        except Exception:
            # ignore non-integer ids (e.g., virtual_770)
            continue
    return out
