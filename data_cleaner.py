import pandas as pd
import numpy as np

def clean_location(place: str) -> str:
    """
    Extracts the region, state, or country name from the place description.
    Example: '12km E of Mammoth Lakes, CA' -> 'CA'
             'Offshore El Salvador' -> 'Offshore El Salvador'
    """
    if not isinstance(place, str):
        return "Unknown"
    
    parts = place.split(",")
    if len(parts) > 1:
        return parts[-1].strip()
    
    # Check for common oceanic / offshore strings
    place_strip = place.strip()
    if "offshore" in place_strip.lower():
        # Clean offshore locations slightly to represent the region
        return place_strip
    return place_strip

def classify_magnitude(mag: float) -> str:
    """Classifies an earthquake magnitude into human-readable categories."""
    if pd.isna(mag):
        return "Unknown"
    if mag < 3.0:
        return "Minor"
    elif mag < 4.5:
        return "Light"
    elif mag < 6.0:
        return "Moderate"
    elif mag < 7.0:
        return "Strong"
    else:
        return "Major"

def clean_raw_data(raw_data: dict) -> pd.DataFrame:
    """
    Converts raw USGS GeoJSON dictionary into a cleaned Pandas DataFrame.
    
    Parameters:
        raw_data (dict): Raw GeoJSON fetched from the USGS API.
        
    Returns:
        pd.DataFrame: Cleaned and structured DataFrame.
    """
    features = raw_data.get("features", [])
    if not features:
        return pd.DataFrame() # Return empty DataFrame if no features
        
    # Extract properties
    properties = [feat.get("properties", {}) for feat in features]
    df = pd.DataFrame(properties)
    
    # Extract geometry coordinates: [longitude, latitude, depth]
    coordinates = [feat.get("geometry", {}).get("coordinates", [np.nan, np.nan, np.nan]) for feat in features]
    
    # Ensure coordinates always has 3 elements
    coords_fixed = []
    for coord in coordinates:
        if len(coord) >= 3:
            coords_fixed.append(coord[:3])
        elif len(coord) == 2:
            coords_fixed.append([coord[0], coord[1], np.nan])
        else:
            coords_fixed.append([np.nan, np.nan, np.nan])
            
    df["longitude"] = [c[0] for c in coords_fixed]
    df["latitude"] = [c[1] for c in coords_fixed]
    df["depth"] = [c[2] for c in coords_fixed]
    df["id"] = [feat.get("id") for feat in features]
    
    # --- CLEANING AND PROCESSING ---
    
    # 1. Drop duplicates based on earthquake ID
    df = df.drop_duplicates(subset=["id"])
    
    # 2. Handle missing magnitudes and filter invalid/negative magnitudes
    df = df.dropna(subset=["mag"])
    df = df[df["mag"] >= 0]
    
    # 3. Fill missing values in key columns
    df["felt"] = df["felt"].fillna(0).astype(int)
    df["cdi"] = df["cdi"].fillna(0.0).astype(float)
    df["mmi"] = df["mmi"].fillna(0.0).astype(float)
    df["alert"] = df["alert"].fillna("none").astype(str)
    
    # Fill structural columns
    df["tsunami"] = df["tsunami"].fillna(0).astype(int)
    df["sig"] = df["sig"].fillna(0).astype(int)
    
    # 4. Data type conversions (Unix millisecond timestamps to datetime objects)
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    df["updated"] = pd.to_datetime(df["updated"], unit="ms")
    
    # Add a formatted readable local time string column
    df["time_readable"] = df["time"].dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    df["date"] = df["time"].dt.date
    
    # 5. Feature Engineering
    df["region"] = df["place"].apply(clean_location)
    df["magnitude_class"] = df["mag"].apply(classify_magnitude)
    
    # Reorder/Select relevant columns for cleaner outputs
    cols_to_keep = [
        "id", "time", "date", "time_readable", "mag", "magnitude_class", "place", "region",
        "longitude", "latitude", "depth", "tsunami", "felt", "cdi", "mmi", "sig", "alert", "status"
    ]
    
    # Filter to only keep columns that actually exist in the dataframe
    existing_cols = [col for col in cols_to_keep if col in df.columns]
    df = df[existing_cols]
    
    # Sort chronologically (oldest to newest)
    df = df.sort_values("time").reset_index(drop=True)
    
    return df
