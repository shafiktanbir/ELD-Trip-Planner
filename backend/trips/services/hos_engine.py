"""
HOS (Hours of Service) Compliance Engine.

Implements FMCSA regulations for property-carrying drivers:
- HOS-1: 11-hour driving limit per shift
- HOS-2: 14-hour driving window (wall clock)
- HOS-3: 30-minute break after 8 hours cumulative driving
- HOS-4: 10-hour consecutive off-duty reset
- HOS-5: 70-hour/8-day cycle limit
- HOS-6: Fueling every 1,000 miles
- HOS-7: 1-hour pickup (On-Duty Not Driving)
- HOS-8: 1-hour dropoff (On-Duty Not Driving)
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from .route_service import interpolate_point_on_polyline

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────
MAX_DRIVING_HOURS = 11.0       # HOS-1: max driving per shift
MAX_WINDOW_HOURS = 14.0        # HOS-2: driving window from first on-duty
BREAK_AFTER_HOURS = 8.0        # HOS-3: mandatory break after cumulative driving
BREAK_DURATION_HOURS = 0.5     # HOS-3: 30-minute break
OFF_DUTY_RESET_HOURS = 10.0    # HOS-4: off-duty to reset shift
MAX_CYCLE_HOURS = 70.0         # HOS-5: 70-hour/8-day cycle
CYCLE_RESTART_HOURS = 34.0     # HOS-5: 34-hr restart
MAX_MILES_BETWEEN_FUEL = 1000  # HOS-6: fueling distance
FUEL_STOP_HOURS = 0.5          # Fueling duration (30 min)
PICKUP_DURATION_HOURS = 1.0    # HOS-7
DROPOFF_DURATION_HOURS = 1.0   # HOS-8

# Status types matching FMCSA log categories
STATUS_OFF_DUTY = "off_duty"
STATUS_SLEEPER = "sleeper_berth"
STATUS_DRIVING = "driving"
STATUS_ON_DUTY = "on_duty_not_driving"


class HoSEngineError(Exception):
    """Custom exception for HOS engine errors."""
    pass


class ScheduleEvent:
    """Represents a single event in the driving schedule."""

    def __init__(
        self,
        status: str,
        start_time: datetime,
        duration_hours: float,
        location: Optional[list] = None,
        location_name: str = "",
        note: str = "",
        miles: float = 0.0,
    ):
        self.status = status
        self.start_time = start_time
        self.duration_hours = round(duration_hours, 4)
        self.end_time = start_time + timedelta(hours=duration_hours)
        self.location = location or [0.0, 0.0]
        self.location_name = location_name
        self.note = note
        self.miles = round(miles, 1)

    def to_dict(self) -> dict:
        return {
            'status': self.status,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration_hours': self.duration_hours,
            'location': self.location,
            'location_name': self.location_name,
            'note': self.note,
            'miles': self.miles,
        }


def calculate_schedule(
    route_data: dict,
    current_cycle_used: float,
    start_time: Optional[datetime] = None,
) -> dict:
    """
    Calculate a complete FMCSA-compliant driving schedule.

    Args:
        route_data: Route data from route_service.get_route()
        current_cycle_used: Hours already used in the 70-hr/8-day cycle
        start_time: When the trip starts (defaults to now)

    Returns:
        dict with schedule events, stops for map markers, and summary stats
    """
    if start_time is None:
        start_time = datetime.now().replace(second=0, microsecond=0)

    # Validate inputs
    if current_cycle_used < 0:
        raise HoSEngineError("Current cycle hours used cannot be negative.")
    if current_cycle_used > MAX_CYCLE_HOURS:
        raise HoSEngineError(
            f"Current cycle hours ({current_cycle_used}) exceeds maximum ({MAX_CYCLE_HOURS})."
        )

    segments = route_data.get('segments', [])
    if not segments:
        raise HoSEngineError("No route segments provided.")

    full_polyline = route_data.get('full_polyline', [])
    total_route_miles = route_data.get('total_distance_miles', 0)

    # ─── Initialize Counters ──────────────────────────────────
    clock = start_time
    schedule: list[ScheduleEvent] = []
    stops: list[dict] = []

    # Shift-level counters (reset after 10-hr off-duty)
    drive_remaining = MAX_DRIVING_HOURS
    window_remaining = MAX_WINDOW_HOURS
    driving_since_break = 0.0

    # Cycle-level counter
    cycle_remaining = MAX_CYCLE_HOURS - current_cycle_used

    # Fueling counter
    miles_since_fuel = 0.0

    # Track total miles covered for polyline interpolation
    total_miles_covered = 0.0

    def _get_current_location() -> list:
        """Get GPS coordinates based on miles traveled along the route."""
        if total_route_miles <= 0 or not full_polyline:
            return [0.0, 0.0]
        fraction = min(total_miles_covered / total_route_miles, 1.0)
        return interpolate_point_on_polyline(full_polyline, fraction)

    def _add_event(
        status: str,
        duration: float,
        note: str = "",
        miles: float = 0.0,
        location_name: str = "",
    ):
        nonlocal clock
        loc = _get_current_location()
        event = ScheduleEvent(
            status=status,
            start_time=clock,
            duration_hours=duration,
            location=loc,
            location_name=location_name,
            note=note,
            miles=miles,
        )
        schedule.append(event)
        clock = event.end_time
        return event

    def _add_stop(stop_type: str, note: str, location_name: str = ""):
        loc = _get_current_location()
        stops.append({
            'type': stop_type,
            'time': clock.isoformat(),
            'location': loc,
            'location_name': location_name,
            'note': note,
        })

    def _reset_shift():
        nonlocal drive_remaining, window_remaining, driving_since_break
        drive_remaining = MAX_DRIVING_HOURS
        window_remaining = MAX_WINDOW_HOURS
        driving_since_break = 0.0

    def _need_cycle_restart() -> bool:
        return cycle_remaining <= 0

    # ─── Process Each Segment ─────────────────────────────────
    for seg_idx, segment in enumerate(segments):
        seg_type = segment.get('type', '')
        from_name = segment.get('from_name', '')
        to_name = segment.get('to_name', '')

        # ── Pickup Activity (before driving to dropoff) ────────
        if seg_type == 'to_pickup':
            # We are at the origin, about to drive to pickup
            _add_stop('origin', 'Trip start', from_name)
        elif seg_type == 'to_dropoff':
            # We just arrived at pickup — do 1-hr pickup activity
            # Check if we need a rest before pickup activity
            if window_remaining < PICKUP_DURATION_HOURS:
                _add_stop('rest', '10-hour mandatory rest (shift window expired before pickup)', to_name)
                _add_event(STATUS_OFF_DUTY, OFF_DUTY_RESET_HOURS,
                          "10-hour mandatory rest before pickup")
                _reset_shift()

            if cycle_remaining < PICKUP_DURATION_HOURS:
                _add_stop('restart', '34-hour cycle restart before pickup', to_name)
                _add_event(STATUS_OFF_DUTY, CYCLE_RESTART_HOURS,
                          "34-hour cycle restart")
                _reset_shift()
                cycle_remaining = MAX_CYCLE_HOURS

            _add_stop('pickup', '1-hour pickup (On-Duty Not Driving)', from_name)
            _add_event(STATUS_ON_DUTY, PICKUP_DURATION_HOURS,
                      "Pickup - loading cargo", location_name=from_name)
            window_remaining -= PICKUP_DURATION_HOURS
            cycle_remaining -= PICKUP_DURATION_HOURS

        # ── Drive the Segment ──────────────────────────────────
        remaining_miles = segment['distance_miles']
        remaining_hours = segment['duration_hours']

        if remaining_hours <= 0 or remaining_miles <= 0:
            continue

        avg_speed = remaining_miles / remaining_hours  # mph

        iteration_guard = 0
        max_iterations = 200  # Safety limit

        while remaining_hours > 0.001 and iteration_guard < max_iterations:
            iteration_guard += 1

            # Check if we need a cycle restart first
            if _need_cycle_restart():
                _add_stop('restart', '34-hour cycle restart (70-hr limit reached)')
                _add_event(STATUS_OFF_DUTY, CYCLE_RESTART_HOURS,
                          "34-hour cycle restart (70-hr cycle limit)")
                _reset_shift()
                cycle_remaining = MAX_CYCLE_HOURS

            # Calculate max driveable time considering all constraints
            max_by_drive = drive_remaining
            max_by_window = window_remaining
            max_by_break = BREAK_AFTER_HOURS - driving_since_break
            max_by_fuel = (MAX_MILES_BETWEEN_FUEL - miles_since_fuel) / avg_speed if avg_speed > 0 else float('inf')
            max_by_cycle = cycle_remaining

            max_drive_time = min(
                max_by_drive,
                max_by_window,
                max_by_break,
                max_by_fuel,
                max_by_cycle,
                remaining_hours,
            )

            if max_drive_time <= 0.001:
                # Determine WHY we can't drive and insert the right stop

                if max_by_break <= 0.001:
                    # 30-minute break required
                    _add_stop('break', '30-minute mandatory break (8-hr driving limit)')
                    _add_event(STATUS_OFF_DUTY, BREAK_DURATION_HOURS,
                              "30-minute mandatory break")
                    driving_since_break = 0.0
                    window_remaining -= BREAK_DURATION_HOURS

                elif max_by_fuel <= 0.001:
                    # Fueling stop — also counts as 30-min break
                    _add_stop('fuel', 'Fueling stop (1,000-mile interval)')
                    _add_event(STATUS_ON_DUTY, FUEL_STOP_HOURS,
                              "Fueling stop")
                    miles_since_fuel = 0.0
                    driving_since_break = 0.0  # >= 30 min → resets break counter
                    window_remaining -= FUEL_STOP_HOURS
                    cycle_remaining -= FUEL_STOP_HOURS

                elif max_by_drive <= 0.001 or max_by_window <= 0.001:
                    # 10-hour mandatory rest
                    _add_stop('rest', '10-hour mandatory rest (shift limit reached)')
                    _add_event(STATUS_OFF_DUTY, OFF_DUTY_RESET_HOURS,
                              "10-hour mandatory rest")
                    _reset_shift()

                elif max_by_cycle <= 0.001:
                    # 34-hour cycle restart
                    _add_stop('restart', '34-hour cycle restart (70-hr limit reached)')
                    _add_event(STATUS_OFF_DUTY, CYCLE_RESTART_HOURS,
                              "34-hour cycle restart (70-hr cycle limit)")
                    _reset_shift()
                    cycle_remaining = MAX_CYCLE_HOURS

                continue

            # ── DRIVE ──────────────────────────────────────────
            drive_miles = max_drive_time * avg_speed
            seg_from_name = from_name if remaining_hours == segment['duration_hours'] else ""
            seg_to_name = to_name if remaining_hours - max_drive_time <= 0.001 else ""

            drive_note = "Driving"
            if seg_from_name and seg_to_name:
                drive_note = f"Driving: {seg_from_name} → {seg_to_name}"
            elif seg_from_name:
                drive_note = f"Driving from {seg_from_name}"
            elif seg_to_name:
                drive_note = f"Driving to {seg_to_name}"

            _add_event(STATUS_DRIVING, max_drive_time, drive_note,
                      miles=drive_miles)

            # Update all counters
            drive_remaining -= max_drive_time
            window_remaining -= max_drive_time
            driving_since_break += max_drive_time
            cycle_remaining -= max_drive_time
            miles_since_fuel += drive_miles
            remaining_hours -= max_drive_time
            remaining_miles -= drive_miles
            total_miles_covered += drive_miles

        # ── Dropoff Activity (after driving to dropoff) ────────
        if seg_type == 'to_dropoff':
            # Check if we need a rest before dropoff
            if window_remaining < DROPOFF_DURATION_HOURS:
                _add_stop('rest', '10-hour mandatory rest before dropoff')
                _add_event(STATUS_OFF_DUTY, OFF_DUTY_RESET_HOURS,
                          "10-hour mandatory rest before dropoff")
                _reset_shift()

            if cycle_remaining < DROPOFF_DURATION_HOURS:
                _add_stop('restart', '34-hour cycle restart before dropoff')
                _add_event(STATUS_OFF_DUTY, CYCLE_RESTART_HOURS,
                          "34-hour cycle restart before dropoff")
                _reset_shift()
                cycle_remaining = MAX_CYCLE_HOURS

            _add_stop('dropoff', '1-hour dropoff (On-Duty Not Driving)', to_name)
            _add_event(STATUS_ON_DUTY, DROPOFF_DURATION_HOURS,
                      "Dropoff - unloading cargo", location_name=to_name)
            window_remaining -= DROPOFF_DURATION_HOURS
            cycle_remaining -= DROPOFF_DURATION_HOURS

    # ─── Build Summary ────────────────────────────────────────
    total_driving = sum(e.duration_hours for e in schedule if e.status == STATUS_DRIVING)
    total_on_duty = sum(e.duration_hours for e in schedule if e.status == STATUS_ON_DUTY)
    total_off_duty = sum(e.duration_hours for e in schedule if e.status in (STATUS_OFF_DUTY, STATUS_SLEEPER))
    total_miles = sum(e.miles for e in schedule if e.status == STATUS_DRIVING)

    trip_start = schedule[0].start_time if schedule else start_time
    trip_end = schedule[-1].end_time if schedule else start_time

    return {
        'schedule': [e.to_dict() for e in schedule],
        'stops': stops,
        'summary': {
            'total_driving_hours': round(total_driving, 2),
            'total_on_duty_hours': round(total_on_duty, 2),
            'total_off_duty_hours': round(total_off_duty, 2),
            'total_trip_hours': round((trip_end - trip_start).total_seconds() / 3600, 2),
            'total_miles': round(total_miles, 1),
            'num_fuel_stops': sum(1 for s in stops if s['type'] == 'fuel'),
            'num_rest_stops': sum(1 for s in stops if s['type'] == 'rest'),
            'num_breaks': sum(1 for s in stops if s['type'] == 'break'),
            'num_cycle_restarts': sum(1 for s in stops if s['type'] == 'restart'),
            'trip_start': trip_start.isoformat(),
            'trip_end': trip_end.isoformat(),
            'cycle_hours_remaining': round(cycle_remaining, 2),
        },
    }
