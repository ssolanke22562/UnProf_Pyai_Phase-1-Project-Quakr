import os
import sys
import json
import pandas as pd
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, FloatPrompt
from rich.align import Align
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
from rich.theme import Theme

# Reconfigure stdout/stderr to use UTF-8 to prevent UnicodeEncodeError on Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


# Import modular components
from data_fetcher import fetch_earthquake_data, FetchError
from data_cleaner import clean_raw_data
from data_analyzer import run_analysis
from data_visualizer import generate_visualizations
from pdf_generator import create_pdf_report

# Custom console theme
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "accent": "bold magenta",
    "title": "bold white on blue",
})

console = Console(theme=custom_theme)

class PipelineState:
    """Manages the in-memory state of the data engineering pipeline."""
    def __init__(self):
        self.start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        self.end_date = datetime.now().strftime("%Y-%m-%d")
        self.min_magnitude = 2.5
        
        self.raw_data = None
        self.cleaned_df = None
        self.analysis_results = None
        self.chart_paths = None
        
        # Output directory settings
        self.data_dir = "data"
        self.visuals_dir = "visuals"
        self.reports_dir = "reports"
        
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.visuals_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)
        
        # Load local cache if available
        self.load_cache()

    @property
    def date_range_str(self) -> str:
        return f"{self.start_date} to {self.end_date} (Min Magnitude: {self.min_magnitude})"

    def load_cache(self):
        """Attempts to load cached datasets from disk to speed up execution."""
        raw_path = os.path.join(self.data_dir, "raw_earthquakes.json")
        cleaned_path = os.path.join(self.data_dir, "cleaned_earthquakes.csv")
        
        if os.path.exists(raw_path):
            try:
                with open(raw_path, 'r', encoding='utf-8') as f:
                    self.raw_data = json.load(f)
            except Exception:
                pass
                
        if os.path.exists(cleaned_path):
            try:
                self.cleaned_df = pd.read_csv(cleaned_path)
                # Convert dates back to datetime
                if 'time' in self.cleaned_df.columns:
                    self.cleaned_df['time'] = pd.to_datetime(self.cleaned_df['time'])
                if 'updated' in self.cleaned_df.columns:
                    self.cleaned_df['updated'] = pd.to_datetime(self.cleaned_df['updated'])
            except Exception:
                pass


def display_header():
    """Prints a beautiful title banner in the console."""
    console.print(Align.center(Panel.fit(
        "[bold cyan]⚡ SEISMIC PIPELINE ENGINE ⚡[/bold cyan]\n"
        "[dim]Fetch ➔ Clean ➔ Analyze ➔ Visualize ➔ Save ➔ Report[/dim]",
        border_style="cyan",
        padding=(1, 5)
    )))


