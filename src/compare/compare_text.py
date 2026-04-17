from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from src.domain.decision_schema import ComparisonPolicy
from src.domain.enums import CompareType, FieldPriority
from src.domain.models import TemplateFieldDefinition


@dataclass(frozen=True)
class TextComparisonResult:
    matched: bool
    similarity: float
    expected_value: str
    actual_value: str


class TextNormalizer:
    """Normalizes OCR text before compare without being too aggressive."""

    _unicode_cleanup = str.maketrans(
        {
            "\u2013": "-",
            "\u2014": "-",
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
        }
    )

    def normalize(self, value: str, field: TemplateFieldDefinition) -> str:
        cleaned = value.translate(self._unicode_cleanup)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Critical fields keep their original punctuation and casing policy
        # because over-normalization may hide business-critical defects.
        if field.priority != FieldPriority.CRITICAL and not field.case_sensitive:
            cleaned = cleaned.upper()

        return cleaned


class TextComparator:
    def __init__(
        self,
        policy: ComparisonPolicy | None = None,
        normalizer: TextNormalizer | None = None,
    ) -> None:
        self._policy = policy or ComparisonPolicy()
        self._normalizer = normalizer or TextNormalizer()

    def compare(
        self,
        field: TemplateFieldDefinition,
        actual_value: str,
    ) -> TextComparisonResult:
        expected_value = self._normalizer.normalize(field.expected_value, field)
        normalized_actual = self._normalizer.normalize(actual_value, field)

        if field.compare_type == CompareType.REGEX:
            pattern = field.regex_pattern or field.expected_value
            matched = re.fullmatch(pattern, actual_value.strip()) is not None
            similarity = 1.0 if matched else 0.0
        elif field.compare_type == CompareType.FUZZY:
            similarity = SequenceMatcher(
                a=expected_value,
                b=normalized_actual,
            ).ratio()
            threshold = field.fuzzy_threshold or self._policy.default_fuzzy_threshold
            matched = similarity >= threshold
        else:
            matched = expected_value == normalized_actual
            similarity = 1.0 if matched else 0.0

        return TextComparisonResult(
            matched=matched,
            similarity=similarity,
            expected_value=expected_value,
            actual_value=normalized_actual,
        )
