from flask import Flask, send_file
import requests
import folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from bs4 import BeautifulSoup
import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
CONFIG = {
    'NEWS_API_KEY': os.getenv('NEWS_API_KEY', '38db7510a9b94a369613c47864991de9'),
    'REQUEST_TIMEOUT': 10,
    'MAX_ARTICLES': 100,  # Increased for timeline
    'CACHE_DURATION_MINUTES': 30,
    'RATE_LIMIT_DELAY': 2,
    'TRUMP_INAUGURATION': '2025-01-20',  # Timeline start date
    'ARTICLES_PER_PAGE': 100
}

# Simple in-memory cache
# Clear all cache to force fresh real data
cache = {}

location_map = {
    # Specific cities (most reliable)
    "liberty": "Liberty, MO",
    "colony ridge": "Cleveland, TX",
    "houston": "Houston, TX",
    "harris county": "Harris County, TX",
    "rochester": "Rochester, MN",
    "denver": "Denver, CO",
    "aurora": "Aurora, CO",
    "washington": "Washington, D.C.",
    "white house": "Washington, D.C.",
    "laredo": "Laredo, TX",
    "dallas": "Dallas, TX",
    "hyattsville": "Hyattsville, MD",
    "new bedford": "New Bedford, MA",
    "apache junction": "Apache Junction, AZ",
    "auburn": "Auburn, CA",
    "san diego": "San Diego, CA",
    "los angeles": "Los Angeles, CA",
    "san jose": "San Jose, CA",
    "san francisco": "San Francisco, CA",
    # Major cities for ICE operations
    "new york": "New York, NY",
    "brooklyn": "Brooklyn, NY",
    "queens": "Queens, NY",
    "bronx": "Bronx, NY",
    "manhattan": "Manhattan, NY",
    "chicago": "Chicago, IL",
    "philadelphia": "Philadelphia, PA",
    "phoenix": "Phoenix, AZ",
    "atlanta": "Atlanta, GA",
    "miami": "Miami, FL",
    "orlando": "Orlando, FL",
    "tampa": "Tampa, FL",
    "jacksonville": "Jacksonville, FL",
    "las vegas": "Las Vegas, NV",
    "seattle": "Seattle, WA",
    "portland": "Portland, OR",
    "baltimore": "Baltimore, MD",
    "boston": "Boston, MA",
    "detroit": "Detroit, MI",
    "minneapolis": "Minneapolis, MN",
    "kansas city": "Kansas City, MO",
    "st. louis": "St. Louis, MO",
    "oklahoma city": "Oklahoma City, OK",
    "tulsa": "Tulsa, OK",
    "nashville": "Nashville, TN",
    "memphis": "Memphis, TN",
    "charlotte": "Charlotte, NC",
    "raleigh": "Raleigh, NC",
    "richmond": "Richmond, VA",
    "norfolk": "Norfolk, VA",
    "salt lake city": "Salt Lake City, UT",
    "albuquerque": "Albuquerque, NM",
    "el paso": "El Paso, TX",
    "san antonio": "San Antonio, TX",
    "austin": "Austin, TX",
    "fort worth": "Fort Worth, TX",
    # Border areas
    "mcallen": "McAllen, TX",
    "brownsville": "Brownsville, TX",
    "nogales": "Nogales, AZ",
    "tucson": "Tucson, AZ",
    "yuma": "Yuma, AZ",
    "san ysidro": "San Ysidro, CA",
    "calexico": "Calexico, CA",
    # Short codes (less reliable, but common)
    "la": "Los Angeles, CA",
    "nyc": "New York, NY",
    "dc": "Washington, D.C.",
    # States (fallback)
    "washington state": "Seattle, WA",
    "california": "Los Angeles, CA",
    "texas": "Houston, TX",
    "florida": "Miami, FL",
    "missouri": "Kansas City, MO",
    "illinois": "Chicago, IL",
    "new york state": "New York, NY",
    "arizona": "Phoenix, AZ"
}

