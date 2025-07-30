# ICE GIS Timeline App

An interactive web application that displays real immigration enforcement news articles on a timeline map.

## Features

- **Real News Articles**: Uses NewsAPI to fetch legitimate news articles about ICE operations, border patrol, and immigration enforcement
- **Interactive Timeline**: Navigate through dates using a timeline slider from June 2025 to July 2025
- **Geographic Mapping**: Articles are plotted on an interactive map based on their geographic locations
- **Play/Pause Controls**: Automatically advance through the timeline or manually navigate
- **No Fake Data**: All articles link to real news sources - no generated or fake URLs

## Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ice-gis-app.git
   cd ice-gis-app
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your NewsAPI key
   ```

4. **Get a NewsAPI key**:
   - Visit [NewsAPI](https://newsapi.org/)
   - Sign up for a free account
   - Add your API key to the `.env` file

5. **Run the application**:
   ```bash
   python app.py
   ```

6. **Access the app**:
   - Open your browser to `http://localhost:8080`

## Deployment

### Heroku
1. Install Heroku CLI
2. Create a Heroku app: `heroku create your-app-name`
3. Set environment variables: `heroku config:set NEWS_API_KEY=your_key_here`
4. Deploy: `git push heroku main`

### Railway
1. Connect your GitHub repository to Railway
2. Set the `NEWS_API_KEY` environment variable
3. Deploy automatically

### Render
1. Connect your GitHub repository to Render
2. Set the `NEWS_API_KEY` environment variable
3. Deploy as a web service

## API Endpoints

- `/` - Main timeline map interface
- `/api/news` - Get raw news data (supports `from_date` and `to_date` parameters)
- `/api/timeline` - Get timeline data grouped by date
- `/health` - Health check endpoint

## Technology Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **Mapping**: Folium + Leaflet.js
- **Data**: NewsAPI for real news articles
- **Geocoding**: Nominatim (OpenStreetMap)

## Configuration

Environment variables:
- `NEWS_API_KEY` - Your NewsAPI key (required)
- `PORT` - Port to run the app on (default: 8080)
- `FLASK_DEBUG` - Enable debug mode (default: True)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is for educational and research purposes only.