"""
Unit tests for the HOS (Hours of Service) compliance engine.

Tests cover all FMCSA rules:
- T06: Edge cases and validation (inputs, constraints, boundary conditions)
- T14: Integration — schedule output correctness
"""
from datetime import datetime, timedelta
from django.test import TestCase

from trips.services.hos_engine import (
    calculate_schedule,
    HoSEngineError,
    MAX_DRIVING_HOURS,
    MAX_WINDOW_HOURS,
    BREAK_AFTER_HOURS,
    OFF_DUTY_RESET_HOURS,
    MAX_CYCLE_HOURS,
    MAX_MILES_BETWEEN_FUEL,
    STATUS_DRIVING,
    STATUS_ON_DUTY,
    STATUS_OFF_DUTY,
)


# ─── Helpers ────────────────────────────────────────────────────────────────

def _make_route(distance_miles: float, duration_hours: float = None) -> dict:
    """
    Build a minimal route_data dict for a single origin→pickup→dropoff trip.
    If duration_hours is None it is derived from distance at 60 mph.
    """
    if duration_hours is None:
        duration_hours = distance_miles / 60.0

    segments = [
        # to_pickup  (origin → pickup, 1 mi / short)
        {
            "type": "to_pickup",
            "from_name": "Origin",
            "to_name": "Pickup",
            "distance_miles": 1.0,
            "duration_hours": 1.0 / 60.0,
            "from_coords": [0.0, 0.0],
            "to_coords": [0.0, 0.01],
            "instructions": [],
        },
        # to_dropoff (pickup → dropoff, the bulk of the trip)
        {
            "type": "to_dropoff",
            "from_name": "Pickup",
            "to_name": "Dropoff",
            "distance_miles": distance_miles,
            "duration_hours": duration_hours,
            "from_coords": [0.0, 0.01],
            "to_coords": [0.0, 1.0],
            "instructions": [],
        },
    ]

    # Build a trivial 2-point polyline
    full_polyline = [[0.0, 0.0], [0.0, 1.0]]
    total_distance = sum(s["distance_miles"] for s in segments)
    total_duration = sum(s["duration_hours"] for s in segments)

    return {
        "segments": segments,
        "full_polyline": full_polyline,
        "total_distance_miles": total_distance,
        "total_duration_hours": total_duration,
        "waypoints": [],
    }


START_TIME = datetime(2024, 1, 15, 8, 0, 0)  # Monday 08:00


# ─── Input Validation Tests ─────────────────────────────────────────────────

class TestHosEngineInputValidation(TestCase):
    """T06: Validate that the engine rejects invalid inputs gracefully."""

    def test_negative_cycle_hours_raises(self):
        """Negative cycle hours are not physically meaningful."""
        route = _make_route(100)
        with self.assertRaises(HoSEngineError):
            calculate_schedule(route, current_cycle_used=-1.0)

    def test_cycle_hours_exceeding_max_raises(self):
        """Cannot start a trip when the driver has already exceeded the 70-hr limit."""
        route = _make_route(100)
        with self.assertRaises(HoSEngineError):
            calculate_schedule(route, current_cycle_used=71.0)

    def test_cycle_hours_at_exact_max_raises(self):
        """Exactly at 70 hours should also raise since there is 0 h remaining."""
        route = _make_route(100)
        with self.assertRaises(HoSEngineError):
            calculate_schedule(route, current_cycle_used=70.0)

    def test_empty_segments_raises(self):
        """A route with no segments must fail cleanly."""
        route = {
            "segments": [],
            "full_polyline": [],
            "total_distance_miles": 0,
            "total_duration_hours": 0,
        }
        with self.assertRaises(HoSEngineError):
            calculate_schedule(route, current_cycle_used=0.0)

    def test_zero_distance_segment_is_skipped(self):
        """
        A segment with 0 miles / 0 hours should not cause infinite loops
        or exceptions — it must be silently skipped.
        """
        route = _make_route(100)
        # Inject a zero-distance segment in the middle
        route["segments"].insert(1, {
            "type": "to_dropoff",
            "from_name": "X",
            "to_name": "Y",
            "distance_miles": 0.0,
            "duration_hours": 0.0,
            "from_coords": [0, 0],
            "to_coords": [0, 0],
            "instructions": [],
        })
        result = calculate_schedule(route, current_cycle_used=0.0, start_time=START_TIME)
        self.assertIn("schedule", result)

    def test_default_start_time_is_used_when_none(self):
        """When start_time is None the engine should not raise."""
        route = _make_route(50)
        result = calculate_schedule(route, current_cycle_used=0.0, start_time=None)
        self.assertIn("schedule", result)
        self.assertTrue(len(result["schedule"]) > 0)