def fetch_article_content(url: str) -> str:
    """Fetch and extract text content from a news article URL."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; ICE-GIS-App/1.0)"}
        response = requests.get(
            url, 
            headers=headers, 
            timeout=CONFIG['REQUEST_TIMEOUT'],
            allow_redirects=True
        )
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text(separator=" ", strip=True)
        logger.info(f"Successfully fetched content from {url}")
        return text.lower()
    except requests.exceptions.RequestException as e:
        logger.warning(f"Request error fetching {url}: {e}")
        return ""
    except Exception as e:
        logger.error(f"Unexpected error fetching {url}: {e}")
        return ""

def scrape_news(from_date: str = None, to_date: str = None) -> list:
    """Scrape REAL news articles from NewsAPI only - no fake data."""
    # Create cache key based on date range
    cache_key = f"news_data_{from_date}_{to_date}"
    
    # Check cache first
    if (cache.get(cache_key) and cache.get(f'{cache_key}_updated') and 
        datetime.now() - cache[f'{cache_key}_updated'] < timedelta(minutes=CONFIG['CACHE_DURATION_MINUTES'])):
        logger.info(f"Returning cached news data for {from_date} to {to_date}")
        return cache[cache_key]
    
    api_key = CONFIG['NEWS_API_KEY']
    all_articles = []
    
    # More targeted search queries for immigration enforcement
    queries = [
        "ICE raids OR ICE arrests",
        "immigration enforcement", 
        "border patrol arrests",
        "ICE detention OR ICE operation",
        "deportation raids",
        "HSI arrests OR homeland security",
        "CBP arrests OR customs border"
    ]
    
    for query in queries:
        try:
            # Build URL - get more articles per query
            url = f"https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=100&apiKey={api_key}"
            
            if from_date:
                url += f"&from={from_date}"
            if to_date:
                url += f"&to={to_date}"
            
            logger.info(f"Searching NewsAPI with query: '{query}'")
            response = requests.get(url, timeout=CONFIG['REQUEST_TIMEOUT'])
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") == "error":
                logger.error(f"NewsAPI error: {data.get('message')}")
                continue
                
            articles = data.get("articles", [])
            logger.info(f"Found {len(articles)} articles for query '{query}'")
            
            for article in articles:
                # Skip if missing essential data
                if not all([article.get("title"), article.get("url"), article.get("publishedAt")]):
                    continue
                
                # Skip duplicates
                if any(existing["url"] == article["url"] for existing in all_articles):
                    continue
                
                # Parse publication date
                try:
                    published_at = article["publishedAt"]
                    if 'T' in published_at:
                        dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    else:
                        dt = datetime.strptime(published_at[:10], '%Y-%m-%d')
                    formatted_date = dt.strftime('%Y-%m-%d')
                except Exception as e:
                    logger.debug(f"Date parsing error: {e}")
                    continue  # Skip articles with bad dates
                
                # Filter by date range
                if from_date and formatted_date < from_date:
                    continue
                if to_date and formatted_date > to_date:
                    continue
                
                # Only include articles that seem relevant to immigration enforcement
                title_lower = article["title"].lower()
                description_lower = (article.get("description") or "").lower()
                
                # Check if article is actually about immigration enforcement
                relevant_terms = [
                    "ice", "immigration", "border", "deportation", "detention", 
                    "enforcement", "raid", "arrest", "cbp", "hsi", "customs",
                    "undocumented", "illegal", "asylum", "refugee"
                ]
                
                if not any(term in title_lower or term in description_lower for term in relevant_terms):
                    continue
                
                all_articles.append({
                    "title": article["title"],
                    "url": article["url"],
                    "location": None,  # Will be extracted later
                    "published_at": published_at,
                    "date": formatted_date,
                    "description": article.get("description", "")[:300] + "..." if article.get("description") else "",
                    "source": article.get("source", {}).get("name", "Unknown"),
                    "content": article.get("content", "")  # Sometimes has more text
                })
            
            # Rate limiting
            import time
            time.sleep(0.3)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error for query '{query}': {e}")
            continue
        except Exception as e:
            logger.error(f"Error processing query '{query}': {e}")
            continue
    
    # Remove duplicates and sort by date
    unique_articles = []
    seen_urls = set()
    
    for article in all_articles:
        if article["url"] not in seen_urls:
            unique_articles.append(article)
            seen_urls.add(article["url"])
    
    # Sort by date (newest first)
    unique_articles.sort(key=lambda x: x['date'], reverse=True)
    
    logger.info(f"Successfully retrieved {len(unique_articles)} unique real articles from NewsAPI")
    
    # Update cache
    cache[cache_key] = unique_articles
    cache[f'{cache_key}_updated'] = datetime.now()
    
    return unique_articles

def create_error_map_html(error_message: str) -> str:
    """Create a simple error map when no real articles are found."""
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>ICE Operations Timeline - Error</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 50px; text-align: center; }}
        .error {{ color: red; font-size: 18px; }}
        .message {{ margin-top: 20px; }}
    </style>
</head>
<body>
    <h1>ICE Operations Timeline Map</h1>
    <div class="error">Error: {error_message}</div>
    <div class="message">
        <p>The app is configured to use only real news articles from NewsAPI.</p>
        <p>Please check your NewsAPI configuration and try again.</p>
        <p>No fake or fallback data will be displayed.</p>
    </div>
</body>
</html>
    """
    return html

