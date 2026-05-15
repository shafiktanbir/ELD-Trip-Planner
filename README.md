loom video = https://www.loom.com/share/a3ca0e693e08466bb30111514fce3ccf
frontend_url=https://eld-trip-planner-green.vercel.app/

# 🚛 ELD Trip Planner

> **Full-Stack Assessment Project** — Django + React  
> Build an app that takes trip details as inputs and outputs route instructions with ELD log sheets drawn on the official FMCSA grid format.

[![Django](https://img.shields.io/badge/Django-5.x-092E20?logo=django)](https://djangoproject.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite)](https://vitejs.dev)

---

## 📺 Demo

> 🎥 **[Loom walkthrough — coming soon](#)**  
> 🌐 **[Live hosted app — coming soon](#)**

---

## Overview

Input a trip's **current location**, **pickup location**, **dropoff location**, and **current cycle hours used** — the app outputs:

- 🗺️ **Interactive map** showing the route with all stop markers (fuel, rest, breaks, pickup, dropoff)
- 📋 **Daily ELD log sheets** drawn on the official FMCSA grid format (Canvas-based, 4-row / 24-hour grid, 15-min subdivisions)
- ⏱️ **Trip summary** with driving hours, rest periods, stop counts, and cycle balance
- 🖨️ **Print-ready** ELD log sheets (click "Print Logs" to print all sheets)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Django 5 + Django REST Framework |
| **Frontend** | React 18 + Vite 5 |
| **Maps** | Leaflet.js + CARTO dark tiles |
| **Routing / Geocoding** | OpenRouteService API (free tier, `driving-hgv` profile) |
| **ELD Log Canvas** | HTML5 Canvas (HiDPI support) |
| **Task Runner** | Taskfile (https://taskfile.dev) |

---

## FMCSA HOS Rules Implemented

| Rule | Description |
|------|-------------|
| **HOS-1** | 11-hour driving limit per shift |
| **HOS-2** | 14-hour driving window from first on-duty |
| **HOS-3** | 30-minute mandatory break after 8 hours cumulative driving |
| **HOS-4** | 10 consecutive hours off-duty to reset the shift |
| **HOS-5** | 70-hour / 8-day cycle (Property-Carrying, no adverse conditions) |
| **HOS-6** | Fuel stop at least every 1,000 miles |
| **HOS-7** | 1-hour pickup (On-Duty Not Driving) |
| **HOS-8** | 1-hour dropoff (On-Duty Not Driving) |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- An [OpenRouteService API key](https://openrouteservice.org/dev/#/signup) (free)

### Option A: Taskfile (recommended)

```bash
# Install Taskfile if needed
sh -c "$(curl -fsSL https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin

# Install all dependencies
task install

# Start backend + frontend (in two terminals)
task dev:backend     # Terminal 1 → http://localhost:8000
task dev:frontend    # Terminal 2 → http://localhost:5173

# Run tests
task test

# Check syntax
task lint
```

### Option B: Manual

**1. Backend setup**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

**2. Configure your ORS API key**

Edit `backend/.env`:
```
ORS_API_KEY=your-key-here
```

**3. Frontend setup**
```bash
cd frontend
npm install
npm run dev
```

Open → `http://localhost:5173`

---

## Running Tests

```bash
# Using Taskfile
task test

# Or directly
cd backend
source venv/bin/activate
python manage.py test trips.tests --verbosity=2
```

Tests cover:
- ✅ HOS engine input validation (negative hours, cycle overflow, empty routes)
- ✅ 30-minute break rule (HOS-3)
- ✅ 11-hour driving / 14-hour window limits (HOS-1, HOS-2)
- ✅ 1,000-mile fueling rule (HOS-6)
- ✅ 70-hr/8-day cycle restart (HOS-5)
- ✅ Schedule chronological ordering
- ✅ ELD log 24-hour coverage
- ✅ API validation (missing fields, bad cycle hours, same pickup/dropoff)
- ✅ API error handling (geocoding failure, routing failure)

---

## Deployment

### Backend (Railway / Render / Heroku)

1. Set environment variables:
   ```
   DJANGO_SECRET_KEY=<generate-a-strong-key>
   ORS_API_KEY=<your-key>
   DEBUG=False
   ALLOWED_HOSTS=yourdomain.com
   CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
   ```
2. Install dependencies: `pip install -r requirements.txt`
3. Run migrations: `python manage.py migrate`
4. Serve with gunicorn: `gunicorn config.wsgi:application`

### Frontend (Vercel)

1. Set `VITE_API_BASE_URL` environment variable to your backend URL in Vercel project settings
2. Build command: `npm run build`
3. Output directory: `dist`

---

## Project Structure

```
ena/
├── backend/
│   ├── config/               # Django settings, URLs, WSGI
│   ├── trips/
│   │   ├── services/
│   │   │   ├── route_service.py   # ORS geocoding + HGV routing + polyline decode
│   │   │   ├── hos_engine.py      # Full FMCSA HOS compliance engine
│   │   │   └── eld_generator.py   # Daily log sheet data (midnight boundary split)
│   │   ├── tests/
│   │   │   ├── test_hos_engine.py # HOS engine unit tests (all 8 HOS rules)
│   │   │   └── test_api.py        # API integration tests (mocked)
│   │   ├── views.py               # PlanTripView — orchestrates all services
│   │   ├── serializers.py         # Input validation
│   │   └── urls.py
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── TripForm/          # Location + cycle hours input form
│   │   │   ├── MapView/           # Leaflet map with route + stop markers
│   │   │   ├── ELDLogSheet/       # Canvas FMCSA log grid (4 rows × 24h)
│   │   │   ├── TripSummary/       # Stats panel (driving, rest, stops, cycle)
│   │   │   ├── Toast/             # Success / error toast notifications
│   │   │   └── Layout/            # Header shell
│   │   ├── services/api.js        # Axios API wrapper
│   │   ├── index.css              # Design system tokens (dark glassmorphism)
│   │   └── App.jsx                # Main orchestrator + state
│   ├── package.json
│   └── vite.config.js
├── Taskfile.yml                   # Task runner (install, dev, test, build, lint)
└── README.md
```

---

## License

Assessment project — not for redistribution.
