"""
Route Service — OpenRouteService integration.

Handles geocoding locations and computing driving routes between waypoints.
Uses the driving-hgv (heavy goods vehicle) profile for truck routing.
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

ORS_BASE_URL = "https://api.openrouteservice.org"

# Conversion factors
METERS_TO_MILES = 0.000621371
SECONDS_TO_HOURS = 1 / 3600


class RouteServiceError(Exception):
    """Custom exception for route service errors."""
    pass


def _get_api_key() -> str:
    """Get the ORS API key from settings."""
    key = getattr(settings, 'ORS_API_KEY', '')
    if not key:
        raise RouteServiceError(
            "OpenRouteService API key not configured. "
            "Set ORS_API_KEY in your .env file."
        )
    return key


def geocode_location(text: str) -> dict:
    """
    Geocode a text location to coordinates using OpenRouteService.

    Args:
        text: Location string (e.g. "New York, NY" or "40.7128,-74.0060")

    Returns:
        dict with keys: lat, lng, display_name

    Raises:
        RouteServiceError: If geocoding fails
    """
    # Check if input is already coordinates ("lat,lng" format)
    parts = text.strip().split(',')
    if len(parts) == 2:
        try:
            lat = float(parts[0].strip())
            lng = float(parts[1].strip())
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                return {
                    'lat': lat,
                    'lng': lng,
                    'display_name': f"{lat:.4f}, {lng:.4f}"
                }
        except ValueError:
            pass  # Not coordinates, continue with geocoding

    api_key = _get_api_key()

    try:
        response = requests.get(
            f"{ORS_BASE_URL}/geocode/search",
            params={
                'api_key': api_key,
                'text': text,
                'boundary.country': 'US',
                'size': 1,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        features = data.get('features', [])
        if not features:
            raise RouteServiceError(
                f"Could not find location: '{text}'. "
                "Please provide a valid US address or city name."
            )

        geometry = features[0]['geometry']
        properties = features[0].get('properties', {})

        # ORS returns [lng, lat] — swap for our standard [lat, lng]
        lng, lat = geometry['coordinates']

        return {
            'lat': lat,
            'lng': lng,
            'display_name': properties.get('label', text),
        }

    except requests.exceptions.Timeout:
        raise RouteServiceError("Geocoding request timed out. Please try again.")
    except requests.exceptions.ConnectionError:
        raise RouteServiceError("Could not connect to geocoding service.")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            raise RouteServiceError("Invalid API key. Check your ORS_API_KEY.")
        elif e.response.status_code == 429:
            raise RouteServiceError("Rate limit exceeded. Please wait and try again.")
        raise RouteServiceError(f"Geocoding error: {e}")


# ORS hard limit for driving-hgv route distance (~3,728 mi = 6,000,000 m)
_ORS_MAX_ROUTE_MILES = 3700


def _validate_route_distance(origin: dict, pickup: dict, dropoff: dict) -> None:
    """
    Pre-flight check: reject routes whose straight-line total exceeds the ORS
    maximum before making an API call.

    ORS limits driving-hgv routes to 6,000,000 m (~3,728 miles).  We use a
    conservative 3,700-mile cap on the haversine (straight-line) distance,
    which is always shorter than the actual road distance.

    Raises:
        RouteServiceError: If the estimated route is too long.
    """
    import math

    def haversine_miles(a: dict, b: dict) -> float:
        R = 3959
        lat1, lng1 = math.radians(a['lat']), math.radians(a['lng'])
        lat2, lng2 = math.radians(b['lat']), math.radians(b['lng'])
        dlat, dlng = lat2 - lat1, lng2 - lng1
        x = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(x), math.sqrt(1 - x))

    total = haversine_miles(origin, pickup) + haversine_miles(pickup, dropoff)
    if total > _ORS_MAX_ROUTE_MILES:
        raise RouteServiceError(
            f"The total route distance is approximately {total:,.0f} miles, "
            f"which exceeds the maximum supported route length of "
            f"{_ORS_MAX_ROUTE_MILES:,} miles. "
            "Please choose locations that are closer together — "
            "this planner is designed for US domestic trips."
        )


def get_route(
    origin: dict,
    pickup: dict,
    dropoff: dict
) -> dict:
    """
    Compute a driving route: origin → pickup → dropoff.

    Args:
        origin: dict with lat, lng, display_name
        pickup: dict with lat, lng, display_name
        dropoff: dict with lat, lng, display_name

    Returns:
        dict with segments, total_distance_miles, total_duration_hours,
        full_polyline, and waypoints

    Raises:
        RouteServiceError: If routing fails
    """
    # Guard: reject before hitting ORS if the route is already too long
    _validate_route_distance(origin, pickup, dropoff)

    api_key = _get_api_key()

    # Build coordinate pairs: [lng, lat] format for ORS
    coordinates = [
        [origin['lng'], origin['lat']],
        [pickup['lng'], pickup['lat']],
        [dropoff['lng'], dropoff['lat']],
    ]

    try:
        response = requests.post(
            f"{ORS_BASE_URL}/v2/directions/driving-hgv",
            json={
                'coordinates': coordinates,
                'instructions': True,
                'geometry': True,
                'units': 'mi',
            },
            headers={
                'Authorization': api_key,
                'Content-Type': 'application/json',
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.Timeout:
        raise RouteServiceError("Route calculation timed out. Please try again.")
    except requests.exceptions.ConnectionError:
        raise RouteServiceError("Could not connect to routing service.")
    except requests.exceptions.HTTPError as e:
        if e.response is not None:
            try:
                err_data = e.response.json()
                msg = err_data.get('error', {}).get('message', str(e))
            except Exception:
                msg = str(e)
            # Make the ORS distance-limit error more user-friendly
            if 'exceed' in msg.lower() and 'distance' in msg.lower():
                raise RouteServiceError(
                    "Route too long: the total trip distance exceeds the "
                    f"routing service limit of ~{_ORS_MAX_ROUTE_MILES:,} miles. "
                    "Please choose locations closer together."
                )
            raise RouteServiceError(f"Routing error: {msg}")
        raise RouteServiceError(f"Routing error: {e}")

    routes = data.get('routes', [])
    if not routes:
        raise RouteServiceError("No route found between the given locations.")

    route = routes[0]

    # Decode the geometry (encoded polyline)
    full_polyline = _decode_polyline(route.get('geometry', ''))

    # Process segments
    segments = []
    ors_segments = route.get('segments', [])

    segment_names = [
        {'from': origin, 'to': pickup, 'type': 'to_pickup'},
        {'from': pickup, 'to': dropoff, 'type': 'to_dropoff'},
    ]

    for i, ors_seg in enumerate(ors_segments):
        seg_info = segment_names[i] if i < len(segment_names) else {
            'from': {'display_name': 'Unknown'},
            'to': {'display_name': 'Unknown'},
            'type': 'unknown',
        }

        # Extract instructions
        instructions = []
        for step in ors_seg.get('steps', []):
            instructions.append({
                'text': step.get('instruction', ''),
                'distance_miles': round(step.get('distance', 0) * METERS_TO_MILES, 1),
                'duration_min': round(step.get('duration', 0) / 60, 1),
            })

        distance_miles = round(ors_seg.get('distance', 0) * METERS_TO_MILES, 1)
        duration_hours = round(ors_seg.get('duration', 0) * SECONDS_TO_HOURS, 2)

        segments.append({
            'from_name': seg_info['from']['display_name'],
            'to_name': seg_info['to']['display_name'],
            'from_coords': [seg_info['from']['lat'], seg_info['from']['lng']],
            'to_coords': [seg_info['to']['lat'], seg_info['to']['lng']],
            'distance_miles': distance_miles,
            'duration_hours': duration_hours,
            'type': seg_info['type'],
            'instructions': instructions,
        })

    total_distance = sum(s['distance_miles'] for s in segments)
    total_duration = sum(s['duration_hours'] for s in segments)

    waypoints = [
        {'name': origin['display_name'], 'lat': origin['lat'], 'lng': origin['lng'], 'type': 'origin'},
        {'name': pickup['display_name'], 'lat': pickup['lat'], 'lng': pickup['lng'], 'type': 'pickup'},
        {'name': dropoff['display_name'], 'lat': dropoff['lat'], 'lng': dropoff['lng'], 'type': 'dropoff'},
    ]

    return {
        'segments': segments,
        'total_distance_miles': round(total_distance, 1),
        'total_duration_hours': round(total_duration, 2),
        'full_polyline': full_polyline,
        'waypoints': waypoints,
    }


def _decode_polyline(encoded: str) -> list:
    """
    Decode a Google-encoded polyline string to a list of [lat, lng] pairs.

    This is the standard polyline encoding algorithm used by Google Maps
    and OpenRouteService.
    """
    if not encoded:
        return []

    decoded = []
    index = 0
    lat = 0
    lng = 0

    while index < len(encoded):
        # Decode latitude
        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        lat += (~(result >> 1) if (result & 1) else (result >> 1))

        # Decode longitude
        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        lng += (~(result >> 1) if (result & 1) else (result >> 1))

        decoded.append([lat / 1e5, lng / 1e5])

    return decoded


def interpolate_point_on_polyline(polyline: list, fraction: float) -> list:
    """
    Find the GPS coordinates at a given fraction (0.0 to 1.0) along a polyline.

    Used to determine intermediate stop locations along the route.

    Args:
        polyline: List of [lat, lng] points
        fraction: 0.0 = start, 1.0 = end

    Returns:
        [lat, lng] at the given fraction
    """
    if not polyline:
        return [0.0, 0.0]

    if fraction <= 0:
        return polyline[0]
    if fraction >= 1:
        return polyline[-1]

    # Calculate total distance
    total_dist = 0
    segment_dists = []
    for i in range(len(polyline) - 1):
        d = _haversine_distance(polyline[i], polyline[i + 1])
        segment_dists.append(d)
        total_dist += d

    if total_dist == 0:
        return polyline[0]

    target_dist = fraction * total_dist
    accumulated = 0

    for i, seg_dist in enumerate(segment_dists):
        if accumulated + seg_dist >= target_dist:
            # Interpolate within this segment
            remaining = target_dist - accumulated
            seg_fraction = remaining / seg_dist if seg_dist > 0 else 0
            lat = polyline[i][0] + seg_fraction * (polyline[i + 1][0] - polyline[i][0])
            lng = polyline[i][1] + seg_fraction * (polyline[i + 1][1] - polyline[i][1])
            return [round(lat, 6), round(lng, 6)]
        accumulated += seg_dist

    return polyline[-1]


def _haversine_distance(point1: list, point2: list) -> float:
    """Calculate distance between two [lat, lng] points in miles."""
    import math
    R = 3959  # Earth's radius in miles

    lat1, lng1 = math.radians(point1[0]), math.radians(point1[1])
    lat2, lng2 = math.radians(point2[0]), math.radians(point2[1])

    dlat = lat2 - lat1
    dlng = lng2 - lng1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c
