"""
ELD (Electronic Logging Device) Daily Log Generator.

Converts the HOS engine's raw schedule into per-day ELD log data
that matches the FMCSA grid format for the frontend Canvas renderer.

Each day runs from midnight to midnight (00:00 to 24:00).
Events spanning midnight are split across two days.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Status types matching FMCSA log categories (same as hos_engine)
STATUS_OFF_DUTY = "off_duty"
STATUS_SLEEPER = "sleeper_berth"
STATUS_DRIVING = "driving"
STATUS_ON_DUTY = "on_duty_not_driving"

# Status display order on the FMCSA grid (top to bottom)
STATUS_ORDER = [STATUS_OFF_DUTY, STATUS_SLEEPER, STATUS_DRIVING, STATUS_ON_DUTY]
STATUS_ROW_INDEX = {s: i for i, s in enumerate(STATUS_ORDER)}


def generate_daily_logs(schedule_data: dict) -> list:
    """
    Convert a schedule into per-day ELD log sheets.

    Args:
        schedule_data: Output from hos_engine.calculate_schedule()

    Returns:
        List of daily log dicts, each containing:
        - date: "YYYY-MM-DD"
        - segments: list of {status, start_hour, end_hour}
        - totals: {off_duty, sleeper_berth, driving, on_duty_not_driving}
        - total_miles: miles driven this day
        - remarks: list of {time, text, location}
    """
    schedule = schedule_data.get('schedule', [])
    if not schedule:
        return []

    # Parse schedule events and determine date range
    events = []
    for event in schedule:
        start = _parse_time(event['start_time'])
        end = _parse_time(event['end_time'])
        events.append({
            'status': event['status'],
            'start_time': start,
            'end_time': end,
            'duration_hours': event['duration_hours'],
            'location': event.get('location', [0, 0]),
            'location_name': event.get('location_name', ''),
            'note': event.get('note', ''),
            'miles': event.get('miles', 0),
        })

    if not events:
        return []

    # Find the date range
    first_date = events[0]['start_time'].date()
    last_date = events[-1]['end_time'].date()

    # If the last event ends exactly at midnight, it belongs to the previous day
    if events[-1]['end_time'].hour == 0 and events[-1]['end_time'].minute == 0:
        last_date = last_date - timedelta(days=1)

    # Generate a log for each day
    daily_logs = []
    current_date = first_date

    while current_date <= last_date:
        day_start = datetime(current_date.year, current_date.month, current_date.day)
        day_end = day_start + timedelta(days=1)

        day_segments = []
        day_remarks = []
        day_miles = 0.0

        for event in events:
            # Check if this event overlaps with this day
            if event['end_time'] <= day_start or event['start_time'] >= day_end:
                continue

            # Clip event to this day's boundaries
            clipped_start = max(event['start_time'], day_start)
            clipped_end = min(event['end_time'], day_end)

            start_hour = (clipped_start - day_start).total_seconds() / 3600
            end_hour = (clipped_end - day_start).total_seconds() / 3600

            if end_hour - start_hour < 0.001:
                continue

            day_segments.append({
                'status': event['status'],
                'start_hour': round(start_hour, 4),
                'end_hour': round(end_hour, 4),
            })

            # Calculate proportional miles for this day's portion
            if event['miles'] > 0 and event['duration_hours'] > 0:
                portion = (end_hour - start_hour) / (event['duration_hours'])
                day_miles += event['miles'] * portion

            # Add remark for status changes that start on this day
            if event['start_time'] >= day_start and event['start_time'] < day_end:
                time_str = clipped_start.strftime('%H:%M')
                remark_text = event['note'] or f"Status: {_format_status(event['status'])}"
                day_remarks.append({
                    'time': time_str,
                    'text': remark_text,
                    'location': event.get('location_name', ''),
                })

        # Fill gaps with off-duty to ensure 24-hour coverage
        day_segments = _fill_gaps(day_segments)

        # Calculate totals per status
        totals = {
            STATUS_OFF_DUTY: 0.0,
            STATUS_SLEEPER: 0.0,
            STATUS_DRIVING: 0.0,
            STATUS_ON_DUTY: 0.0,
        }
        for seg in day_segments:
            duration = seg['end_hour'] - seg['start_hour']
            if seg['status'] in totals:
                totals[seg['status']] += duration

        # Round totals
        totals = {k: round(v, 2) for k, v in totals.items()}

        daily_logs.append({
            'date': current_date.isoformat(),
            'day_number': (current_date - first_date).days + 1,
            'segments': day_segments,
            'totals': totals,
            'total_miles': round(day_miles, 1),
            'remarks': day_remarks,
        })

        current_date += timedelta(days=1)

    return daily_logs


def _fill_gaps(segments: list) -> list:
    """
    Fill any gaps in the day's segments with off-duty time.
    Ensures segments cover exactly 0.0 to 24.0 hours.
    """
    if not segments:
        return [{'status': STATUS_OFF_DUTY, 'start_hour': 0.0, 'end_hour': 24.0}]

    # Sort by start time
    segments.sort(key=lambda s: s['start_hour'])

    filled = []
    current_hour = 0.0

    for seg in segments:
        # Fill gap before this segment
        if seg['start_hour'] > current_hour + 0.001:
            filled.append({
                'status': STATUS_OFF_DUTY,
                'start_hour': round(current_hour, 4),
                'end_hour': round(seg['start_hour'], 4),
            })

        filled.append(seg)
        current_hour = seg['end_hour']

    # Fill gap at the end of the day
    if current_hour < 23.999:
        filled.append({
            'status': STATUS_OFF_DUTY,
            'start_hour': round(current_hour, 4),
            'end_hour': 24.0,
        })

    return filled


def _parse_time(time_str: str) -> datetime:
    """Parse an ISO format datetime string."""
    if isinstance(time_str, datetime):
        return time_str
    # Handle both with and without microseconds
    for fmt in ('%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M'):
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    # Try with timezone info (strip it for simplicity)
    time_str = time_str.replace('+00:00', '').replace('Z', '')
    return datetime.fromisoformat(time_str)


def _format_status(status: str) -> str:
    """Format status string for display."""
    return status.replace('_', ' ').title()