# ─── Short Trip Tests ────────────────────────────────────────────────────────

class TestHosEngineShortTrip(TestCase):
    """A very short trip should complete without any mandatory stops beyond pickup/dropoff."""

    def setUp(self):
        self.route = _make_route(distance_miles=50, duration_hours=1.0)
        self.result = calculate_schedule(
            self.route, current_cycle_used=0.0, start_time=START_TIME
        )

    def test_schedule_contains_driving(self):
        statuses = [e["status"] for e in self.result["schedule"]]
        self.assertIn(STATUS_DRIVING, statuses)

    def test_schedule_contains_pickup_on_duty(self):
        notes = [e["note"] for e in self.result["schedule"]]
        self.assertTrue(any("Pickup" in n for n in notes))

    def test_schedule_contains_dropoff_on_duty(self):
        notes = [e["note"] for e in self.result["schedule"]]
        self.assertTrue(any("Dropoff" in n for n in notes))

    def test_no_mandatory_rest_for_short_trip(self):
        """Under 8 hours driving — no 10-hr rest or 30-min break should appear."""
        off_duty_notes = [
            e["note"] for e in self.result["schedule"]
            if e["status"] == STATUS_OFF_DUTY
        ]
        self.assertEqual(len(off_duty_notes), 0,
                         f"Unexpected off-duty events for a 50-mile trip: {off_duty_notes}")

    def test_summary_miles_approx_correct(self):
        total = self.result["summary"]["total_miles"]
        # Driving distance is 50 miles from dropoff segment + 1 mile from pickup segment
        self.assertAlmostEqual(total, 51.0, delta=2.0)

    def test_stops_include_origin_pickup_dropoff(self):
        types = {s["type"] for s in self.result["stops"]}
        self.assertIn("origin", types)
        self.assertIn("pickup", types)
        self.assertIn("dropoff", types)

    def test_cycle_hours_remaining_decreased(self):
        remaining = self.result["summary"]["cycle_hours_remaining"]
        # Should have used at least the 1-hr pickup + driving + 1-hr dropoff
        self.assertLess(remaining, MAX_CYCLE_HOURS)


# ─── HOS-3: 30-Minute Break Rule ────────────────────────────────────────────

class TestHos30MinBreak(TestCase):
    """HOS-3: A 30-minute break is required after 8 hours of cumulative driving."""

    def test_break_appears_after_8h_driving(self):
        # Trip long enough to trigger the break (> 8 hrs driving)
        route = _make_route(distance_miles=600, duration_hours=10.0)
        result = calculate_schedule(route, current_cycle_used=0.0, start_time=START_TIME)

        break_stops = [s for s in result["stops"] if s["type"] == "break"]
        self.assertGreater(len(break_stops), 0,
                           "Expected at least one 30-min break for a 10-hour trip")

    def test_driving_per_stint_never_exceeds_break_threshold(self):
        """No continuous driving block should exceed 8 hours before a break."""
        route = _make_route(distance_miles=600, duration_hours=10.0)
        result = calculate_schedule(route, current_cycle_used=0.0, start_time=START_TIME)

        consecutive_driving = 0.0
        for event in result["schedule"]:
            if event["status"] == STATUS_DRIVING:
                consecutive_driving += event["duration_hours"]
            else:
                consecutive_driving = 0.0
            self.assertLessEqual(
                consecutive_driving, BREAK_AFTER_HOURS + 0.01,
                f"Consecutive driving {consecutive_driving:.2f}h exceeded 8h limit"
            )


# ─── HOS-1/HOS-2: 11-Hour Driving / 14-Hour Window ─────────────────────────

class TestHosShiftLimits(TestCase):
    """HOS-1 (11h driving) and HOS-2 (14h window) force a mandatory 10h rest."""

    def test_rest_stop_appears_in_long_trip(self):
        # 700 miles at 60 mph → ~11.7 hrs — crosses both the 11-hr driving and 14-hr window
        route = _make_route(distance_miles=700, duration_hours=11.7)
        result = calculate_schedule(route, current_cycle_used=0.0, start_time=START_TIME)

        rest_stops = [s for s in result["stops"] if s["type"] == "rest"]
        self.assertGreater(len(rest_stops), 0,
                           "Expected mandatory rest for a 700-mile trip")

    def test_driving_hours_per_shift_never_exceed_11(self):
        """Total driving within any shift must not exceed 11 hours."""
        route = _make_route(distance_miles=1500, duration_hours=25.0)
        result = calculate_schedule(route, current_cycle_used=0.0, start_time=START_TIME)

        driving_in_shift = 0.0
        for event in result["schedule"]:
            if event["status"] == STATUS_OFF_DUTY:
                if event["duration_hours"] >= OFF_DUTY_RESET_HOURS - 0.01:
                    # Rest reset — start a new shift
                    driving_in_shift = 0.0
            elif event["status"] == STATUS_DRIVING:
                driving_in_shift += event["duration_hours"]
                self.assertLessEqual(
                    driving_in_shift, MAX_DRIVING_HOURS + 0.01,
                    f"Driving {driving_in_shift:.2f}h exceeded 11-hr limit in a single shift"
                )

    def test_summary_has_rest_stops_count(self):
        route = _make_route(distance_miles=700, duration_hours=11.7)
        result = calculate_schedule(route, current_cycle_used=0.0, start_time=START_TIME)
        self.assertGreaterEqual(result["summary"]["num_rest_stops"], 1)


