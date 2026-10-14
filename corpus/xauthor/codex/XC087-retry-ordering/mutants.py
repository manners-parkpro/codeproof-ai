WEAKENED: dict[str, list[tuple[str, str]]] = {
    "retry_reverses_order": [
        ("while cursor > 0 and self._items[cursor - 1] > self._items[cursor]:", "while cursor > 0:"),
    ],
    "constructor_sorts_early": [
        ("[int(value) for value in priorities]", "sorted(int(value) for value in priorities)"),
    ],
    "constructor_drops_duplicates": [
        ("[int(value) for value in priorities]", "list(dict.fromkeys(int(value) for value in priorities))"),
    ],
    "empty_constructor_adds_value": [
        ("[int(value) for value in priorities]", "[int(value) for value in priorities] or [0]"),
    ],
    "source_alias": [
        ("[int(value) for value in priorities]", "priorities"),
    ],
    "source_subclass_alias": [
        ("[int(value) for value in priorities]", "[int(value) for value in priorities] if type(priorities) is list else priorities"),
    ],
    "skip_first_pair": [
        ("range(1, len(self._items))", "range(2, len(self._items))"),
    ],
    "skip_last_item": [
        ("range(1, len(self._items))", "range(1, len(self._items) - 1)"),
    ],
    "one_swap_per_item": [
        ("                cursor -= 1", "                break"),
    ],
    "descending_order": [
        ("self._items[cursor - 1] > self._items[cursor]", "self._items[cursor - 1] < self._items[cursor]"),
    ],
    "drop_sorted_duplicates": [
        ("        for right in range(1, len(self._items)):\n            cursor = right\n            while cursor > 0 and self._items[cursor - 1] > self._items[cursor]:\n                self._items[cursor - 1], self._items[cursor] = (\n                    self._items[cursor], self._items[cursor - 1]\n                )\n                cursor -= 1", "        self._items = sorted(set(self._items))"),
    ],
    "absolute_value_order": [
        ("        for right in range(1, len(self._items)):\n            cursor = right\n            while cursor > 0 and self._items[cursor - 1] > self._items[cursor]:\n                self._items[cursor - 1], self._items[cursor] = (\n                    self._items[cursor], self._items[cursor - 1]\n                )\n                cursor -= 1", "        self._items.sort(key=abs)"),
    ],
    "floating_point_order": [
        ("        for right in range(1, len(self._items)):\n            cursor = right\n            while cursor > 0 and self._items[cursor - 1] > self._items[cursor]:\n                self._items[cursor - 1], self._items[cursor] = (\n                    self._items[cursor], self._items[cursor - 1]\n                )\n                cursor -= 1", "        self._items.sort(key=float)"),
    ],
    "bounded_integer_conversion": [
        ("int(value) for value in priorities", "int(value) % (1 << 32) for value in priorities"),
    ],
    "large_input_bypass": [
        ("        for right in range(1, len(self._items)):", "        if len(self._items) > 8:\n            return\n        for right in range(1, len(self._items)):"),
    ],
    "zero_attempts_runs": [
        ("range(int(attempts))", "range(max(1, int(attempts)))"),
    ],
    "one_attempt_skipped": [
        ("range(int(attempts))", "range(int(attempts) - 1)"),
    ],
    "negative_attempts_runs": [
        ("range(int(attempts))", "range(abs(int(attempts)))"),
    ],
    "subtype_attempts_skipped": [
        ("range(int(attempts))", "range(attempts if type(attempts) is int else 0)"),
    ],
    "large_attempts_skipped": [
        ("range(int(attempts))", "range(int(attempts) if int(attempts) < (1 << 64) else 0)"),
    ],
    "callback_sees_unsorted": [
        ("                self._order()\n                acknowledge()", "                acknowledge()\n                self._order()"),
    ],
    "timeout_undoes_sort": [
        ("            except TimeoutError:\n                continue", "            except TimeoutError:\n                self._items.reverse()\n                continue"),
    ],
    "exception_undoes_sort": [
        ("                acknowledge()", "                try:\n                    acknowledge()\n                except BaseException:\n                    self._items.reverse()\n                    raise"),
    ],
    "second_call_undoes_sort": [
        ("        self._items = [int(value) for value in priorities]", "        self._items = [int(value) for value in priorities]\n        self._ordered = False"),
        ("    def _order(self) -> None:", "    def _order(self) -> None:\n        if self._ordered:\n            self._items.reverse()\n            return\n        self._ordered = True"),
    ],
    "plain_int_values_rejected": [
        ("        self._items = [int(value) for value in priorities]", "        if any(type(value) is not int for value in priorities):\n            raise ValueError\n        self._items = [int(value) for value in priorities]"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "builtin_sort": [
        ("        for right in range(1, len(self._items)):\n            cursor = right\n            while cursor > 0 and self._items[cursor - 1] > self._items[cursor]:\n                self._items[cursor - 1], self._items[cursor] = (\n                    self._items[cursor], self._items[cursor - 1]\n                )\n                cursor -= 1", "        self._items.sort()"),
    ],
    "selection_sort": [
        ("        for right in range(1, len(self._items)):\n            cursor = right\n            while cursor > 0 and self._items[cursor - 1] > self._items[cursor]:\n                self._items[cursor - 1], self._items[cursor] = (\n                    self._items[cursor], self._items[cursor - 1]\n                )\n                cursor -= 1", "        for left in range(len(self._items)):\n            smallest = min(range(left, len(self._items)), key=self._items.__getitem__)\n            self._items[left], self._items[smallest] = self._items[smallest], self._items[left]"),
    ],
    "retain_integer_subtypes": [
        ("[int(value) for value in priorities]", "list(priorities)"),
    ],
    "list_snapshot": [
        ("    def snapshot(self) -> tuple[int, ...]:\n        return tuple(self._items)", "    def snapshot(self) -> list[int]:\n        return list(self._items)"),
    ],
    "equivalent_comparison": [
        ("self._items[cursor - 1] > self._items[cursor]", "self._items[cursor] < self._items[cursor - 1]"),
    ],
    "swap_equal_values": [
        ("self._items[cursor - 1] > self._items[cursor]", "self._items[cursor - 1] >= self._items[cursor]"),
    ],
    "sort_once_before_retry": [
        ("        for _ in range(int(attempts)):\n            try:\n                self._order()", "        if attempts > 0:\n            self._order()\n        for _ in range(int(attempts)):\n            try:"),
    ],
    "propagate_timeout": [
        ("            except TimeoutError:\n                continue", "            except TimeoutError:\n                raise"),
    ],
    "translate_timeout": [
        ("            except TimeoutError:\n                continue", "            except TimeoutError:\n                raise RuntimeError('acknowledgment failed')"),
    ],
    "changed_return": [
        ("                return\n", "                return True\n"),
    ],
    "direct_integer_range": [
        ("range(int(attempts))", "range(attempts)"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {
}

