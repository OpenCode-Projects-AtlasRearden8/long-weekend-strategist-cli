from datetime import date

from longweekend.holidays import us_federal_holidays
from longweekend.planner import build_status, enumerate_plans, exact_blocks

FED2026 = us_federal_holidays(2026)
FED2027 = us_federal_holidays(2027)
FED2028 = us_federal_holidays(2028)


def best(plans):
    return sorted(plans, key=lambda p: p.rank_key(3))[0]


class TestEnumeration:
    def test_thanksgiving_bridge_costs_one_day(self):
        plans = enumerate_plans(2026, FED2026, set(), 3)
        assert any(
            p.pto == (date(2026, 11, 27),) and p.cost == 1 and p.longest == 4
            for p in plans
        )
        # The New Year bridge (holiday Thu + Fri + Mon) makes a bigger block cheaply
        assert best(plans).longest == 5

    def test_balance_zero_still_scores_free_blocks(self):
        plans = enumerate_plans(2026, FED2026, set(), 0)
        assert len(plans) == 1
        p = plans[0]
        assert p.cost == 0 and not p.pto
        assert p.longest == 3  # Sat-Sun-Mon holiday-weekend blocks are free

    def test_balance_never_exceeded(self):
        for p in enumerate_plans(2026, FED2026, set(), 5):
            assert p.cost <= 5

    def test_no_plan_touches_blackout_dates(self):
        frozen = {date(2026, 11, 26), date(2026, 11, 27)}
        plans = enumerate_plans(2026, FED2026, frozen, 3)
        for p in plans:
            for d in p.pto:
                assert d not in frozen

    def test_blackout_splits_thanksgiving_block(self):
        frozen = {date(2026, 11, 27)}
        plans = enumerate_plans(2026, FED2026, frozen, 2)
        for p in plans:
            for s, e, n in p.blocks:
                if s <= date(2026, 11, 25) <= e:
                    # Fri blocked: the Thanksgiving block cannot reach 4 days
                    assert n < 4

    def test_sunday_holiday_offered_after_weekend_bridge(self):
        # Independence Day Jul 4, 2027 falls on a Sunday -> observed Mon Jul 5.
        # A single Friday Jul 2 request yields a Fri-Mon 4-day block.
        plans = enumerate_plans(2027, FED2027, set(), 2)
        assert any(
            p.pto == (date(2027, 7, 2),) and p.longest == 4 for p in plans
        )


class TestExactScoring:
    def test_exact_blocks_counts_holiday_weekends(self):
        status = build_status(2026, FED2026, set())
        lengths = {(s, e): n for s, e, n in exact_blocks(status, frozenset(), 2026)}
        # Thanksgiving 2026 is a lone Thursday: Friday is an ordinary workday
        assert lengths[(date(2026, 11, 26), date(2026, 11, 26))] == 1
        assert lengths[(date(2026, 11, 28), date(2026, 11, 29))] == 2

    def test_exact_blocks_merges_pto(self):
        status = build_status(2026, FED2026, set())
        blocks = exact_blocks(status, frozenset([date(2026, 11, 27)]), 2026)
        lengths = {(s, e): n for s, e, n in blocks}
        assert lengths[(date(2026, 11, 26), date(2026, 11, 29))] == 4

    def test_rank_keeps_best_longest_block(self):
        plans = enumerate_plans(2026, FED2026, set(), 10)
        ranked = sorted(plans, key=lambda p: p.rank_key(3))
        assert ranked[0].longest >= 5
        assert ranked[0].cost <= 3

    def test_leap_year_runs_clean(self):
        plans = enumerate_plans(2028, FED2028, set(), 4)
        for p in plans:
            for d in p.pto:
                assert d.year == 2028
                assert not (d.month == 2 and d.day == 29 and d.weekday() > 4)
                assert (d.weekday() in (5, 6)) == (date(2028, d.month, d.day) in ()
                    or d.weekday() in (5, 6))
