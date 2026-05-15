"""
Integration tests for the trip planning API endpoint.

Tests cover:
- Input validation (bad data → 400)
- Correct response shape when ORS is mocked
- Error handling for geocoding / routing failures
"""
from unittest.mock import patch, MagicMock
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status


MOCK_GEOCODE_CURRENT = {
    "lat": 40.7128,
    "lng": -74.006,
    "display_name": "New York, NY",
}
MOCK_GEOCODE_PICKUP = {
    "lat": 39.9526,
    "lng": -75.1652,
    "display_name": "Philadelphia, PA",
}
MOCK_GEOCODE_DROPOFF = {
    "lat": 34.0522,
    "lng": -118.2437,
    "display_name": "Los Angeles, CA",
}

MOCK_ROUTE = {
    "segments": [
        {
            "type": "to_pickup",
            "from_name": "New York, NY",
            "to_name": "Philadelphia, PA",
            "from_coords": [40.7128, -74.006],
            "to_coords": [39.9526, -75.1652],
            "distance_miles": 95.0,
            "duration_hours": 1.6,
            "instructions": [],
        },
        {
            "type": "to_dropoff",
            "from_name": "Philadelphia, PA",
            "to_name": "Los Angeles, CA",
            "from_coords": [39.9526, -75.1652],
            "to_coords": [34.0522, -118.2437],
            "distance_miles": 2740.0,
            "duration_hours": 41.0,
            "instructions": [],
        },
    ],
    "total_distance_miles": 2835.0,
    "total_duration_hours": 42.6,
    "full_polyline": [[40.7128, -74.006], [34.0522, -118.2437]],
    "waypoints": [
        {"name": "New York, NY", "lat": 40.7128, "lng": -74.006, "type": "origin"},
        {"name": "Philadelphia, PA", "lat": 39.9526, "lng": -75.1652, "type": "pickup"},
        {"name": "Los Angeles, CA", "lat": 34.0522, "lng": -118.2437, "type": "dropoff"},
    ],
}