# ─── HOS-6: Fueling Every 1,000 Miles ───────────────────────────────────────

class TestHosFuelingRule(TestCase):
    """HOS-6: A fuel stop must occur at least every 1,000 miles."""

    def test_fuel_stop_appears_in_1200_mile_trip(self):
        route = _make_route(distance_miles=1200, duration_hours=20.0)
        result = calculate_schedule(route, current_cycle_used=0.0, start_time=START_TIME)

        fuel_stops = [s for s in result["stops"] if s["type"] == "fuel"]
        self.assertGreater(len(fuel_stops), 0,
                           "Expected at least one fuel stop for a 1,200-mile trip")

    def test_cumulative_miles_between_fuels_never_exceed_1000(self):
        """Miles between consecutive fuel stops must stay within the 1,000-mile limit."""
        route = _make_route(distance_miles=2500, duration_hours=42.0)
        result = calculate_schedule(route, current_cycle_used=0.0, start_time=START_TIME)

        miles_since_fuel = 0.0
        for event in result["schedule"]:
            if event["status"] == STATUS_DRIVING:
                miles_since_fuel += event["miles"]
                self.assertLessEqual(
                    miles_since_fuel, MAX_MILES_BETWEEN_FUEL + 1.0,  # 1 mi tolerance for avg speed math
                    f"Miles since last fuel ({miles_since_fuel:.1f}) exceeded 1,000-mile limit"
                )
            elif event["status"] == STATUS_ON_DUTY and "Fueling" in event.get("note", ""):
                miles_since_fuel = 0.0

    def test_fuel_stop_count_in_summary(self):
        route = _make_route(distance_miles=1200, duration_hours=20.0)
        result = calculate_schedule(route, current_cycle_used=0.0, start_time=START_TIME)
        self.assertGreaterEqual(result["summary"]["num_fuel_stops"], 1)


# ─── HOS-5: 70-Hour / 8-Day Cycle ───────────────────────────────────────────

class TestHosCycleLimit(TestCase):
    """HOS-5: The 70-hr/8-day cycle limit triggers a 34-hr restart."""

    def test_high_cycle_hours_used_causes_restart(self):
        """Starting near the 70-hr cycle limit should trigger a 34-hr cycle restart."""
        # 68 hrs used + 3 hrs trip → would exceed 70 hrs
        route = _make_route(distance_miles=180, duration_hours=3.0)
        result = calculate_schedule(route, current_cycle_used=68.0, start_time=START_TIME)

        restart_stops = [s for s in result["stops"] if s["type"] == "restart"]
        self.assertGreater(len(restart_stops), 0,
                           "Expected a 34-hr cycle restart when starting with 68h used")

    def test_cycle_hours_never_go_negative_in_summary(self):
        """cycle_hours_remaining in summary must always be >= 0."""
        route = _make_route(distance_miles=500, duration_hours=8.5)
        result = calculate_schedule(route, current_cycle_used=0.0, start_time=START_TIME)
        self.assertGreaterEqual(result["summary"]["cycle_hours_remaining"], 0.0)

    def test_zero_cycle_used_full_cycle_available(self):
        route = _make_route(distance_miles=100, duration_hours=2.0)
        result = calculate_schedule(route, current_cycle_used=0.0, start_time=START_TIME)
        # After a short trip, most of the 70h cycle should remain
        self.assertGreater(result["summary"]["cycle_hours_remaining"], 60.0)


# ─── Schedule Structure Tests ────────────────────────────────────────────────

