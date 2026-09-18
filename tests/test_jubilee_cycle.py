import datetime as dt

from tools.generate_jubilee_cycle import (
    MONTH_LENGTHS,
    common_position,
    generate_cycle,
    jubilee_year_state,
    month_day_from_ordinal,
    ordinal_day,
    position_from_boundary_date,
    weekday_for_date,
)


def test_ordinary_grid_is_364_and_each_quarter_is_91():
    assert sum(MONTH_LENGTHS) == 364
    for q in range(0, 12, 3):
        assert sum(MONTH_LENGTHS[q:q + 3]) == 91


def test_observation_zero_maps_to_real_common_position():
    position = position_from_boundary_date(
        opening_civil_date=dt.date(2026, 1, 1),
        active_boundary_civil_date=dt.date(2026, 9, 17),
        day001_weekday="Friday",
    )
    assert position == {
        "dayOfYear": 260,
        "month": 9,
        "day": 18,
        "quarter": 3,
        "dayOfQuarter": 78,
        "weekOfYear": 38,
        "dayInWeek": 1,
        "weekday": "Friday",
    }


def test_ordinal_round_trip():
    for ordinal in range(1, 365):
        month, day = month_day_from_ordinal(ordinal)
        assert ordinal_day(month, day) == ordinal


def test_fixed_date_examples_have_permanent_weekdays():
    assert weekday_for_date(12, 10, day001_weekday="Friday") == "Thursday"
    assert weekday_for_date(12, 25, day001_weekday="Friday") == "Friday"
    assert weekday_for_date(7, 10, day001_weekday="Friday") == "Sunday"


def test_biblical_fixed_feast_weekdays_are_deterministic():
    assert weekday_for_date(1, 14, day001_weekday="Friday") == "Thursday"
    assert weekday_for_date(1, 15, day001_weekday="Friday") == "Friday"
    assert weekday_for_date(7, 1, day001_weekday="Friday") == "Friday"
    assert weekday_for_date(7, 15, day001_weekday="Friday") == "Friday"


def test_fixed_date_weekday_is_independent_of_year_number():
    one = generate_cycle(first_common_year=1, day001_weekday="Friday")
    later = generate_cycle(first_common_year=500, day001_weekday="Friday")
    assert one["fixedWeekdayAnchors"] == later["fixedWeekdayAnchors"]


def test_sabbatical_thresholds_are_seven_sevens():
    thresholds = [
        y for y in range(1, 50)
        if jubilee_year_state(y)["isSabbaticalThreshold"]
    ]
    assert thresholds == [7, 14, 21, 28, 35, 42, 49]


def test_year_50_is_jubilee_with_day_of_atonement_release_gate():
    state = jubilee_year_state(50)
    assert state["isJubileeYear"] is True
    assert state["releaseGate"] == {
        "month": 7,
        "day": 10,
        "name": "Day of Atonement",
    }


def test_common_day_364_is_month_12_day_31():
    assert month_day_from_ordinal(364) == (12, 31)


def test_common_position_week_and_quarter_math():
    pos = common_position(260, day001_weekday="Friday")
    assert pos["weekOfYear"] == 38
    assert pos["quarter"] == 3
    assert pos["weekday"] == "Friday"
