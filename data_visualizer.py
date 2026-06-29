import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def generate_visualizations(df: pd.DataFrame, output_dir: str = "visuals") -> dict:
    """
    Generates Matplotlib charts for earthquake analysis and saves them as images.
    
    Parameters:
        df (pd.DataFrame): Cleaned earthquake DataFrame.
        output_dir (str): Folder where visualizations will be saved.
        
    Returns:
        dict: A dictionary containing paths to the generated chart files.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Define aesthetic parameters
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    
    # Custom font & text settings
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Helvetica', 'Arial', 'Liberation Sans']
    plt.rcParams['text.color'] = '#2E3440'
    plt.rcParams['axes.labelcolor'] = '#4C566A'
    plt.rcParams['xtick.color'] = '#4C566A'
    plt.rcParams['ytick.color'] = '#4C566A'
    plt.rcParams['axes.edgecolor'] = '#D8DEE9'
    plt.rcParams['grid.color'] = '#E5E9F0'
    plt.rcParams['grid.linestyle'] = '--'
    plt.rcParams['grid.alpha'] = 0.7
    
    # Color palette
    colors_dict = {
        "Minor": "#5E81AC",      # Nord Slate Blue
        "Light": "#8FBCBB",      # Nord Teal
        "Moderate": "#D08770",   # Nord Orange
        "Strong": "#BF616A",     # Nord Red
        "Major": "#88C0D0"       # Nord Frost Blue
    }
    
    chart_paths = {}
    
    # --- CHART 1: Magnitude Distribution (Bar Chart) ---
    fig, ax = plt.subplots(figsize=(7, 4.5), layout="constrained")
    
    # Get magnitude counts in correct order
    classes = ["Minor", "Light", "Moderate", "Strong", "Major"]
    counts = []
    bar_colors = []
    
    class_counts = df["magnitude_class"].value_counts()
    for cls in classes:
        counts.append(class_counts.get(cls, 0))
        # Warm color mapping depending on severity
        if cls == "Minor":
            bar_colors.append("#4C6EF5") # Blue
        elif cls == "Light":
            bar_colors.append("#12B886") # Teal
        elif cls == "Moderate":
            bar_colors.append("#FAB005") # Yellow/Orange
        elif cls == "Strong":
            bar_colors.append("#FD7E14") # Dark Orange
        else: # Major
            bar_colors.append("#FA5252") # Red
            
    bars = ax.bar(classes, counts, color=bar_colors, width=0.6, edgecolor="#ECEFF4", linewidth=1.2)
    
    # Set labels & titles
    ax.set_title("Earthquake Frequency by Magnitude Classification", fontsize=14, fontweight="bold", pad=15, color="#2E3440")
    ax.set_xlabel("Magnitude Class", fontsize=11, labelpad=8)
    ax.set_ylabel("Number of Events", fontsize=11, labelpad=8)
    
    # Value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax.annotate(f'{height}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=9, fontweight="bold", color="#4C566A")
            
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#D8DEE9')
    ax.spines['bottom'].set_color('#D8DEE9')
    
    mag_dist_path = os.path.join(output_dir, "magnitude_distribution.png")
    fig.savefig(mag_dist_path, dpi=300)
    plt.close(fig)
    chart_paths["magnitude_distribution"] = mag_dist_path
    
    # --- CHART 2: Depth vs Magnitude (Scatter Plot) ---
    fig, ax = plt.subplots(figsize=(7, 4.5), layout="constrained")
    
    # Invert the depth axis so deeper earthquakes are visually lower
    # Use significance for scatter point sizes, and magnitude for color
    scatter = ax.scatter(
        df["mag"], 
        df["depth"], 
        s=df["sig"] * 0.3 + 15, # size scales with significance
        c=df["mag"], 
        cmap="plasma", 
        alpha=0.75, 
        edgecolors="w", 
        linewidths=0.5
    )
    
    ax.set_title("Earthquake Depth vs. Magnitude Profile", fontsize=14, fontweight="bold", pad=15, color="#2E3440")
    ax.set_xlabel("Magnitude (M)", fontsize=11, labelpad=8)
    ax.set_ylabel("Depth (km)", fontsize=11, labelpad=8)
    
    # Invert y-axis to represent depth under surface
    ax.invert_yaxis()
    
    # Colorbar
    cbar = fig.colorbar(scatter, ax=ax, pad=0.02)
    cbar.set_label("Magnitude (M)", fontsize=10, labelpad=8)
    cbar.ax.tick_params(labelsize=9)
    cbar.outline.set_edgecolor('#D8DEE9')
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#D8DEE9')
    ax.spines['bottom'].set_color('#D8DEE9')
    
    depth_scatter_path = os.path.join(output_dir, "depth_vs_magnitude.png")
    fig.savefig(depth_scatter_path, dpi=300)
    plt.close(fig)
    chart_paths["depth_vs_magnitude"] = depth_scatter_path
    
    # --- CHART 3: Daily Trend (Dual-Axis Timeline) ---
    # Group by date and calculate metrics
    daily_df = df.groupby("date").agg(
        count=("id", "count"),
        max_mag=("mag", "max")
    ).reset_index()
    
    daily_df["date"] = pd.to_datetime(daily_df["date"])
    daily_df = daily_df.sort_values("date")
    
    fig, ax1 = plt.subplots(figsize=(7.5, 4.5), layout="constrained")
    
    # Primary axis - Frequency of events (Shaded Area Chart)
    color_freq = "#228BE6" # Deepish blue
    ax1.fill_between(daily_df["date"], daily_df["count"], color=color_freq, alpha=0.15)
    line1, = ax1.plot(daily_df["date"], daily_df["count"], color=color_freq, linewidth=2, label="Daily Event Count")
    
    ax1.set_xlabel("Date", fontsize=11, labelpad=8)
    ax1.set_ylabel("Daily Earthquake Frequency", color=color_freq, fontsize=11, labelpad=8)
    ax1.tick_params(axis='y', labelcolor=color_freq)
    ax1.grid(True, linestyle="--", alpha=0.5)
    
    # Secondary axis - Maximum magnitude (Line Chart with markers)
    ax2 = ax1.twinx()
    color_mag = "#FA5252" # Coral Red
    line2, = ax2.plot(daily_df["date"], daily_df["max_mag"], color=color_mag, linewidth=2, linestyle="-.", marker="o", markersize=5, label="Max Magnitude (M)")
    
    ax2.set_ylabel("Max Magnitude (M)", color=color_mag, fontsize=11, labelpad=8)
    ax2.tick_params(axis='y', labelcolor=color_mag)
    ax2.grid(False) # Turn off grid lines on secondary axis so it doesn't overlap
    
    # Add a title
    ax1.set_title("Earthquake Activity Trend & Peak Magnitudes", fontsize=14, fontweight="bold", pad=15, color="#2E3440")
    
    # Formatter for date x-axis
    fig.autofmt_xdate()
    
    # Legend combining both plots
    lines = [line1, line2]
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper left", frameon=True, facecolor="#FFFFFF", edgecolor="#E5E9F0")
    
    ax1.spines['top'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    ax1.spines['left'].set_color('#D8DEE9')
    ax1.spines['bottom'].set_color('#D8DEE9')
    
    trend_path = os.path.join(output_dir, "activity_trend.png")
    fig.savefig(trend_path, dpi=300)
    plt.close(fig)
    chart_paths["activity_trend"] = trend_path
    
    return chart_paths