def run_fetch_step(state: PipelineState) -> bool:
    """Executes the Fetching step."""
    console.print("\n[bold info][Step 1/5] Fetching data from USGS API...[/bold info]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        progress.add_task(description=f"Querying events ({state.start_date} to {state.end_date})...", total=None)
        try:
            state.raw_data = fetch_earthquake_data(
                start_date=state.start_date,
                end_date=state.end_date,
                min_magnitude=state.min_magnitude
            )
        except FetchError as e:
            console.print(f"[error]Fetching failed: {e}[/error]")
            return False
            
    # Save Raw Data
    raw_path = os.path.join(state.data_dir, "raw_earthquakes.json")
    try:
        with open(raw_path, 'w', encoding='utf-8') as f:
            json.dump(state.raw_data, f, indent=2)
        total_fetched = len(state.raw_data.get("features", []))
        console.print(f"[success]✔ Successfully fetched {total_fetched} raw events![/success]")
        console.print(f"[dim]Raw GeoJSON cached in [underline]{raw_path}[/underline][/dim]")
        return True
    except Exception as e:
        console.print(f"[error]Failed to cache raw data: {e}[/error]")
        return False


def run_clean_step(state: PipelineState) -> bool:
    """Executes the Cleaning & Feature Engineering step."""
    if state.raw_data is None:
        console.print("[warning]⚠ No raw data loaded in memory. Fetching first...[/warning]")
        if not run_fetch_step(state):
            return False
            
    console.print("\n[bold info][Step 2/5] Cleaning & flattening data...[/bold info]")
    
    try:
        initial_count = len(state.raw_data.get("features", []))
        state.cleaned_df = clean_raw_data(state.raw_data)
        final_count = len(state.cleaned_df)
        
        console.print(f"[success]✔ Cleaning complete! Structured {initial_count} features into tabular format.[/success]")
        if initial_count != final_count:
            console.print(f"[info]Note: Removed {initial_count - final_count} invalid or outlier features.[/info]")
            
        return True
    except Exception as e:
        console.print(f"[error]Cleaning failed: {e}[/error]")
        import traceback
        console.print(traceback.format_exc(), style="dim")
        return False


def run_analyze_step(state: PipelineState) -> bool:
    """Executes the Analysis step and prints summary tables to the terminal."""
    if state.cleaned_df is None:
        console.print("[warning]⚠ No cleaned dataset available. Cleaning first...[/warning]")
        if not run_clean_step(state):
            return False
            
    console.print("\n[bold info][Step 3/5] Performing statistical analysis...[/bold info]")
    
    try:
        state.analysis_results = run_analysis(state.cleaned_df)
        res = state.analysis_results
        
        # Display Stats Table in CLI
        table = Table(title="Earthquake Dataset General Statistics", border_style="cyan")
        table.add_column("Metric", style="bold cyan")
        table.add_column("Magnitude (M)", style="green")
        table.add_column("Depth (km)", style="magenta")
        
        mag = res["mag_stats"]
        depth = res["depth_stats"]
        table.add_row("Count", f"{res['total_count']}", f"{res['total_count']}")
        table.add_row("Mean (Avg)", f"{mag.get('mean', 0.0):.3f}", f"{depth.get('mean', 0.0):.2f}")
        table.add_row("Median", f"{mag.get('median', 0.0):.2f}", f"{depth.get('median', 0.0):.2f}")
        table.add_row("Min", f"{mag.get('min', 0.0):.2f}", f"{depth.get('min', 0.0):.2f}")
        table.add_row("Max", f"{mag.get('max', 0.0):.2f}", f"{depth.get('max', 0.0):.2f}")
        
        console.print(table)
        
        # Display Hazard Class Counts
        table_class = Table(title="Hazard Classification Frequencies", border_style="yellow")
        table_class.add_column("Magnitude Class", style="bold yellow")
        table_class.add_column("Occurrence Count", style="green")
        
        for k, v in res["class_counts"].items():
            table_class.add_row(k, str(v))
        console.print(table_class)
        
        # Tsunami and correlation briefs
        console.print(f"[info]Tsunami Warnings Triggered:[/info] [bold]{res['tsunami_stats']['count_yes']}[/bold] events ({res['tsunami_stats']['percentage_yes']:.1f}%)")
        console.print(f"[info]Correlation (Magnitude vs Depth):[/info] [bold]{res['correlation_mag_depth']:.4f}[/bold]")
        
        return True
    except Exception as e:
        console.print(f"[error]Analysis failed: {e}[/error]")
        return False


def run_visualize_step(state: PipelineState) -> bool:
    """Executes the Visualization step."""
    if state.cleaned_df is None:
        console.print("[warning]⚠ No cleaned dataset available. Processing first...[/warning]")
        if not run_clean_step(state):
            return False
            
    console.print("\n[bold info][Step 4/5] Rendering Matplotlib charts...[/bold info]")
    
    try:
        state.chart_paths = generate_visualizations(state.cleaned_df, output_dir=state.visuals_dir)
        console.print(f"[success]✔ Visualizations successfully generated and saved to [underline]{state.visuals_dir}/[/underline]![/success]")
        for chart_name, path in state.chart_paths.items():
            console.print(f"  • {chart_name.replace('_', ' ').title()}: [dim]{path}[/dim]")
        return True
    except Exception as e:
        console.print(f"[error]Visualization rendering failed: {e}[/error]")
        return False


def run_save_step(state: PipelineState) -> bool:
    """Saves cleaned DataFrame locally as CSV and JSON."""
    if state.cleaned_df is None:
        console.print("[warning]⚠ No cleaned dataset available to save. Processing first...[/warning]")
        if not run_clean_step(state):
            return False
            
    console.print("\n[bold info][Step 5/5] Exporting processed datasets to disk...[/bold info]")
    
    csv_path = os.path.join(state.data_dir, "cleaned_earthquakes.csv")
    json_path = os.path.join(state.data_dir, "cleaned_earthquakes.json")
    
    try:
        # Save CSV
        state.cleaned_df.to_csv(csv_path, index=False)
        
        # Save JSON (Need to handle datetime serialization)
        # Convert df to records and convert datetime columns to strings
        from datetime import date
        records_df = state.cleaned_df.copy()
        for col in records_df.columns:
            if len(records_df) > 0:
                first_val = records_df[col].iloc[0]
                if pd.api.types.is_datetime64_any_dtype(records_df[col]) or isinstance(first_val, (datetime, date)):
                    records_df[col] = records_df[col].astype(str)
                
        records = records_df.to_dict(orient="records")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=2)
            
        console.print(f"[success]✔ Saved Cleaned CSV:[/success] [underline]{csv_path}[/underline]")
        console.print(f"[success]✔ Saved Cleaned JSON:[/success] [underline]{json_path}[/underline]")
        return True
    except Exception as e:
        console.print(f"[error]Saving files failed: {e}[/error]")
        return False


