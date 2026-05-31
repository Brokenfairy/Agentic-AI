"""Skill selection scoring helpers."""

from __future__ import annotations

from typing import Dict, Iterable, Set


def selection_metrics(expected: Iterable[str], actual: Iterable[str]) -> Dict[str, float]:
    expected_set: Set[str] = set(expected)
    actual_set: Set[str] = set(actual)
    true_positive = len(expected_set & actual_set)
    false_positive = len(actual_set - expected_set)
    false_negative = len(expected_set - actual_set)

    precision = true_positive / max(1, true_positive + false_positive)
    recall = true_positive / max(1, true_positive + false_negative)
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)

    return {
        "precision": round(precision, 2),
        "recall": round(recall, 2),
        "f1_score": round(f1, 2),
        "correctly_selected": true_positive,
        "incorrectly_selected": false_positive,
        "missed_skills": false_negative,
    }