# NO FALLBACK DATA - Use only real articles from NewsAPI

def geocode_location(location_name: str) -> list:
    """Geocode a location name to coordinates with caching and fallback."""
    # Create cache key
    cache_key = f"geocode_{location_name.lower()}"
    
    # Check if we have cached coordinates
    if cache_key in cache:
        logger.debug(f"Using cached coordinates for {location_name}")
        return cache[cache_key]
    
    geolocator = Nominatim(user_agent="ice_gis_app/1.0")
    geocode = RateLimiter(
        geolocator.geocode, 
        min_delay_seconds=CONFIG['RATE_LIMIT_DELAY'], 
        max_retries=3
    )
    
    try:
        # Normalize location name using location_map
        normalized_name = location_name
        for key, value in location_map.items():
            if key in location_name.lower():
                normalized_name = value
                logger.debug(f"Normalized '{location_name}' to '{normalized_name}'")
                break
        
        # Ensure "United States" is included for better geocoding
        if "United States" not in normalized_name.lower():
            normalized_name += ", United States"
        
        location = geocode(normalized_name)
        if location:
            coords = [location.latitude, location.longitude]
            cache[cache_key] = coords  # Cache the result
            logger.info(f"Geocoded '{location_name}' to {coords}")
            return coords
        
        logger.warning(f"Geocoding failed for '{location_name}', using US center")
        fallback_coords = [39.8283, -98.5795]  # US geographic center
        cache[cache_key] = fallback_coords
        return fallback_coords
        
    except Exception as e:
        logger.error(f"Geocoding error for '{location_name}': {e}")
        fallback_coords = [39.8283, -98.5795]
        cache[cache_key] = fallback_coords
        return fallback_coords

