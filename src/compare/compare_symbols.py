from __future__ import annotations


def compare_symbol_value(expected_value: str, actual_value: str) -> bool:
    return expected_value.strip().upper() == actual_value.strip().upper()
