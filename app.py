import os
import json
from datetime import datetime, timedelta
import pandas as pd
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import pipeline modules
from data_fetcher import fetch_earthquake_data, FetchError
from data_cleaner import clean_raw_data
from data_analyzer import run_analysis
from data_visualizer import generate_visualizations
from pdf_generator import create_pdf_report

# Ensure output directories exist at startup
DATA_DIR = "data"
VISUALS_DIR = "visuals"
REPORTS_DIR = "reports"
STATIC_DIR = "static"

for folder in [DATA_DIR, VISUALS_DIR, REPORTS_DIR, STATIC_DIR]:
    os.makedirs(folder, exist_ok=True)

app = FastAPI(
    title="Seismic Pipeline Engine API",
    description="Backend API for the Fetch ➔ Clean ➔ Analyze ➔ Visualize ➔ Save ➔ Report pipeline",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PipelineParams(BaseModel):
    start_date: str = Field(
        default_factory=lambda: (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
        description="Start date for data query (YYYY-MM-DD)"
    )
    end_date: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d"),
        description="End date for data query (YYYY-MM-DD)"
    )
    min_magnitude: float = Field(
        default=2.5,
        ge=0.0,
        le=10.0,
        description="Minimum earthquake magnitude threshold"
    )

@app.get("/")
def read_index():
    """Serves the main frontend Single Page Application (SPA)."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        # Fallback response if index.html doesn't exist yet
        return JSONResponse(
            content={"message": "Frontend static file index.html is missing. Please create it in the static/ folder."},
            status_code=404
        )
    return FileResponse(index_path)

@app.get("/api/pipeline/status")
def get_status():
    """Returns the current availability status of cached data files on disk."""
    raw_path = os.path.join(DATA_DIR, "raw_earthquakes.json")
    csv_path = os.path.join(DATA_DIR, "cleaned_earthquakes.csv")
    json_path = os.path.join(DATA_DIR, "cleaned_earthquakes.json")
    pdf_path = os.path.join(REPORTS_DIR, "earthquake_report.pdf")
    
    # Check if files exist
    raw_exists = os.path.exists(raw_path)
    csv_exists = os.path.exists(csv_path)
    json_exists = os.path.exists(json_path)
    pdf_exists = os.path.exists(pdf_path)
    
    metadata = {}
    if csv_exists:
        try:
            df = pd.read_csv(csv_path)
            metadata["total_records"] = len(df)
            if "time" in df.columns and len(df) > 0:
                metadata["min_date"] = str(df["time"].min())
                metadata["max_date"] = str(df["time"].max())
        except Exception:
            pass

    return {
        "files": {
            "raw_json": raw_exists,
            "cleaned_csv": csv_exists,
            "cleaned_json": json_exists,
            "pdf_report": pdf_exists
        },
        "metadata": metadata
    }

@app.post("/api/pipeline/run")
def run_pipeline(params: PipelineParams):
    """
    Triggers the end-to-end data pipeline synchronously and returns analysis results.
    """
    try:
        # Validate date formats
        try:
            datetime.strptime(params.start_date, "%Y-%m-%d")
            datetime.strptime(params.end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Must be YYYY-MM-DD.")
            
        # Step 1: Fetch
        try:
            raw_data = fetch_earthquake_data(
                start_date=params.start_date,
                end_date=params.end_date,
                min_magnitude=params.min_magnitude
            )
            raw_path = os.path.join(DATA_DIR, "raw_earthquakes.json")
            with open(raw_path, 'w', encoding='utf-8') as f:
                json.dump(raw_data, f, indent=2)
        except FetchError as e:
            raise HTTPException(status_code=502, detail=f"Failed to fetch data from USGS: {str(e)}")
            
        # Step 2: Clean
        df = clean_raw_data(raw_data)
        if df.empty:
            return JSONResponse(
                content={
                    "status": "empty",
                    "message": "No earthquakes matching the criteria were found during this date range.",
                    "total_count": 0
                }
            )
            
        # Step 3: Save Data locally
        csv_path = os.path.join(DATA_DIR, "cleaned_earthquakes.csv")
        json_path = os.path.join(DATA_DIR, "cleaned_earthquakes.json")
        
        df.to_csv(csv_path, index=False)
        
        # Serialize datetime columns for JSON output
        from datetime import date
        records_df = df.copy()
        for col in records_df.columns:
            if len(records_df) > 0:
                first_val = records_df[col].iloc[0]
                if pd.api.types.is_datetime64_any_dtype(records_df[col]) or isinstance(first_val, (datetime, date)):
                    records_df[col] = records_df[col].astype(str)
        records = records_df.to_dict(orient="records")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=2)
            
        # Step 4: Analyze
        analysis_results = run_analysis(df)
        
        # Step 5: Visualize
        chart_paths = generate_visualizations(df, output_dir=VISUALS_DIR)
        
        # Step 6: PDF Report
        pdf_path = os.path.join(REPORTS_DIR, "earthquake_report.pdf")
        create_pdf_report(
            analysis_results=analysis_results,
            chart_paths=chart_paths,
            date_range=f"{params.start_date} to {params.end_date}",
            output_path=pdf_path
        )
        
        # Add relative URL paths for charts to allow direct HTML loading
        web_chart_paths = {
            k: f"/{v.replace(os.sep, '/')}" for k, v in chart_paths.items()
        }
        
        return {
            "status": "success",
            "date_range": f"{params.start_date} to {params.end_date}",
            "min_magnitude": params.min_magnitude,
            "total_count": analysis_results["total_count"],
            "mag_stats": analysis_results["mag_stats"],
            "class_counts": analysis_results["class_counts"],
            "top_regions": analysis_results["top_regions"],
            "strongest_events": analysis_results["strongest_events"],
            "tsunami_stats": analysis_results["tsunami_stats"],
            "depth_stats": analysis_results["depth_stats"],
            "correlation_mag_depth": analysis_results["correlation_mag_depth"],
            "charts": web_chart_paths
        }
        
    except Exception as e:
        # In a real app, log the error trace
        raise HTTPException(status_code=500, detail=f"Pipeline execution error: {str(e)}")

# Download routes
@app.get("/api/pipeline/download/csv")
def download_csv():
    """Serves the cleaned CSV dataset for download."""
    csv_path = os.path.join(DATA_DIR, "cleaned_earthquakes.csv")
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="Cleaned CSV data is not available. Run the pipeline first.")
    return FileResponse(csv_path, media_type="text/csv", filename="cleaned_earthquakes.csv")

@app.get("/api/pipeline/download/json")
def download_json():
    """Serves the cleaned JSON dataset for download."""
    json_path = os.path.join(DATA_DIR, "cleaned_earthquakes.json")
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Cleaned JSON data is not available. Run the pipeline first.")
    return FileResponse(json_path, media_type="application/json", filename="cleaned_earthquakes.json")

@app.get("/api/pipeline/download/pdf")
def download_pdf():
    """Serves the generated PDF report for download."""
    pdf_path = os.path.join(REPORTS_DIR, "earthquake_report.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF report is not available. Run the pipeline first.")
    return FileResponse(pdf_path, media_type="application/pdf", filename="earthquake_report.pdf")

# Mount visual images and reports directories as static
app.mount("/visuals", StaticFiles(directory=VISUALS_DIR), name="visuals")
app.mount("/reports", StaticFiles(directory=REPORTS_DIR), name="reports")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
