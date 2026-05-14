"""
URL routing for the trips app.
"""
from django.urls import path
from . import views

app_name = 'trips'

urlpatterns = [
    path('plan/', views.PlanTripView.as_view(), name='plan-trip'),
]
