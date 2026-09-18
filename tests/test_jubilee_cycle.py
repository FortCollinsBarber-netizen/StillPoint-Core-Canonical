from tools.generate_jubilee_cycle import (
    MONTH_LENGTHS,
    generate_cycle,
    jubilee_year_state,
    ordinal_day,
    weekday_for_date,
)


def test_ordinary_grid_is_364_and_each_quarter_is_91():
    assert sum(MONTH_LENGTHS) == 364
    for q in range(0, 12, 3):
        assert sum(MONTH_LENGTHS[q:q+3]) == 91


def test_2026_fixed_date_examples_imply_consistent_friday_day001_epoch():
    assert weekday_for_date(12, 10, day001_weekday="Friday") == "Thursday"
    assert weekday_for_date(12, 25, day001_weekday="Friday") == "Friday"


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


def test_month_day_validation():
    assert ordinal_day(12, 31) == 364
