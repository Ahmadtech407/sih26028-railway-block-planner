"""
Unit tests for Destination Alarm Logic (SIH26028).
"""

import time
from typing import Optional


def should_trigger_alarm(
    enabled: bool,
    eta_min: Optional[int],
    buffer_min: int,
    dismissed: bool,
    snoozed_until: Optional[float] = None,
) -> bool:
    """Core logic to determine if the destination wake-up alarm should trigger."""
    if not enabled:
        return False
    if dismissed:
        return False
    if snoozed_until is not None and time.time() < snoozed_until:
        return False
    if eta_min is None:
        return False
    return eta_min <= buffer_min


def test_alarm_triggers_when_within_buffer():
    assert should_trigger_alarm(enabled=True, eta_min=10, buffer_min=15, dismissed=False) is True
    assert should_trigger_alarm(enabled=True, eta_min=15, buffer_min=15, dismissed=False) is True
    assert should_trigger_alarm(enabled=True, eta_min=5, buffer_min=10, dismissed=False) is True


def test_alarm_does_not_trigger_outside_buffer():
    assert should_trigger_alarm(enabled=True, eta_min=20, buffer_min=15, dismissed=False) is False
    assert should_trigger_alarm(enabled=True, eta_min=16, buffer_min=15, dismissed=False) is False


def test_alarm_disabled_does_not_trigger():
    assert should_trigger_alarm(enabled=False, eta_min=5, buffer_min=15, dismissed=False) is False


def test_alarm_dismissed_does_not_trigger():
    assert should_trigger_alarm(enabled=True, eta_min=5, buffer_min=15, dismissed=True) is False


def test_alarm_snoozed_does_not_trigger():
    snooze_target = time.time() + 300  # 5 minutes in future
    assert should_trigger_alarm(enabled=True, eta_min=5, buffer_min=15, dismissed=False, snoozed_until=snooze_target) is False

    # After snooze expires
    past_target = time.time() - 10
    assert should_trigger_alarm(enabled=True, eta_min=5, buffer_min=15, dismissed=False, snoozed_until=past_target) is True


def test_alarm_with_none_eta():
    assert should_trigger_alarm(enabled=True, eta_min=None, buffer_min=15, dismissed=False) is False
