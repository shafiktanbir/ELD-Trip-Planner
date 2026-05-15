"""
Views for the trips app.
"""
import logging
from datetime import datetime

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import TripInputSerializer
from .services.route_service import geocode_location, get_route, RouteServiceError
from .services.hos_engine import calculate_schedule, HoSEngineError
from .services.eld_generator import generate_daily_logs

logger = logging.getLogger(__name__)


class PlanTripView(APIView):
    """
    POST /api/v1/trips/plan/

    Accepts trip details and returns:
    - Route information with polyline for map display
    - HOS-compliant driving schedule with all stops
    - Daily ELD log sheets for each day of the trip
    """

    def post(self, request):
        serializer = TripInputSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    'error': 'Invalid input',
                    'details': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        try:
            # Step 1: Geocode all locations
            current = geocode_location(data['current_location'])
            pickup = geocode_location(data['pickup_location'])
            dropoff = geocode_location(data['dropoff_location'])

            # Validate that pickup and dropoff are not the same
            if (abs(pickup['lat'] - dropoff['lat']) < 0.001 and
                    abs(pickup['lng'] - dropoff['lng']) < 0.001):
                return Response(
                    {
                        'error': 'Pickup and dropoff locations are the same.',
                        'details': {
                            'pickup': pickup['display_name'],
                            'dropoff': dropoff['display_name'],
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Step 2: Get route
            route_data = get_route(current, pickup, dropoff)

            # Step 3: Calculate HOS-compliant schedule
            # Use provided start_time or default to now (strip timezone for naive datetime)
            start_time = data.get('start_time')
            if start_time is not None:
                # Make timezone-naive for the HOS engine
                start_time = start_time.replace(tzinfo=None).replace(second=0, microsecond=0)

            schedule_data = calculate_schedule(
                route_data=route_data,
                current_cycle_used=data['current_cycle_hours'],
                start_time=start_time,  # None → engine defaults to now
            )

            # Step 4: Generate daily ELD logs
            daily_logs = generate_daily_logs(schedule_data)

            # Build response
            return Response({
                'route': {
                    'segments': route_data['segments'],
                    'total_distance_miles': route_data['total_distance_miles'],
                    'total_duration_hours': route_data['total_duration_hours'],
                    'polyline': route_data['full_polyline'],
                    'waypoints': route_data['waypoints'],
                },
                'schedule': schedule_data['schedule'],
                'stops': schedule_data['stops'],
                'summary': schedule_data['summary'],
                'daily_logs': daily_logs,
                'locations': {
                    'current': current,
                    'pickup': pickup,
                    'dropoff': dropoff,
                },
            })

        except RouteServiceError as e:
            logger.error(f"Route service error: {e}")
            return Response(
                {'error': str(e), 'details': {}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except HoSEngineError as e:
            logger.error(f"HOS engine error: {e}")
            return Response(
                {'error': str(e), 'details': {}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return Response(
                {'error': 'An unexpected error occurred. Please try again.', 'details': {}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