def run_pdf_report_step(state: PipelineState) -> bool:
    """Compiles everything into the ReportLab PDF document."""
    # Ensure dependencies are loaded
    if state.cleaned_df is None:
        console.print("[warning]⚠ Cleaned data is missing. Processing first...[/warning]")
        if not run_clean_step(state):
            return False
            
    if state.analysis_results is None:
        if not run_analyze_step(state):
            return False
            
    if state.chart_paths is None:
        if not run_visualize_step(state):
            return False
            
    console.print("\n[bold info][Bonus Step] Compiling PDF report...[/bold info]")
    
    report_path = os.path.join(state.reports_dir, "earthquake_report.pdf")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        ) as progress:
            progress.add_task(description="Generating ReportLab story layouts...", total=None)
            create_pdf_report(
                analysis_results=state.analysis_results,
                chart_paths=state.chart_paths,
                date_range=f"{state.start_date} to {state.end_date}",
                output_path=report_path
            )
            
        console.print(f"[success]✔ Professional report successfully exported![/success]")
        console.print(f"[success]➔ PDF Document Location:[/success] [underline]{report_path}[/underline]")
        return True
    except Exception as e:
        console.print(f"[error]PDF generation failed: {e}[/error]")
        import traceback
        console.print(traceback.format_exc(), style="dim")
        return False


def run_entire_pipeline(state: PipelineState):
    """Executes all pipeline components in sequence."""
    console.print(Panel("[bold cyan]🚀 EXECUTING COMPLETE END-TO-END PIPELINE[/bold cyan]", border_style="cyan"))
    
    steps = [
        ("Fetching Data", run_fetch_step),
        ("Cleaning & Processing", run_clean_step),
        ("Statistical Analysis", run_analyze_step),
        ("Matplotlib Visualization", run_visualize_step),
        ("Local Dataset Export", run_save_step),
        ("PDF Report Compilation", run_pdf_report_step)
    ]
    
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=30, complete_style="green", finished_style="bold green"),
        MofNCompleteColumn(),
        transient=False
    ) as progress:
        pipeline_task = progress.add_task("Pipeline Progress", total=len(steps))
        
        for desc, step_func in steps:
            progress.update(pipeline_task, description=f"[bold cyan]Running: {desc}...[/bold cyan]")
            success = step_func(state)
            if not success:
                console.print(f"\n[error]❌ Pipeline halted due to error in: {desc}[/error]")
                return
            progress.advance(pipeline_task)
            
    console.print(Panel(
        f"[success]🎉 PIPELINE RUN COMPLETED SUCCESSFULLY! 🎉[/success]\n\n"
        f"[bold]Output Summary:[/bold]\n"
        f"  • Raw JSON: [dim]{state.data_dir}/raw_earthquakes.json[/dim]\n"
        f"  • Clean CSV: [dim]{state.data_dir}/cleaned_earthquakes.csv[/dim]\n"
        f"  • Clean JSON: [dim]{state.data_dir}/cleaned_earthquakes.json[/dim]\n"
        f"  • Visualizations: [dim]{state.visuals_dir}/[/dim] (3 PNGs)\n"
        f"  • Executive PDF: [dim]{state.reports_dir}/earthquake_report.pdf[/dim]",
        border_style="green"
    ))


