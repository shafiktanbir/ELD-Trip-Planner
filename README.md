# 🚛 ELD Trip Planner

A full-stack application that calculates HOS-compliant trucking routes and generates ELD (Electronic Logging Device) daily log sheets.

## Overview

Input a trip's **current location**, **pickup location**, **dropoff location**, and **current cycle hours used** — the app outputs:

- 🗺️ **Interactive map** showing the route with stops, rest breaks, and fuel stops
- 📋 **Daily ELD log sheets** drawn on the official FMCSA grid format
- ⏱️ **Trip summary** with driving time, rest periods, and compliance info

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Django 5 + Django REST Framework |
| **Frontend** | React 18 + Vite |
| **Maps** | React-Leaflet + OpenStreetMap |
| **Routing** | OpenRouteService API |
| **ELD Logs** | HTML5 Canvas |

## Getting Started

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py runserver
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## FMCSA HOS Rules Implemented

- **11-Hour Driving Limit** — max 11 hours driving after 10 consecutive hours off duty
- **14-Hour Window** — no driving past the 14th hour after coming on duty
- **30-Minute Break** — required after 8 hours of cumulative driving
- **10-Hour Off-Duty** — 10 consecutive hours off duty before new shift
- **70-Hour/8-Day Limit** — no driving after 70 hours on duty in 8 consecutive days
- **Fueling** — at least once every 1,000 miles
- **1 Hour Pickup/Dropoff** — on-duty not driving

## License

Assessment project — not for redistribution.