class TestPlanTripAPIValidation(TestCase):
    """Validate input validation on POST /api/v1/trips/plan/."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/trips/plan/"

    def test_missing_all_fields_returns_400(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", resp.data)

    def test_missing_current_location_returns_400(self):
        resp = self.client.post(
            self.url,
            {
                "pickup_location": "Philadelphia, PA",
                "dropoff_location": "Los Angeles, CA",
                "current_cycle_hours": 0,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cycle_hours_above_70_returns_400(self):
        resp = self.client.post(
            self.url,
            {
                "current_location": "New York, NY",
                "pickup_location": "Philadelphia, PA",
                "dropoff_location": "Los Angeles, CA",
                "current_cycle_hours": 75,  # exceeds max
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cycle_hours_below_0_returns_400(self):
        resp = self.client.post(
            self.url,
            {
                "current_location": "New York, NY",
                "pickup_location": "Philadelphia, PA",
                "dropoff_location": "Los Angeles, CA",
                "current_cycle_hours": -5,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_numeric_cycle_hours_returns_400(self):
        resp = self.client.post(
            self.url,
            {
                "current_location": "New York, NY",
                "pickup_location": "Philadelphia, PA",
                "dropoff_location": "Los Angeles, CA",
                "current_cycle_hours": "not-a-number",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class TestPlanTripAPISuccess(TestCase):
    """Validate correct response structure when all dependencies are mocked."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/trips/plan/"

    @patch("trips.views.get_route", return_value=MOCK_ROUTE)
    @patch("trips.views.geocode_location")
    def test_successful_plan_returns_200(self, mock_geocode, mock_route):
        mock_geocode.side_effect = [
            MOCK_GEOCODE_CURRENT,
            MOCK_GEOCODE_PICKUP,
            MOCK_GEOCODE_DROPOFF,
        ]

        resp = self.client.post(
            self.url,
            {
                "current_location": "New York, NY",
                "pickup_location": "Philadelphia, PA",
                "dropoff_location": "Los Angeles, CA",
                "current_cycle_hours": 0,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    @patch("trips.views.get_route", return_value=MOCK_ROUTE)
    @patch("trips.views.geocode_location")
    def test_response_has_required_top_level_keys(self, mock_geocode, mock_route):
        mock_geocode.side_effect = [
            MOCK_GEOCODE_CURRENT,
            MOCK_GEOCODE_PICKUP,
            MOCK_GEOCODE_DROPOFF,
        ]

        resp = self.client.post(
            self.url,
            {
                "current_location": "New York, NY",
                "pickup_location": "Philadelphia, PA",
                "dropoff_location": "Los Angeles, CA",
                "current_cycle_hours": 0,
            },
            format="json",
        )

        for key in ("route", "schedule", "stops", "summary", "daily_logs", "locations"):
            self.assertIn(key, resp.data, f"Response missing key: {key}")

    @patch("trips.views.get_route", return_value=MOCK_ROUTE)
    @patch("trips.views.geocode_location")
    def test_daily_logs_are_generated(self, mock_geocode, mock_route):
        mock_geocode.side_effect = [
            MOCK_GEOCODE_CURRENT,
            MOCK_GEOCODE_PICKUP,
            MOCK_GEOCODE_DROPOFF,
        ]

        resp = self.client.post(
            self.url,
            {
                "current_location": "New York, NY",
                "pickup_location": "Philadelphia, PA",
                "dropoff_location": "Los Angeles, CA",
                "current_cycle_hours": 0,
            },
            format="json",
        )

        self.assertIsInstance(resp.data["daily_logs"], list)
        self.assertGreater(len(resp.data["daily_logs"]), 0)

    @patch("trips.views.get_route", return_value=MOCK_ROUTE)
    @patch("trips.views.geocode_location")
    def test_summary_contains_expected_fields(self, mock_geocode, mock_route):
        mock_geocode.side_effect = [
            MOCK_GEOCODE_CURRENT,
            MOCK_GEOCODE_PICKUP,
            MOCK_GEOCODE_DROPOFF,
        ]

        resp = self.client.post(
            self.url,
            {
                "current_location": "New York, NY",
                "pickup_location": "Philadelphia, PA",
                "dropoff_location": "Los Angeles, CA",
                "current_cycle_hours": 10,
            },
            format="json",
        )

        summary = resp.data["summary"]
        for field in (
            "total_driving_hours",
            "total_on_duty_hours",
            "total_off_duty_hours",
            "total_trip_hours",
            "total_miles",
            "num_fuel_stops",
            "num_rest_stops",
        ):
            self.assertIn(field, summary, f"Summary missing: {field}")


class TestPlanTripAPIErrors(TestCase):
    """Validate that external-service failures return appropriate 4xx/5xx codes."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/trips/plan/"

    @patch("trips.views.geocode_location")
    def test_geocoding_failure_returns_422(self, mock_geocode):
        from trips.services.route_service import RouteServiceError
        mock_geocode.side_effect = RouteServiceError("Location not found")

        resp = self.client.post(
            self.url,
            {
                "current_location": "Nonexistent Place XYZ",
                "pickup_location": "Philadelphia, PA",
                "dropoff_location": "Los Angeles, CA",
                "current_cycle_hours": 0,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("error", resp.data)

    @patch("trips.views.get_route")
    @patch("trips.views.geocode_location")
    def test_same_pickup_and_dropoff_returns_400(self, mock_geocode, mock_route):
        """Pickup and dropoff at the same coordinates must be rejected."""
        same_location = {
            "lat": 39.9526,
            "lng": -75.1652,
            "display_name": "Philadelphia, PA",
        }
        mock_geocode.side_effect = [MOCK_GEOCODE_CURRENT, same_location, same_location]

        resp = self.client.post(
            self.url,
            {
                "current_location": "New York, NY",
                "pickup_location": "Philadelphia, PA",
                "dropoff_location": "Philadelphia, PA",
                "current_cycle_hours": 0,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
