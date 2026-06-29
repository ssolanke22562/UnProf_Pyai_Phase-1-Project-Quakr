import pandas as pd
import numpy as np

def run_analysis(df: pd.DataFrame) -> dict:
    """
    Analyzes the cleaned earthquake DataFrame and computes summaries.
    
    Parameters:
        df (pd.DataFrame): Cleaned earthquake DataFrame.
        
    Returns:
        dict: A dictionary containing various analytical summaries.
    """
    if df.empty:
        return {
            "total_count": 0,
            "mag_stats": {},
            "class_counts": {},
            "top_regions": [],
            "strongest_events": [],
            "tsunami_stats": {},
            "correlation_mag_depth": 0.0
        }

    # 1. General counts and overall magnitude stats
    mag_stats = {
        "mean": float(df["mag"].mean()),
        "median": float(df["mag"].median()),
        "min": float(df["mag"].min()),
        "max": float(df["mag"].max()),
        "std": float(df["mag"].std()) if len(df) > 1 else 0.0
    }
    
    # 2. Magnitude Class Distribution
    class_counts = df["magnitude_class"].value_counts().to_dict()
    # Ensure all classes exist in the dict for completeness
    for cls in ["Minor", "Light", "Moderate", "Strong", "Major"]:
        if cls not in class_counts:
            class_counts[cls] = 0
            
    # 3. Top Active Regions (by count)
    region_counts = df["region"].value_counts().reset_index()
    region_counts.columns = ["region", "count"]
    
    # Get max magnitude per region
    region_max = df.groupby("region")["mag"].max().reset_index()
    region_max.columns = ["region", "max_mag"]
    
    # Merge region data
    region_summary = pd.merge(region_counts, region_max, on="region")
    top_regions = region_summary.head(10).to_dict(orient="records")
    
    # 4. Top 5 Strongest Earthquakes
    strongest_events = df.sort_values("mag", ascending=False).head(5)[
        ["time_readable", "mag", "place", "region", "depth", "tsunami", "felt"]
    ].to_dict(orient="records")
    
    # 5. Tsunami Risk Analysis
    tsunami_counts = df["tsunami"].value_counts().to_dict()
    tsunami_yes = tsunami_counts.get(1, 0)
    tsunami_no = tsunami_counts.get(0, 0)
    
    mag_by_tsunami = df.groupby("tsunami")["mag"].mean().to_dict()
    mean_mag_yes = mag_by_tsunami.get(1, 0.0)
    mean_mag_no = mag_by_tsunami.get(0, 0.0)
    
    tsunami_stats = {
        "count_yes": int(tsunami_yes),
        "count_no": int(tsunami_no),
        "percentage_yes": float(tsunami_yes / len(df) * 100) if len(df) > 0 else 0.0,
        "mean_mag_yes": float(mean_mag_yes),
        "mean_mag_no": float(mean_mag_no)
    }
    
    # 6. Depth Analysis
    depth_stats = {
        "mean": float(df["depth"].mean()) if df["depth"].notna().any() else 0.0,
        "min": float(df["depth"].min()) if df["depth"].notna().any() else 0.0,
        "max": float(df["depth"].max()) if df["depth"].notna().any() else 0.0
    }
    
    # 7. Correlation between magnitude and depth
    correlation = 0.0
    if len(df) > 1 and df["depth"].notna().any() and df["depth"].std() > 0:
        correlation = float(df["mag"].corr(df["depth"]))
        if np.isnan(correlation):
            correlation = 0.0
            
    # 8. Activity Timeline (Daily counts)
    daily_activity = df.groupby("date").agg(
        count=("id", "count"),
        max_mag=("mag", "max")
    ).reset_index()
    
    # Convert date to string for JSON serialization
    daily_activity["date"] = daily_activity["date"].astype(str)
    daily_stats = daily_activity.to_dict(orient="records")

    return {
        "total_count": len(df),
        "mag_stats": mag_stats,
        "class_counts": class_counts,
        "top_regions": top_regions,
        "strongest_events": strongest_events,
        "tsunami_stats": tsunami_stats,
        "depth_stats": depth_stats,
        "correlation_mag_depth": correlation,
        "daily_stats": daily_stats
    }
