"""
Serializers for trip planning input/output.
"""
from rest_framework import serializers


class LocationSerializer(serializers.Serializer):
    """Represents a location with address and optional coordinates."""
    address = serializers.CharField(
        max_length=500,
        help_text="Full address or city name"
    )
    lat = serializers.FloatField(
        required=False,
        help_text="Latitude (optional — geocoded if not provided)"
    )
    lng = serializers.FloatField(
        required=False,
        help_text="Longitude (optional — geocoded if not provided)"
    )


class TripInputSerializer(serializers.Serializer):
    """
    Input data for trip planning.

    Accepts current location, pickup, dropoff, and current cycle hours used.
    """
    current_location = serializers.CharField(
        max_length=500,
        help_text="Current location address or 'lat,lng'"
    )
    pickup_location = serializers.CharField(
        max_length=500,
        help_text="Pickup location address or 'lat,lng'"
    )
    dropoff_location = serializers.CharField(
        max_length=500,
        help_text="Dropoff location address or 'lat,lng'"
    )
    current_cycle_hours = serializers.FloatField(
        min_value=0,
        max_value=70,
        help_text="Hours already used in the current 70-hour/8-day cycle"
    )