def configure_settings(state: PipelineState):
    """Modifies pipeline execution variables."""
    console.print(Panel("[bold yellow]⚙ PIPELINE CONFIGURATION SETTINGS[/bold yellow]", border_style="yellow"))
    console.print(f"Current Config: [green]{state.date_range_str}[/green]\n")
    
    # Start Date
    start = Prompt.ask(
        "Enter start date (YYYY-MM-DD)", 
        default=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    )
    # End Date
    end = Prompt.ask(
        "Enter end date (YYYY-MM-DD)", 
        default=datetime.now().strftime("%Y-%m-%d")
    )
    
    # Min Magnitude
    min_mag = FloatPrompt.ask(
        "Enter minimum magnitude (e.g. 2.0, 4.5)", 
        default=2.5
    )
    
    # Validate date structure
    try:
        datetime.strptime(start, "%Y-%m-%d")
        datetime.strptime(end, "%Y-%m-%d")
        
        state.start_date = start
        state.end_date = end
        state.min_magnitude = min_mag
        
        # Reset state memory to force fresh fetching
        state.raw_data = None
        state.cleaned_df = None
        state.analysis_results = None
        state.chart_paths = None
        
        console.print("[success]✔ Settings updated successfully! Local cache invalidated for fresh run.[/success]")
    except ValueError:
        console.print("[error]❌ Error: Dates must be in YYYY-MM-DD format. Settings not saved.[/error]")


def main():
    state = PipelineState()
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        display_header()
        
        console.print(f"🌍 [bold]Query Target:[/bold] [green]{state.date_range_str}[/green]")
        status_raw = "[success]Loaded[/success]" if state.raw_data else "[dim]Not loaded[/dim]"
        status_clean = "[success]Loaded[/success]" if state.cleaned_df is not None else "[dim]Not loaded[/dim]"
        console.print(f"📁 [bold]In-Memory State:[/bold] Raw GeoJSON: {status_raw} | Cleaned DataFrame: {status_clean}\n")
        
        console.print("[bold]Available Options:[/bold]")
        console.print("  [bold cyan]1.[/bold cyan] Run Entire Pipeline (Fetch ➔ Report)")
        console.print("  [bold info]2.[/bold info] [Step 1] Fetch Raw USGS Data")
        console.print("  [bold info]3.[/bold info] [Step 2] Clean & Clean Outliers")
        console.print("  [bold info]4.[/bold info] [Step 3] Run Analysis Summary")
        console.print("  [bold info]5.[/bold info] [Step 4] Generate Visual Charts")
        console.print("  [bold info]6.[/bold info] [Step 5] Export Cleaned Datasets (CSV/JSON)")
        console.print("  [bold info]7.[/bold info] [Bonus] Compile PDF Executive Report")
        console.print("  [bold yellow]8.[/bold yellow] Change API Settings (Dates / Threshold)")
        console.print("  [bold red]9.[/bold red] Exit Console")
        
        choice = Prompt.ask("\nChoose an option", choices=[str(i) for i in range(1, 10)], default="1")
        
        if choice == "1":
            run_entire_pipeline(state)
            Prompt.ask("\nPress Enter to return to main menu...")
        elif choice == "2":
            run_fetch_step(state)
            Prompt.ask("\nPress Enter to return to main menu...")
        elif choice == "3":
            run_clean_step(state)
            Prompt.ask("\nPress Enter to return to main menu...")
        elif choice == "4":
            run_analyze_step(state)
            Prompt.ask("\nPress Enter to return to main menu...")
        elif choice == "5":
            run_visualize_step(state)
            Prompt.ask("\nPress Enter to return to main menu...")
        elif choice == "6":
            run_save_step(state)
            Prompt.ask("\nPress Enter to return to main menu...")
        elif choice == "7":
            run_pdf_report_step(state)
            Prompt.ask("\nPress Enter to return to main menu...")
        elif choice == "8":
            configure_settings(state)
            Prompt.ask("\nPress Enter to return to main menu...")
        elif choice == "9":
            console.print("\n[bold info]Thank you for using Seismic Pipeline Engine! Goodbye.[/bold info]")
            break

if __name__ == "__main__":
    main()
