from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.config import CorrelationConfig
from src.correlation import correlate
from src.correlation.dtos import AlertDTO
from src.correlation.fingerprint import tier
from src.correlation.loader import load_alerts

CFG = CorrelationConfig(
    session_gap=timedelta(minutes=10),
    cascade_enabled=True,
    cascade_window=timedelta(minutes=10),
)

BASE = datetime(2026, 7, 9, 9, 0, 0, tzinfo=timezone.utc)


def mk(id, host, service, severity, message, offset_s, tags=("env:prod",)):
    return AlertDTO(
        id=id,
        timestamp=BASE + timedelta(seconds=offset_s),
        host=host,
        service=service,
        severity=severity,
        message=message,
        tags=tuple(tags),
    )


def by_id(incidents):
    return {i.id: i for i in incidents}


# --- Pass A ---------------------------------------------------------------

def test_single_alert_is_one_incident():
    inc = correlate([mk("a1", "web-01", "nginx", "critical", "boom", 0)], CFG)
    assert len(inc) == 1
    assert inc[0].alert_count == 1
    assert inc[0].id == "base:a1"


def test_burst_same_key_within_window_is_one_incident():
    alerts = [mk(f"a{i}", "web-03", "nginx", "critical", "502", i * 30) for i in range(4)]
    inc = correlate(alerts, CFG)
    assert len(inc) == 1
    assert inc[0].alert_count == 4
    assert inc[0].max_severity == "critical"
    assert inc[0].duration_s == 90  # 3 gaps * 30s


def test_gap_larger_than_window_splits_into_two():
    alerts = [
        mk("a1", "db-01", "postgres", "warning", "slow", 0),
        mk("a2", "db-01", "postgres", "warning", "slow", 60),
        mk("a3", "db-01", "postgres", "warning", "slow", 20 * 60),  # 20 min later
    ]
    inc = correlate(alerts, CFG)
    assert len(inc) == 2


def test_info_is_separated_from_actionable():
    alerts = [
        mk("a1", "web-01", "nginx", "critical", "502", 0),
        mk("a2", "web-01", "nginx", "info", "deploy done", 10),
    ]
    inc = correlate(alerts, CFG)
    assert len(inc) == 2
    tiers = {i.severity_tier for i in inc}
    assert tiers == {"actionable", "info"}


def test_warning_escalates_to_critical_stays_one_incident():
    alerts = [
        mk("a1", "svc-01", "api", "warning", "latency high", 0),
        mk("a2", "svc-01", "api", "critical", "500s", 60),
    ]
    inc = correlate(alerts, CFG)
    assert len(inc) == 1
    assert inc[0].max_severity == "critical"
    assert inc[0].warn_count == 1 and inc[0].crit_count == 1


# --- Pass B (cascade) -----------------------------------------------------

def _cascade_alerts():
    dep = ("env:prod", "region:us-east-1", "dependency:fraud-check")
    prod = ("env:prod", "region:us-east-1")
    return [
        mk("p1", "pay-01", "payment-api", "critical", "Timeout calling fraud-check", 0, dep),
        mk("p2", "pay-02", "payment-api", "critical", "Timeout calling fraud-check", 25, dep),
        mk("p3", "pay-03", "payment-api", "critical", "Timeout calling fraud-check", 50, dep),
        mk("f1", "fraud-01", "fraud-check", "critical", "OutOfMemoryError", 60, prod),
        mk("f2", "fraud-01", "fraud-check", "critical", "OutOfMemoryError", 100, prod),
    ]


def test_cascade_merges_across_hosts_and_services():
    inc = correlate(_cascade_alerts(), CFG)
    assert len(inc) == 1
    c = inc[0]
    assert c.correlation == "cascade"
    assert c.dependency == "fraud-check"
    assert c.alert_count == 5
    assert c.host is None


def test_cascade_region_guard_does_not_merge_across_regions():
    us = ("env:prod", "region:us-east-1", "dependency:fraud-check")
    eu = ("env:prod", "region:eu-west-1", "dependency:fraud-check")
    alerts = [
        mk("p1", "pay-01", "payment-api", "critical", "Timeout", 0, us),
        mk("f1", "fraud-01", "fraud-check", "critical", "OOM", 30, ("env:prod", "region:us-east-1")),
        mk("p2", "pay-09", "payment-api", "critical", "Timeout", 0, eu),
        mk("f2", "fraud-09", "fraud-check", "critical", "OOM", 30, ("env:prod", "region:eu-west-1")),
    ]
    inc = correlate(alerts, CFG)
    cascades = [i for i in inc if i.correlation == "cascade"]
    assert len(cascades) == 2
    assert {c.region for c in cascades} == {"us-east-1", "eu-west-1"}


def test_cascade_disabled_leaves_pass_a_untouched():
    off = CorrelationConfig(session_gap=timedelta(minutes=10), cascade_enabled=False)
    inc = correlate(_cascade_alerts(), off)
    assert all(i.correlation == "base" for i in inc)
    assert len(inc) == 4


# --- Determinism / robustness --------------------------------------------

def test_deterministic_ids_and_ordering():
    alerts = [mk(f"a{i}", "web-03", "nginx", "critical", "502", i * 30) for i in range(4)]
    first = correlate(alerts, CFG)
    second = correlate(list(reversed(alerts)), CFG)
    assert [i.id for i in first] == [i.id for i in second]
    assert first[0].id == "base:a0"


def test_empty_input():
    assert correlate([], CFG) == []


# --- Fingerprint ----------------------------------------------------------

def test_tier():
    assert tier("info") == "info"
    assert tier("warning") == tier("critical") == "actionable"


# --- Real sample data -----------------------------------------------------

def test_real_sample_reduces_meaningfully():
    path = Path(__file__).resolve().parents[2] / "data" / "sample_alerts.json"
    alerts = load_alerts(path)
    incidents = correlate(alerts, CFG)
    assert len(alerts) == 50
    assert len(incidents) < 30
    cascades = [i for i in incidents if i.correlation == "cascade"]
    assert len(cascades) == 1
    assert cascades[0].dependency == "fraud-check"
    assert cascades[0].alert_count >= 15