def extract_location_from_article(article_data: dict) -> str:
    """Extract location from real article data using improved parsing and prioritization."""
    title = article_data.get("title", "")
    description = article_data.get("description", "")
    content = article_data.get("content", "")
    url = article_data.get("url", "")
    
    # Combine all text sources
    all_text = f"{title} {description} {content}".lower()
    
    logger.debug(f"Extracting location from: {title}")
    
    # First, try to get more content from the URL if needed
    if len(all_text) < 200:  # If we don't have much text, try to fetch more
        fetched_content = fetch_article_content(url)
        all_text += f" {fetched_content}"
    
    # Priority 1: Look for explicit location patterns in title first (most reliable)
    title_lower = title.lower()
    
    # Look for "in [City]" or "at [City]" patterns in the title
    import re
    location_patterns = [
        r'\b(?:in|at|near|from)\s+([A-Za-z][A-Za-z\s]+?)(?:,|\s+(?:raids?|arrests?|operations?|detention|enforcement|ICE|immigration))',
        r'\b([A-Za-z][A-Za-z\s]+?)(?:,|\s+)(?:raids?|arrests?|operations?|detention|enforcement|ICE)',
        r'\b([A-Za-z][A-Za-z\s]+?)\s+(?:ICE|immigration|enforcement|raids?|arrests?)'
    ]
    
    for pattern in location_patterns:
        matches = re.findall(pattern, title, re.IGNORECASE)
        for match in matches:
            location_candidate = match.strip().lower()
            # Check if this matches any of our known locations
            for key, full_location in location_map.items():
                if key in location_candidate or location_candidate in key:
                    logger.info(f"Found title location pattern: '{match}' -> {key}")
                    return key
                # Also check city names
                city_name = full_location.split(',')[0].lower()
                if city_name in location_candidate or location_candidate in city_name:
                    if len(location_candidate) > 3:  # Avoid very short matches
                        logger.info(f"Found title city match: '{match}' -> {key}")
                        return key
    
    # Priority 2: Look for specific location context in full text
    # Look for "City, State" patterns first (most reliable)
    state_abbrevs = r'\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\b'
    city_state_pattern = rf'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*{state_abbrevs}'
    
    matches = re.findall(city_state_pattern, all_text.title())
    for city, state in matches:
        city_lower = city.lower()
        state_lower = state.lower()
        # Look for exact matches in our location map
        for key, full_location in location_map.items():
            full_lower = full_location.lower()
            if city_lower in full_lower and state_lower in full_lower:
                logger.info(f"Found City,State pattern: {city}, {state} -> {key}")
                return key
    
    # Priority 3: Look for location keywords from our map (but be more selective)
    # First pass: exact matches and longer location names (more reliable)
    location_scores = []
    for key, full_location in location_map.items():
        score = 0
        
        # Higher score for longer, more specific matches
        if key in all_text:
            score += len(key) * 2  # Longer matches get higher priority
            
            # Bonus if found in title (more reliable)
            if key in title_lower:
                score += 10
                
            # Bonus for context words nearby
            context_words = ['raids', 'arrests', 'operation', 'detention', 'enforcement', 'ice']
            for word in context_words:
                if word in all_text and abs(all_text.find(key) - all_text.find(word)) < 50:
                    score += 2
                    
            location_scores.append((score, key, full_location))
        
        # Also check city names from full location
        location_parts = full_location.lower().split(", ")
        if len(location_parts) >= 1:
            city_name = location_parts[0]
            if city_name in all_text and len(city_name) > 4:  # Only longer city names
                city_score = len(city_name)
                if city_name in title_lower:
                    city_score += 5
                location_scores.append((city_score, key, full_location))
    
    # Return the highest scoring location
    if location_scores:
        location_scores.sort(key=lambda x: x[0], reverse=True)
        best_score, best_key, best_location = location_scores[0]
        if best_score > 3:  # Only return if we have reasonable confidence
            logger.info(f"Found best location match: '{best_key}' -> {best_location} (score: {best_score})")
            return best_key
    
    # Look for specific location patterns in the text
    import re
    
    # City, State patterns
    state_abbrevs = r'\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\b'
    city_state_pattern = rf'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*{state_abbrevs}'
    
    matches = re.findall(city_state_pattern, all_text.title())  # Use title case for proper matching
    for city, state in matches:
        city_lower = city.lower()
        # Check if this city matches our location map
        for key, value in location_map.items():
            if city_lower in key or key in city_lower:
                logger.info(f"Found location via regex: {city}, {state} -> {key}")
                return key
    
    # Look for directional indicators with cities
    direction_patterns = [
        r'\bin\s+([a-z]+(?:\s+[a-z]+)*)\b',
        r'\bnear\s+([a-z]+(?:\s+[a-z]+)*)\b',
        r'\bfrom\s+([a-z]+(?:\s+[a-z]+)*)\b',
        r'\bout(?:side)?\s+of\s+([a-z]+(?:\s+[a-z]+)*)\b'
    ]
    
    for pattern in direction_patterns:
        matches = re.findall(pattern, all_text)
        for match in matches:
            location_text = match.strip()
            # Check against our location map
            for key in location_map.keys():
                if key in location_text or location_text in key:
                    logger.info(f"Found directional location: {location_text} -> {key}")
                    return key
    
    # Look for major cities without directional indicators
    major_cities = {
        "houston": "houston", "dallas": "dallas", "chicago": "chicago", 
        "los angeles": "los angeles", "new york": "new york", "miami": "miami",
        "denver": "denver", "phoenix": "phoenix", "atlanta": "atlanta",
        "boston": "boston", "seattle": "washington state", "portland": "portland"
    }
    
    for city_name, location_key in major_cities.items():
        if city_name in all_text:
            logger.info(f"Found major city '{city_name}' -> {location_key}")
            return location_key if location_key in location_map else city_name
    
    # Look for state names
    states = {
        "texas": "dallas", "california": "los angeles", "florida": "miami", 
        "new york": "new york", "illinois": "chicago", "arizona": "phoenix",
        "colorado": "denver", "washington": "washington state",
        "missouri": "liberty", "maryland": "hyattsville"
    }
    
    for state_name, location_key in states.items():
        if state_name in all_text:
            logger.info(f"Found state '{state_name}' -> {location_key}")
            return location_key
    
    # Default fallback - return first location that makes sense
    logger.warning(f"No specific location found for: {title[:50]}...")
    return "washington"  # Default to DC for federal immigration news

