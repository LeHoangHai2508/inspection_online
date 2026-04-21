from __future__ import annotations


def compare_symbol_value(expected_value: str, actual_value: str) -> bool:
    expected = {
        item.strip().upper()
        for item in expected_value.split("|")
        if item.strip()
    }
    actual = {
        item.strip().upper()
        for item in actual_value.split("|")
        if item.strip()
    }
    return expected == actual
