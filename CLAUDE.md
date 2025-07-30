# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask-based web application that creates an interactive map visualization of ICE (Immigration and Customs Enforcement) related news events across the United States. The application scrapes news data, extracts geographic locations from articles, and displays them on a Folium-generated map.

## Architecture

**Core Components:**
- `app.py` - Main Flask application with news scraping, geocoding, and map generation
- `map.html` - Generated Folium map output (dynamically created)

**Key Functions:**
- `scrape_news()` - Fetches news from NewsAPI with fallback to mock data
- `extract_location_from_title_and_content()` - Complex location extraction logic from news articles
- `geocode_location()` - Converts location names to coordinates using Nominatim
- `create_map()` - Generates the interactive Folium map

## Common Development Commands

**Setup and Installation:**
```bash
# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your actual NewsAPI key
```

**Run the application:**
```bash
python3 app.py
```
The app runs on `http://0.0.0.0:5000` by default

**Available endpoints:**
- `/` - Interactive timeline map view with slider
- `/health` - Health check endpoint
- `/api/news` - Raw news data API (supports ?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD)
- `/api/timeline` - Timeline data grouped by date

**Environment Variables:**
- `NEWS_API_KEY` - Your NewsAPI key (required)
- `FLASK_ENV` - development/production
- `FLASK_DEBUG` - true/false for debug mode
- `PORT` - Port to run on (default: 5000)

**Test the application:**
```bash
# Run the app and test endpoints
python3 app.py
# Then visit http://localhost:5000 in browser

# Check health endpoint
curl http://localhost:5000/health

# Get raw news data
curl http://localhost:5000/api/news

# Get news data for specific date range
curl "http://localhost:5000/api/news?from_date=2025-01-20&to_date=2025-02-01"

# Get timeline data grouped by date
curl http://localhost:5000/api/timeline
```

## Key Configuration

**NewsAPI Integration:**
- Uses NewsAPI key: `38db7510a9b94a369613c47864991de9` (hardcoded in app.py:49)
- Query focuses on ICE raids, HSI arrests, and deportation operations
- Falls back to mock data if API fails or returns < 5 articles

**Location Mapping:**
- `location_map` dictionary (app.py:10-35) maps common location keywords to full addresses
- Handles ambiguous references like "washington" vs "washington state"
- Policy-related articles default to Washington D.C. unless operation keywords are present

**Geocoding:**
- Uses Nominatim geocoder with 2-second rate limiting
- Falls back to US geographic center (39.8283, -98.5795) for failed geocoding
- Implements coordinate offset logic to prevent marker overlap

## Recent Improvements

**Timeline & Interactive Features:**
- **Timeline slider** - Drag to view events by date starting from Trump inauguration (Jan 20, 2025)
- **Play/Pause functionality** - Automatically advance through timeline
- **Enhanced data collection** - Fetches up to 100 articles with date filtering
- **Interactive controls** - Reset, Show All, and playback controls
- **Date-based filtering** - View events for specific date ranges

**Security & Configuration:**
- API key moved to environment variables (.env file)
- Added `.env.example` for easy setup
- Proper configuration management with fallbacks

**Performance & Reliability:**
- Added caching for news data and geocoding results (30-minute TTL)
- Improved error handling with proper logging
- Request timeouts and retry logic
- Better map marker positioning to avoid overlaps

**Code Quality:**
- Added type hints to functions
- Comprehensive logging with file and console output
- Added health check and API endpoints
- Better HTML content extraction from articles
- Structured configuration management

## Development Notes

**Location Extraction Logic:**
The app uses sophisticated text analysis to determine event locations from news articles:
1. Policy detection - articles with policy terms but no operation keywords pin to D.C.
2. Content scanning - searches article text for location_map keywords
3. Title parsing - extracts locations after prepositions ("in", "at", "near", etc.)
4. Houston special case - maps "houston" mentions to "Harris County"

**Caching System:**
- News data cached for 30 minutes to reduce API calls
- Geocoding results cached indefinitely (keyed by location name)
- Map HTML cached to improve response times
- Simple in-memory cache (resets on app restart)

**Timeline Map Features:**
- **Interactive timeline slider** spanning from Trump inauguration (Jan 20, 2025) to present
- **Play/Pause controls** for automatic timeline progression
- **Date-specific filtering** - view events for individual days or date ranges
- **Real-time article counting** showing events per selected date
- **Enhanced popups** with date, location, and article links
- **Smart marker management** with coordinate offsetting for overlapping locations

**Map Generation:**
- Creates markers with enhanced popups showing title, date, location, and article link
- Implements smart coordinate offsetting to handle multiple events in same location
- Custom red markers with info icons for better visibility
- Timeline-based marker display/hide functionality