def create_timeline_map() -> str:
    """Create an interactive map with timeline functionality using REAL articles only."""
    # Try different date ranges to find available articles
    to_date = datetime.now().strftime('%Y-%m-%d')
    
    # First try: Last 30 days (most likely to have data)
    from_date_30 = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    logger.info(f"Trying last 30 days: {from_date_30} to {to_date}")
    all_news = scrape_news(from_date_30, to_date)
    
    # If no articles in last 30 days, try last 60 days
    if not all_news:
        from_date_60 = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
        logger.info(f"Trying last 60 days: {from_date_60} to {to_date}")
        all_news = scrape_news(from_date_60, to_date)
    
    # If still no articles, try inauguration date (may fail due to API limits)
    if not all_news:
        from_date_inauguration = CONFIG['TRUMP_INAUGURATION']  # 2025-01-20
        logger.info(f"Trying from inauguration: {from_date_inauguration} to {to_date}")
        all_news = scrape_news(from_date_inauguration, to_date)
    
    # If still no articles, try without date filter (get recent articles)
    if not all_news:
        logger.info("Trying without date filter to get any recent articles")
        all_news = scrape_news()  # No date filter
    
    logger.info(f"Retrieved {len(all_news)} total REAL articles")
    
    if not all_news:
        logger.error("No real articles found! Check NewsAPI configuration.")
        return create_error_map_html("No real articles found from NewsAPI")
    
    # Use the real articles we found
    news = all_news
    
    # Process all articles and add location data
    processed_articles = []
    used_coords = []
    
    for i, item in enumerate(news):
        try:
            # Extract location using the new method
            location_name = extract_location_from_article(item)
            coords = geocode_location(location_name)
            
            # Offset coordinates if they're too close to existing markers
            original_coords = coords[:]
            offset_multiplier = 1
            while coords in used_coords:
                coords = [coords[0] + (0.01 * offset_multiplier), coords[1] + (0.01 * offset_multiplier)]
                offset_multiplier += 1
                
            used_coords.append(coords)
            
            processed_articles.append({
                **item,
                'location_name': location_name,
                'coords': coords,
                'id': f'marker_{i}'
            })
            
        except Exception as e:
            logger.error(f"Error processing real article {i}: {e}")
            continue
    
    # Create the HTML with timeline functionality - only if we have real articles
    if processed_articles:
        html_content = create_timeline_html(processed_articles)
    else:
        html_content = create_error_map_html("No real articles could be processed with valid locations")
    
    # Save to file
    map_filename = "map.html"
    with open(map_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"Timeline map created successfully with {len(processed_articles)} articles")
    return map_filename

