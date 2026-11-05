import json

import pytest

from longweekend.holidays import (
    load_holidays,
    parse_blackouts,
    us_federal_holidays,
)


class TestUsFederal2026:
    def test_thanksgiving_day_2026(self):
        h = us_federal_holidays(2026)
        from datetime import date

        assert h[date(2026, 11, 26)] == "Thanksgiving Day"

    def test_july_4_observed_friday_when_saturday(self):
        from datetime import date

        h = us_federal_holidays(2026)
        # Jul 4, 2026 is a Saturday -> observed Friday Jul 3
        assert date(2026, 7, 4).weekday() == 5
        assert "Independence Day" in h[date(2026, 7, 3)]

    def test_memorial_day_is_last_monday(self):
        from datetime import date

        h = us_federal_holidays(2026)
        assert date(2026, 5, 25) in h
        assert date(2026, 5, 25).weekday() == 0

    def test_mlk_is_third_monday(self):
        from datetime import date

        h = us_federal_holidays(2026)
        assert date(2026, 1, 19) in h

    def test_eleven_entries_for_2026(self):
        # 5 fixed + 6 floating = 11; no observed days fall outside 2026
        assert len(us_federal_holidays(2026)) == 11

    def test_sunday_holiday_moves_to_monday(self):
        from datetime import date

        # Juneteenth Jun 19, 2027 falls on a Saturday? 2027-06-19 is Saturday -> Fri Jun 18
        h = us_federal_holidays(2027)
        assert date(2027, 6, 19).weekday() == 5
        assert "Juneteenth" in h[date(2027, 6, 18)]

    def test_no_observed_days_leak_outside_the_year(self):
        h = us_federal_holidays(2022)
        assert all(d.year == 2022 for d in h)


class TestCustomHolidays:
    def test_json_object_form(self, tmp_path):
        f = tmp_path / "h.json"
        f.write_text(
            json.dumps(
                {"holidays": [{"date": "2026-07-03", "name": "Summer Break"}]}
            ),
            encoding="utf-8",
        )
        from datetime import date

        assert load_holidays(str(f), 2026) == {date(2026, 7, 3): "Summer Break"}

    def test_json_list_form_with_optional_name(self, tmp_path):
        f = tmp_path / "h.json"
        f.write_text(json.dumps(["2026-12-24 Company Eve"]), encoding="utf-8")
        from datetime import date

        assert load_holidays(str(f), 2026) == {date(2026, 12, 24): "Company Eve"}

    def test_dates_outside_year_are_filtered(self, tmp_path):
        f = tmp_path / "h.json"
        f.write_text(
            json.dumps(["2026-01-01", "2025-07-04 Old News"]), encoding="utf-8"
        )
        from datetime import date

        assert list(load_holidays(str(f), 2026)) == [date(2026, 1, 1)]

    def test_none_spec_is_empty(self):
        assert load_holidays("none", 2026) == {}

    def test_bad_spec_raises(self):
        with pytest.raises(ValueError):
            load_holidays("martian-federal", 2026)

    def test_bad_date_raises(self, tmp_path):
        f = tmp_path / "h.json"
        f.write_text(json.dumps(["2026-13-99"]), encoding="utf-8")
        with pytest.raises(ValueError):
            load_holidays(str(f), 2026)


class TestBlackouts:
    def test_single_date(self):
        from datetime import date

        assert parse_blackouts(["2026-11-26"]) == {date(2026, 11, 26)}

    def test_range_is_inclusive(self):
        from datetime import date

        got = parse_blackouts(["2026-12-24..2026-12-26"])
        assert got == {date(2026, 12, d) for d in (24, 25, 26)}

    def test_comma_and_space_mixing(self):
        from datetime import date

        got = parse_blackouts(["2026-01-01, 2026-01-02"])
        assert got == {date(2026, 1, 1), date(2026, 1, 2)}

    def test_reversed_range_raises(self):
        with pytest.raises(ValueError):
            parse_blackouts(["2026-12-26..2026-12-24"])

    def test_bad_token_raises(self):
        with pytest.raises(ValueError):
            parse_blackouts(["not-a-date"])
