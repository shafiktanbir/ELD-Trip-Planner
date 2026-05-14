"""
Custom utilities for the trips app.
"""
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler that returns errors in a consistent format:
    {"error": "message", "details": {...}}
    """
    response = exception_handler(exc, context)

    if response is not None:
        custom_data = {
            'error': str(exc.detail) if hasattr(exc, 'detail') else str(exc),
            'details': response.data if isinstance(response.data, dict) else {'messages': response.data}
        }
        response.data = custom_data

    return response