def create_timeline_html(articles: list) -> str:
    """Generate HTML with timeline slider and map."""
    # Group articles by date - only use dates where we actually have articles
    articles_by_date = {}
    for article in articles:
        date = article.get('date', datetime.now().strftime('%Y-%m-%d'))
        if date not in articles_by_date:
            articles_by_date[date] = []
        articles_by_date[date].append(article)
    
    # Get the actual date range from our real articles
    if not articles_by_date:
        logger.error("No articles to create timeline from")
        return create_error_map_html("No articles available for timeline")
    
    # Use only the dates where we have actual articles
    dates = sorted(articles_by_date.keys())
    start_date = dates[0]
    end_date = dates[-1]
    
    logger.info(f"Creating timeline with {len(dates)} dates from {start_date} to {end_date}")
    
    # Convert articles to JSON for JavaScript
    import json
    articles_json = json.dumps(articles, default=str)
    articles_by_date_json = json.dumps(articles_by_date, default=str)
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>ICE Operations Timeline Map</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    
    <style>
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
        #map {{ height: 85vh; width: 100%; }}
        
        .timeline-container {{
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(255, 255, 255, 0.95);
            padding: 15px;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
            z-index: 1000;
        }}
        
        .timeline-header {{
            text-align: center;
            margin-bottom: 10px;
            font-weight: bold;
            color: #333;
        }}
        
        .timeline-controls {{
            display: flex;
            align-items: center;
            gap: 15px;
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .date-slider {{
            flex: 1;
            height: 6px;
            background: #ddd;
            border-radius: 3px;
            outline: none;
            appearance: none;
        }}
        
        .date-slider::-webkit-slider-thumb {{
            appearance: none;
            width: 20px;
            height: 20px;
            background: #e74c3c;
            border-radius: 50%;
            cursor: pointer;
        }}
        
        .date-slider::-moz-range-thumb {{
            width: 20px;
            height: 20px;
            background: #e74c3c;
            border-radius: 50%;
            cursor: pointer;
            border: none;
        }}
        
        .date-display {{
            min-width: 120px;
            text-align: center;
            font-weight: bold;
            color: #e74c3c;
        }}
        
        .article-count {{
            min-width: 100px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}
        
        .control-buttons {{
            display: flex;
            gap: 5px;
        }}
        
        .control-btn {{
            padding: 8px 12px;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8em;
        }}
        
        .control-btn:hover {{
            background: #2980b9;
        }}
        
        .play-btn {{
            background: #27ae60;
        }}
        
        .play-btn:hover {{
            background: #229954;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    
    <div class="timeline-container">
        <div class="timeline-header">ICE Operations Timeline - Trump Administration 2025</div>
        <div class="timeline-controls">
            <div class="date-display" id="currentDate">{start_date}</div>
            <input type="range" class="date-slider" id="dateSlider" 
                   min="0" max="{len(dates)-1 if dates else 0}" value="0" step="1">
            <div class="article-count" id="articleCount">0 events</div>
            <div class="control-buttons">
                <button class="control-btn play-btn" id="playBtn" onclick="togglePlay()">▶ Play</button>
                <button class="control-btn" onclick="resetTimeline()">Reset</button>
                <button class="control-btn" onclick="showAll()">Show All</button>
            </div>
        </div>
    </div>
    
    <!-- Leaflet JavaScript -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    
    <script>
        // Data from Python
        const articles = {articles_json};
        const articlesByDate = {articles_by_date_json};
        const dates = {json.dumps(dates)};
        
        // Initialize map
        const map = L.map('map').setView([39.8283, -98.5795], 4);
        
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors'
        }}).addTo(map);
        
        // Store markers
        let markers = {{}};
        let currentMarkers = [];
        let isPlaying = false;
        let playInterval = null;
        
        // Create all markers (initially hidden)
        articles.forEach(article => {{
            const marker = L.marker(article.coords, {{
                icon: L.icon({{
                    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
                    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34],
                    shadowSize: [41, 41]
                }})
            }});
            
            const popupContent = `
                <div style="width: 300px;">
                    <h4 style="margin-bottom: 10px;">${{article.title}}</h4>
                    <p><strong>Date:</strong> ${{article.date}}</p>
                    <p><strong>Location:</strong> ${{article.location_name}}</p>
                    <a href="${{article.url}}" target="_blank" style="color: #0066cc;">Read Full Article</a>
                </div>
            `;
            
            marker.bindPopup(popupContent);
            marker.bindTooltip(article.title);
            
            if (!markers[article.date]) {{
                markers[article.date] = [];
            }}
            markers[article.date].push(marker);
        }});
        
        // Update map based on slider value
        function updateMap(dateIndex) {{
            // Clear current markers
            currentMarkers.forEach(marker => map.removeLayer(marker));
            currentMarkers = [];
            
            if (dateIndex >= 0 && dateIndex < dates.length) {{
                const selectedDate = dates[dateIndex];
                document.getElementById('currentDate').textContent = selectedDate;
                
                // Add markers for selected date
                if (markers[selectedDate]) {{
                    markers[selectedDate].forEach(marker => {{
                        map.addLayer(marker);
                        currentMarkers.push(marker);
                    }});
                }}
                
                const count = markers[selectedDate] ? markers[selectedDate].length : 0;
                document.getElementById('articleCount').textContent = `${{count}} event${{count !== 1 ? 's' : ''}}`;
            }}
        }}
        
        // Show all markers
        function showAll() {{
            currentMarkers.forEach(marker => map.removeLayer(marker));
            currentMarkers = [];
            
            Object.values(markers).forEach(dateMarkers => {{
                dateMarkers.forEach(marker => {{
                    map.addLayer(marker);
                    currentMarkers.push(marker);
                }});
            }});
            
            document.getElementById('currentDate').textContent = 'All Dates';
            document.getElementById('articleCount').textContent = `${{currentMarkers.length}} total events`;
        }}
        
        // Reset timeline
        function resetTimeline() {{
            stopPlay();
            document.getElementById('dateSlider').value = 0;
            updateMap(0);
        }}
        
        // Toggle play/pause
        function togglePlay() {{
            if (isPlaying) {{
                stopPlay();
            }} else {{
                startPlay();
            }}
        }}
        
        function startPlay() {{
            isPlaying = true;
            document.getElementById('playBtn').innerHTML = '⏸ Pause';
            
            playInterval = setInterval(() => {{
                const slider = document.getElementById('dateSlider');
                let currentValue = parseInt(slider.value);
                
                if (currentValue >= dates.length - 1) {{
                    stopPlay();
                    return;
                }}
                
                slider.value = currentValue + 1;
                updateMap(currentValue + 1);
            }}, 1000); // Change every second
        }}
        
        function stopPlay() {{
            isPlaying = false;
            document.getElementById('playBtn').innerHTML = '▶ Play';
            if (playInterval) {{
                clearInterval(playInterval);
                playInterval = null;
            }}
        }}
        
        // Event listeners
        document.getElementById('dateSlider').addEventListener('input', function(e) {{
            updateMap(parseInt(e.target.value));
        }});
        
        // Initialize with first date
        if (dates.length > 0) {{
            updateMap(0);
        }}
    </script>
</body>
</html>
    """
    
    return html

@app.route('/')
def serve_map():
    """Serve the timeline map HTML file."""
    try:
        map_file = create_timeline_map()
        logger.info(f"Serving timeline map file: {map_file}")
        return send_file(map_file, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error serving timeline map: {e}")
        return f"<h1>Error generating timeline map</h1><p>{str(e)}</p>", 500

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.route('/api/news')
def api_news():
    """API endpoint to get raw news data with optional date filtering."""
    from flask import request
    
    try:
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        news = scrape_news(from_date, to_date)
        return {"articles": news, "count": len(news), "from_date": from_date, "to_date": to_date}
    except Exception as e:
        logger.error(f"Error in news API: {e}")
        return {"error": str(e)}, 500

@app.route('/api/timeline')
def api_timeline():
    """API endpoint to get timeline data grouped by date."""
    try:
        from_date = CONFIG['TRUMP_INAUGURATION']
        to_date = datetime.now().strftime('%Y-%m-%d')
        
        news = scrape_news(from_date, to_date)
        
        # Group by date
        timeline = {}
        for article in news:
            date = article.get('date', datetime.now().strftime('%Y-%m-%d'))
            if date not in timeline:
                timeline[date] = []
            timeline[date].append(article)
        
        return {
            "timeline": timeline,
            "total_articles": len(news),
            "date_range": {"from": from_date, "to": to_date},
            "dates": sorted(timeline.keys())
        }
    except Exception as e:
        logger.error(f"Error in timeline API: {e}")
        return {"error": str(e)}, 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting ICE GIS App on port {port}")
    logger.info(f"Debug mode: {debug}")
    
    app.run(
        host='0.0.0.0', 
        port=port,
        debug=debug,
        threaded=True
    )
