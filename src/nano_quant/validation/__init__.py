"""Validation utilities. Software tests are not evidence of real-world alpha."""

from nano_quant.validation.research import (
    NegativeControlResult,
    WalkForwardWindow,
    circular_shift_negative_control,
    rank_ic,
    walk_forward_windows,
)

__all__ = [
    "NegativeControlResult",
    "WalkForwardWindow",
    "circular_shift_negative_control",
    "rank_ic",
    "walk_forward_windows",
]
