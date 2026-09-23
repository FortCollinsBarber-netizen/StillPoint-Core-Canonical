from __future__ import annotations

from datetime import date

import pytest

from stillpoint.calendar_core.calendar import (
    CANONICAL_DAY001_WEEKDAY,
    CANONICAL_TEMPLATE_YEAR,
    MONTH_LENGTHS,
    MONTH_NAMES,
    common_date,
    month_day_from_ordinal,
    ordinal_day,
)
from stillpoint.calendar_core.observances import observances_for_ordinal
from stillpoint.calendar_core.population import address_from_ordinal
from stillpoint.calendar_core.runtime_surface import load_enacted_publication


EXPECTED_MONTH_NAMES = (
    "January", "February", "March", "April",
    "May", "June", "July", "August",
    "September", "October", "November", "December",
)
EXPECTED_MONTH_LENGTHS = (
    31, 28, 31, 30, 31, 30,
    31, 31, 30, 31, 30, 30,
)


def test_lockdown_preserves_every_named_date_january_1_through_december_30():
    assert MONTH_NAMES == EXPECTED_MONTH_NAMES
    assert MONTH_LENGTHS == EXPECTED_MONTH_LENGTHS
    assert CANONICAL_TEMPLATE_YEAR == 2026
    assert CANONICAL_DAY001_WEEKDAY == "Thursday"

    expected_ordinal = 1
    for month, length in enumerate(MONTH_LENGTHS, start=1):
        for day in range(1, length + 1):
            assert ordinal_day(month, day) == expected_ordinal
            assert month_day_from_ordinal(expected_ordinal) == (month, day)
            expected_ordinal += 1

    assert expected_ordinal == 365
    assert ordinal_day(12, 30) == 364


def test_lockdown_rejects_only_the_extra_year_dates():
    with pytest.raises(ValueError):
        ordinal_day(12, 31)
    with pytest.raises(ValueError):
        ordinal_day(2, 29)


def test_lockdown_repeats_one_364_day_weekday_grid_for_all_fifty_years():
    for ordinal in range(1, 365):
        expected = common_date(
            year=CANONICAL_TEMPLATE_YEAR,
            ordinal=ordinal,
        ).weekday
        observed = {
            common_date(year=year, ordinal=ordinal).weekday
            for year in range(2026, 2076)
        }
        assert observed == {expected}


def test_lockdown_publication_is_exactly_fifty_contiguous_364_day_years():
    document = load_enacted_publication()
    rows = document["years"]

    assert len(rows) == 50
    assert int(rows[0]["year"]) == 2026
    assert int(rows[-1]["year"]) == 2075

    for index, row in enumerate(rows[:-1]):
        next_row = rows[index + 1]
        opening = date.fromisoformat(row["openingCivilDate"])
        next_opening = date.fromisoformat(next_row["openingCivilDate"])
        assert int(next_row["year"]) == int(row["year"]) + 1
        assert (next_opening - opening).days == 364


def test_lockdown_key_dates_have_permanent_seed_weekdays():
    expected = {
        (1, 1): "Thursday",
        (2, 14): "Saturday",
        (4, 3): "Friday",
        (4, 5): "Sunday",
        (5, 10): "Sunday",
        (5, 25): "Monday",
        (6, 19): "Friday",
        (6, 21): "Sunday",
        (7, 4): "Saturday",
        (9, 7): "Monday",
        (10, 31): "Saturday",
        (11, 11): "Wednesday",
        (11, 26): "Thursday",
        (12, 10): "Thursday",
        (12, 24): "Thursday",
        (12, 25): "Friday",
        (12, 30): "Wednesday",
    }

    for (month, day), weekday in expected.items():
        ordinal = ordinal_day(month, day)
        assert common_date(year=2026, ordinal=ordinal).weekday == weekday
        assert common_date(year=2075, ordinal=ordinal).weekday == weekday


def test_lockdown_december_30_to_january_1_preserves_week_rhythm():
    closing = common_date(year=2026, ordinal=364)
    opening = common_date(year=2027, ordinal=1)

    assert (closing.month, closing.day, closing.weekday) == (
        12,
        30,
        "Wednesday",
    )
    assert (opening.month, opening.day, opening.weekday) == (
        1,
        1,
        "Thursday",
    )
    assert closing.week == 52
    assert opening.week == 1


def test_lockdown_familiar_observances_hold_fixed_seed_positions():
    expected = {
        (1, 1): "New Year's Day",
        (2, 14): "Valentine's Day",
        (4, 3): "Good Friday",
        (4, 5): "Easter Sunday",
        (7, 4): "Independence Day",
        (10, 31): "Halloween",
        (11, 26): "Thanksgiving Day",
        (12, 24): "Christmas Eve",
        (12, 25): "Christmas Day",
        (12, 30): "New Year's Eve",
    }

    for (month, day), name in expected.items():
        names = {
            item.name
            for item in observances_for_ordinal(ordinal_day(month, day))
        }
        assert name in names


def test_lockdown_all_observance_addresses_repeat_across_fifty_years():
    document = load_enacted_publication()

    seed = {}
    for ordinal in range(1, 365):
        row = address_from_ordinal(
            publication_document=document,
            year=2026,
            ordinal=ordinal,
            jubilee_epoch_common_year=2026,
        )
        seed[ordinal] = (
            row.month,
            row.day,
            row.weekday,
            row.observance_ids,
            row.observance_names,
        )

    for year in range(2026, 2076):
        for ordinal in range(1, 365):
            row = address_from_ordinal(
                publication_document=document,
                year=year,
                ordinal=ordinal,
                jubilee_epoch_common_year=2026,
            )
            assert (
                row.month,
                row.day,
                row.weekday,
                row.observance_ids,
                row.observance_names,
            ) == seed[ordinal]


def test_lockdown_jubilee_changes_cycle_state_not_calendar_surface():
    document = load_enacted_publication()
    ordinal = ordinal_day(7, 10)

    ordinary = address_from_ordinal(
        publication_document=document,
        year=2026,
        ordinal=ordinal,
        jubilee_epoch_common_year=2026,
    )
    jubilee = address_from_ordinal(
        publication_document=document,
        year=2075,
        ordinal=ordinal,
        jubilee_epoch_common_year=2026,
    )

    assert (ordinary.month, ordinary.day, ordinary.weekday) == (
        jubilee.month,
        jubilee.day,
        jubilee.weekday,
    )
    assert ordinary.observance_ids == jubilee.observance_ids
    assert ordinary.is_jubilee_year is False
    assert jubilee.is_jubilee_year is True
    assert jubilee.is_jubilee_release_day is True