class TestScheduleStructure(TestCase):
    """Validate that output schedule events are well-formed."""

    def setUp(self):
        self.route = _make_route(distance_miles=300, duration_hours=5.0)
        self.result = calculate_schedule(
            self.route, current_cycle_used=0.0, start_time=START_TIME
        )

    def test_each_event_has_required_fields(self):
        required_fields = {
            "status", "start_time", "end_time", "duration_hours",
            "location", "location_name", "note", "miles",
        }
        for event in self.result["schedule"]:
            missing = required_fields - set(event.keys())
            self.assertEqual(missing, set(), f"Event missing fields: {missing}")

    def test_events_are_chronologically_ordered(self):
        schedule = self.result["schedule"]
        for i in range(1, len(schedule)):
            prev_end = schedule[i - 1]["end_time"]
            curr_start = schedule[i]["start_time"]
            self.assertEqual(
                prev_end, curr_start,
                f"Gap/overlap between event {i-1} end ({prev_end}) and event {i} start ({curr_start})"
            )

    def test_summary_has_all_fields(self):
        expected_keys = {
            "total_driving_hours", "total_on_duty_hours", "total_off_duty_hours",
            "total_trip_hours", "total_miles", "num_fuel_stops", "num_rest_stops",
            "num_breaks", "num_cycle_restarts", "trip_start", "trip_end",
            "cycle_hours_remaining",
        }
        missing = expected_keys - set(self.result["summary"].keys())
        self.assertEqual(missing, set(), f"Summary missing keys: {missing}")

    def test_total_hours_are_non_negative(self):
        summary = self.result["summary"]
        self.assertGreaterEqual(summary["total_driving_hours"], 0)
        self.assertGreaterEqual(summary["total_on_duty_hours"], 0)
        self.assertGreaterEqual(summary["total_off_duty_hours"], 0)
        self.assertGreaterEqual(summary["total_trip_hours"], 0)

    def test_location_is_list_of_two_floats(self):
        for event in self.result["schedule"]:
            loc = event["location"]
            self.assertIsInstance(loc, list, "location must be a list")
            self.assertEqual(len(loc), 2, "location must have exactly 2 coordinates")

    def test_iteration_guard_does_not_trigger(self):
        """
        For any reasonable trip, the engine must not silently truncate output due
        to hitting the 200-iteration safety guard. We verify by checking that the
        total miles in the summary roughly matches the route distance.
        """
        route = _make_route(distance_miles=500, duration_hours=8.5)
        result = calculate_schedule(route, current_cycle_used=0.0, start_time=START_TIME)
        # Should drive close to 500 miles (within 10%)
        self.assertGreater(result["summary"]["total_miles"], 450)


# ─── ELD Log Integration Tests ──────────────────────────────────────────────

class TestEldLogGeneration(TestCase):
    """T14: Validate that ELD daily logs are properly generated from a schedule."""

    def test_eld_logs_generated_for_multi_day_trip(self):
        from trips.services.eld_generator import generate_daily_logs

        route = _make_route(distance_miles=1500, duration_hours=25.0)
        schedule_data = calculate_schedule(
            route, current_cycle_used=0.0, start_time=START_TIME
        )
        logs = generate_daily_logs(schedule_data)

        self.assertGreater(len(logs), 1, "Expected multiple ELD log days for a 25-hour trip")

    def test_eld_log_totals_add_to_24h(self):
        from trips.services.eld_generator import generate_daily_logs

        route = _make_route(distance_miles=1500, duration_hours=25.0)
        schedule_data = calculate_schedule(
            route, current_cycle_used=0.0, start_time=START_TIME
        )
        logs = generate_daily_logs(schedule_data)

        for log in logs:
            daily_total = sum(log["totals"].values())
            self.assertAlmostEqual(
                daily_total, 24.0, delta=0.1,
                msg=f"Day {log['date']} totals sum to {daily_total:.2f}h, expected 24h"
            )

    def test_eld_log_has_required_fields(self):
        from trips.services.eld_generator import generate_daily_logs

        route = _make_route(distance_miles=200, duration_hours=4.0)
        schedule_data = calculate_schedule(
            route, current_cycle_used=0.0, start_time=START_TIME
        )
        logs = generate_daily_logs(schedule_data)

        self.assertTrue(len(logs) >= 1)
        log = logs[0]
        for field in ("date", "day_number", "segments", "totals", "total_miles", "remarks"):
            self.assertIn(field, log, f"ELD log missing field: {field}")

    def test_eld_segments_cover_full_day(self):
        from trips.services.eld_generator import generate_daily_logs

        route = _make_route(distance_miles=200, duration_hours=4.0)
        schedule_data = calculate_schedule(
            route, current_cycle_used=0.0, start_time=START_TIME
        )
        logs = generate_daily_logs(schedule_data)

        for log in logs:
            if not log["segments"]:
                continue
            segments = sorted(log["segments"], key=lambda s: s["start_hour"])
            # First segment must start at 0
            self.assertAlmostEqual(segments[0]["start_hour"], 0.0, delta=0.01)
            # Last segment must end at 24
            self.assertAlmostEqual(segments[-1]["end_hour"], 24.0, delta=0.01)
