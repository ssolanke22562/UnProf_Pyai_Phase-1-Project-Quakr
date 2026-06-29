import requests
from datetime import datetime, timedelta
import urllib.parse

USGS_API_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

class FetchError(Exception):
    """Custom exception for API fetching errors."""
    pass

def fetch_earthquake_data(start_date: str = None, end_date: str = None, min_magnitude: float = 2.5) -> dict:
    """
    Fetches earthquake data from the USGS API in GeoJSON format.
    
    Parameters:
        start_date (str): Start date in YYYY-MM-DD format. Defaults to 30 days ago.
        end_date (str): End date in YYYY-MM-DD format. Defaults to today.
        min_magnitude (float): Minimum magnitude of earthquakes to fetch. Defaults to 2.5.
        
    Returns:
        dict: The parsed GeoJSON response from the API.
        
    Raises:
        FetchError: If the request fails, times out, or returns a non-200 status code.
    """
    # Default date ranges if not provided
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
        
    # Validate date formats
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError as e:
        raise FetchError(f"Invalid date format. Must be YYYY-MM-DD. Error: {e}")

    params = {
        "format": "geojson",
        "starttime": start_date,
        "endtime": end_date,
        "minmagnitude": min_magnitude,
        "orderby": "time"
    }

    try:
        # Construct URL for logging purposes
        query_string = urllib.parse.urlencode(params)
        full_url = f"{USGS_API_URL}?{query_string}"
        
        response = requests.get(USGS_API_URL, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        # Check if the GeoJSON is valid or has features
        if "features" not in data:
            raise FetchError("Invalid API response format. Missing 'features' key.")
            
        return data
        
    except requests.exceptions.Timeout:
        raise FetchError("The request to USGS API timed out. Please try again later.")
    except requests.exceptions.ConnectionError:
        raise FetchError("Failed to connect to the USGS API. Check your internet connection.")
    except requests.exceptions.HTTPError as e:
        raise FetchError(f"USGS API returned HTTP Error: {e.response.status_code}. Details: {e}")
    except ValueError:
        raise FetchError("Failed to parse JSON response from USGS API.")
    except Exception as e:
        raise FetchError(f"An unexpected error occurred while fetching data: {e}")
