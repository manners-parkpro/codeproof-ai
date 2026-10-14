WEAKENED: dict[str, list[tuple[str, str]]] = {
    "accept reversed": [
        ("if start > end:", "if False:"),
    ],
    "validate first interval only": [
        ("for start, end in intervals:\n", "for start, end in intervals[:1]:\n"),
    ],
    "ignore negative reversal": [
        ("if start > end:", "if start > end and start >= 0:"),
    ],
    "accept overlap": [
        ("if previous_end > next_start:", "if False:"),
    ],
    "allow nesting": [
        ("(next_start, _) in zip", "(next_start, next_end) in zip"),
        ("if previous_end > next_start:", "if previous_end > next_start and previous_end <= next_end:"),
    ],
    "deduplicate intervals": [
        ("sorted((start, end) for start, end in intervals if start < end)",
         "sorted(set((start, end) for start, end in intervals if start < end))"),
    ],
    "check first pair only": [
        ("zip(occupied, occupied[1:])", "zip(occupied[:1], occupied[1:2])"),
    ],
    "allow one tick overlap": [
        ("if previous_end > next_start:", "if previous_end > next_start + 1:"),
    ],
    "trust input order": [
        ("sorted((start, end) for start, end in intervals if start < end)",
         "[(start, end) for start, end in intervals if start < end]"),
    ],
    "reject empty input": [
        ("    _validate_intervals(intervals)",
         "    if not intervals:\n        raise ValueError('empty')\n    _validate_intervals(intervals)"),
    ],
    "reject zero length": [
        ("if start > end:", "if start >= end:"),
    ],
    "include empty intervals in overlap check": [
        ("if start < end)", "if start <= end)"),
    ],
    "reject touching": [
        ("if previous_end > next_start:", "if previous_end >= next_start:"),
    ],
    "ignore negative overlap": [
        ("if previous_end > next_start:", "if previous_end > next_start and next_start >= 0:"),
    ],
    "limit coordinate range": [
        ("if start > end:", "if start > end or abs(start) > 2**63 or abs(end) > 2**63:"),
    ],
    "require exact int type": [
        ("if start > end:", "if start > end or type(start) is not int or type(end) is not int:"),
    ],
    "truncate coordinates": [
        ("return sum(end - start for start, end in intervals)",
         "return sum(int(float(end)) - int(float(start)) for start, end in intervals)"),
    ],
    "return bounding span": [
        ("return sum(end - start for start, end in intervals)",
         "return max((end for start, end in intervals), default=0) - min((start for start, end in intervals), default=0)"),
    ],
    "drop final interval": [
        ("return sum(end - start for start, end in intervals)",
         "return sum(end - start for start, end in intervals[:-1])"),
    ],
    "count endpoints": [
        ("return sum(end - start for start, end in intervals)",
         "return sum(end - start + 1 for start, end in intervals)"),
    ],
    "sort caller input": [
        ("    _validate_intervals(intervals)",
         "    intervals.sort()\n    _validate_intervals(intervals)"),
    ],
    "clear rejected input": [
        ('            raise ValueError("reversed interval")',
         '            intervals.clear()\n            raise ValueError("reversed interval")'),
    ],
    "assert validation": [
        ('        if start > end:\n            raise ValueError("reversed interval")',
         '        assert start <= end'),
        ('        if previous_end > next_start:\n            raise ValueError("overlapping intervals")',
         '        assert previous_end <= next_start'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "different exception": [
        ('raise ValueError("reversed interval")', 'raise RuntimeError("reversed interval")'),
        ('raise ValueError("overlapping intervals")', 'raise RuntimeError("overlapping intervals")'),
    ],
    "sort by start": [
        ("sorted((start, end) for start, end in intervals if start < end)",
         "sorted(((start, end) for start, end in intervals if start < end), key=lambda item: item[0])"),
    ],
    "equivalent empty filter": [
        ("if start < end)", "if start != end)"),
    ],
    "generator total": [
        ("return sum(end - start for start, end in intervals)",
         "return sum(map(lambda item: item[1] - item[0], intervals))"),
    ],
    "copied argument": [
        ("    _validate_intervals(intervals)",
         "    intervals = list(intervals)\n    _validate_intervals(intervals)"),
    ],
    "equivalent inequality": [
        ("if previous_end > next_start:", "if next_start < previous_end:"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
