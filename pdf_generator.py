import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, KeepTogether
from reportlab.pdfgen import canvas

# Colors
PRIMARY = HexColor("#2E3440")    # Nord Dark Slate
SECONDARY = HexColor("#4C566A")  # Nord Slate Gray
ACCENT = HexColor("#5E81AC")     # Nord Blue
MUTED = HexColor("#88C0D0")      # Nord Teal Light
TEXT_DARK = HexColor("#3B4252")  # Body Text Dark
BG_ALT = HexColor("#F8F9FA")     # Alternate row light gray
BORDER_COLOR = HexColor("#D8DEE9")

class NumberedCanvas(canvas.Canvas):
    """Canvas that implements a two-pass layout to compute total page numbers dynamically."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, page_count):
        # Page 1 is the cover page - do not draw header, footer, or page number
        if self._pageNumber == 1:
            return
            
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(SECONDARY)
        
        # Running Header
        self.drawString(54, 750, "USGS SEISMIC ACTIVITY ANALYSIS REPORT")
        self.setFont("Helvetica", 8)
        self.drawRightString(558, 750, datetime.now().strftime("%B %Y"))
        
        # Header line separator
        self.setStrokeColor(BORDER_COLOR)
        self.setLineWidth(0.5)
        self.line(54, 742, 558, 742)
        
        # Running Footer line separator
        self.line(54, 52, 558, 52)
        
        # Running Footer
        self.drawString(54, 40, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data source: USGS API")
        
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 40, page_text)
        
        self.restoreState()


def create_pdf_report(analysis_results: dict, chart_paths: dict, date_range: str, output_path: str = "reports/earthquake_report.pdf") -> str:
    """
    Compiles earthquake statistics, tables, and Matplotlib images into a professional PDF report.
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Setup document template
    # Margins: 0.75 in (54 pt) all around. Header at 750 is above top margin, footer at 40 is below bottom margin.
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=72,
        bottomMargin=72
    )
    
    # Styles
    base_styles = getSampleStyleSheet()
    
    styles = {
        'CoverTitle': ParagraphStyle(
            'CoverTitle',
            parent=base_styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=28,
            leading=34,
            textColor=PRIMARY,
            alignment=TA_CENTER,
            spaceAfter=15
        ),
        'CoverSubtitle': ParagraphStyle(
            'CoverSubtitle',
            parent=base_styles['Normal'],
            fontName='Helvetica',
            fontSize=13,
            leading=18,
            textColor=SECONDARY,
            alignment=TA_CENTER,
            spaceAfter=40
        ),
        'CoverMeta': ParagraphStyle(
            'CoverMeta',
            parent=base_styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=SECONDARY,
            alignment=TA_CENTER
        ),
        'H1': ParagraphStyle(
            'ReportH1',
            parent=base_styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            textColor=PRIMARY,
            spaceBefore=18,
            spaceAfter=10,
            keepWithNext=True
        ),
        'H2': ParagraphStyle(
            'ReportH2',
            parent=base_styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=17,
            textColor=SECONDARY,
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True
        ),
        'Body': ParagraphStyle(
            'ReportBody',
            parent=base_styles['BodyText'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=TEXT_DARK,
            spaceAfter=10
        ),
        'BodyBold': ParagraphStyle(
            'ReportBodyBold',
            parent=base_styles['BodyText'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=14,
            textColor=PRIMARY,
            spaceAfter=10
        ),
        'TableHeader': ParagraphStyle(
            'TableHeader',
            parent=base_styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=11,
            textColor=HexColor('#ECEFF4')
        ),
        'TableCell': ParagraphStyle(
            'TableCell',
            parent=base_styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=11,
            textColor=TEXT_DARK
        ),
        'TableCellBold': ParagraphStyle(
            'TableCellBold',
            parent=base_styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=11,
            textColor=PRIMARY
        )
    }
    
    story = []
    
    # ------------------ PAGE 1: COVER PAGE ------------------
    story.append(Spacer(1, 120))
    
    # Title
    story.append(Paragraph("Seismic Activity Analysis Report", styles['CoverTitle']))
    
    # Minimalist colored divider bar
    d_table = Table([[""]], colWidths=[200], rowHeights=[4])
    d_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), ACCENT),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(d_table)
    story.append(Spacer(1, 20))
    
    # Subtitle
    story.append(Paragraph("Interactive Pipeline Analysis of Global Earthquake Data", styles['CoverSubtitle']))
    
    story.append(Spacer(1, 150))
    
    # Metadata Block
    meta_text = f"""
    <b>Data Range Analyzed:</b> {date_range}<br/>
    <b>Total Events Processed:</b> {analysis_results['total_count']}<br/>
    <b>Maximum Recorded Magnitude:</b> {analysis_results['mag_stats'].get('max', 0.0)} M<br/>
    <b>Generated By:</b> Antigravity Pipeline Engine<br/>
    <b>Date:</b> {datetime.now().strftime('%B %d, %Y')}
    """
    story.append(Paragraph(meta_text, styles['CoverMeta']))
    story.append(PageBreak())
    
    # ------------------ PAGE 2: EXEC SUMMARY & DATA OVERVIEW ------------------
    story.append(Paragraph("Executive Summary", styles['H1']))
    
    summary_p1 = f"""
    This report contains analysis computed from data fetched dynamically from the <b>USGS Earthquake Hazards Program API</b>.
    A total of <b>{analysis_results['total_count']}</b> seismic events occurred during the selected window of <b>{date_range}</b>. 
    The maximum recorded earthquake had a magnitude of <b>{analysis_results['mag_stats'].get('max', 0.0)} M</b>.
    The average magnitude across all tracked events is <b>{analysis_results['mag_stats'].get('mean', 0.0):.2f} M</b> with a median of <b>{analysis_results['mag_stats'].get('median', 0.0):.2f} M</b>.
    """
    story.append(Paragraph(summary_p1, styles['Body']))
    
    # Descriptive Statistics Table
    story.append(Paragraph("Dataset Descriptive Statistics", styles['H2']))
    story.append(Paragraph("Below is a statistical breakdown of magnitude and depth indicators across all processed features.", styles['Body']))
    
    # Create descriptive table
    stats_data = [
        [
            Paragraph("Metric", styles['TableHeader']), 
            Paragraph("Magnitude (M)", styles['TableHeader']), 
            Paragraph("Depth (km)", styles['TableHeader'])
        ],
        [
            Paragraph("Count", styles['TableCellBold']), 
            Paragraph(f"{analysis_results['total_count']}", styles['TableCell']), 
            Paragraph(f"{analysis_results['total_count']}", styles['TableCell'])
        ],
        [
            Paragraph("Mean (Average)", styles['TableCellBold']), 
            Paragraph(f"{analysis_results['mag_stats'].get('mean', 0.0):.3f}", styles['TableCell']), 
            Paragraph(f"{analysis_results['depth_stats'].get('mean', 0.0):.2f}", styles['TableCell'])
        ],
        [
            Paragraph("Median", styles['TableCellBold']), 
            Paragraph(f"{analysis_results['mag_stats'].get('median', 0.0):.2f}", styles['TableCell']), 
            Paragraph(f"{analysis_results['depth_stats'].get('median', 0.0):.2f}", styles['TableCell'])
        ],
        [
            Paragraph("Minimum Value", styles['TableCellBold']), 
            Paragraph(f"{analysis_results['mag_stats'].get('min', 0.0):.2f}", styles['TableCell']), 
            Paragraph(f"{analysis_results['depth_stats'].get('min', 0.0):.2f}", styles['TableCell'])
        ],
        [
            Paragraph("Maximum Value", styles['TableCellBold']), 
            Paragraph(f"{analysis_results['mag_stats'].get('max', 0.0):.2f}", styles['TableCell']), 
            Paragraph(f"{analysis_results['depth_stats'].get('max', 0.0):.2f}", styles['TableCell'])
        ],
        [
            Paragraph("Standard Deviation", styles['TableCellBold']), 
            Paragraph(f"{analysis_results['mag_stats'].get('std', 0.0):.3f}", styles['TableCell']), 
            Paragraph(f"{analysis_results['depth_stats'].get('std', 0.0):.2f}", styles['TableCell'])
        ]
    ]
    
    # Format and add table style
    t_stats = Table(stats_data, colWidths=[150, 175, 175])
    ts = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('LINEBELOW', (0,0), (-1,0), 1.5, ACCENT),
        ('LINEBELOW', (0,-1), (-1,-1), 1.5, PRIMARY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,0), 5),
        ('TOPPADDING', (0,0), (-1,0), 5),
        ('BOTTOMPADDING', (0,1), (-1,-1), 4),
        ('TOPPADDING', (0,1), (-1,-1), 4),
    ])
    # Add alternating rows
    for i in range(1, len(stats_data)):
        if i % 2 == 0:
            ts.add('BACKGROUND', (0, i), (-1, i), BG_ALT)
            
    t_stats.setStyle(ts)
    story.append(t_stats)
    story.append(Spacer(1, 15))
    
    # Tsunami statistics
    tsunami_txt = f"""
    <b>Tsunami Warning Analysis:</b> Out of {analysis_results['total_count']} earthquakes, 
    <b>{analysis_results['tsunami_stats'].get('count_yes', 0)}</b> events triggered a tsunami warning 
    ({analysis_results['tsunami_stats'].get('percentage_yes', 0.0):.2f}% of all events). 
    The mean magnitude for events triggering tsunami warnings was <b>{analysis_results['tsunami_stats'].get('mean_mag_yes', 0.0):.2f} M</b>, 
    compared to <b>{analysis_results['tsunami_stats'].get('mean_mag_no', 0.0):.2f} M</b> for non-tsunami events.
    This highlights the strong relationship between earthquake magnitude and ocean displacement risk.
    """
    story.append(Paragraph(tsunami_txt, styles['Body']))
    
    # Magnitude Distribution Section
    story.append(Paragraph("Magnitude Distribution", styles['H2']))
    story.append(Paragraph("The chart below aggregates occurrences grouped by magnitude categories. Light and Minor tremors make up the vast majority of activities, which aligns with standard seismic frequency models.", styles['Body']))
    
    if "magnitude_distribution" in chart_paths:
        img_w, img_h = 4.2 * inch, 2.7 * inch
        story.append(Image(chart_paths["magnitude_distribution"], width=img_w, height=img_h))
        
    story.append(PageBreak())
    
    # ------------------ PAGE 3: DEEP TRENDS & MAP STATISTICS ------------------
    story.append(Paragraph("Depth and Physical Profiles", styles['H1']))
    story.append(Paragraph("Analyzing how earthquake focal depth corresponds with event magnitude allows researchers to understand fault-line friction dynamics. Deeper earthquakes typically occur at subduction zones.", styles['Body']))
    
    if "depth_vs_magnitude" in chart_paths:
        img_w, img_h = 4.2 * inch, 2.7 * inch
        story.append(Image(chart_paths["depth_vs_magnitude"], width=img_w, height=img_h))
        
    story.append(Spacer(1, 10))
    corr_val = analysis_results.get("correlation_mag_depth", 0.0)
    corr_desc = "no linear correlation"
    if abs(corr_val) > 0.5:
        corr_desc = "strong " + ("positive" if corr_val > 0 else "negative") + " linear correlation"
    elif abs(corr_val) > 0.2:
        corr_desc = "moderate " + ("positive" if corr_val > 0 else "negative") + " linear correlation"
        
    story.append(Paragraph(f"<b>Statistical Analysis:</b> The correlation between magnitude and depth is <b>{corr_val:.4f}</b>. This indicates <b>{corr_desc}</b> between an earthquake's magnitude and how deep it is recorded within the crust.", styles['Body']))
    
    # Daily Trend Chart
    story.append(Paragraph("Chronological Trends & Max Energy Peak", styles['H2']))
    
    if "activity_trend" in chart_paths:
        img_w, img_h = 4.2 * inch, 2.5 * inch
        story.append(Image(chart_paths["activity_trend"], width=img_w, height=img_h))
        
    story.append(PageBreak())
    
    # ------------------ PAGE 4: DETAILED REGIONS & SIGNIFICANT EVENTS ------------------
    story.append(Paragraph("Regional and Event Breakdowns", styles['H1']))
    
    # Top Regions Table
    story.append(Paragraph("Top 5 Most Active Regions", styles['H2']))
    
    region_headers = [
        [
            Paragraph("Region / Location", styles['TableHeader']), 
            Paragraph("Event Count", styles['TableHeader']), 
            Paragraph("Max Magnitude (M)", styles['TableHeader'])
        ]
    ]
    for r in analysis_results['top_regions'][:5]:
        region_headers.append([
            Paragraph(r['region'], styles['TableCellBold']),
            Paragraph(str(r['count']), styles['TableCell']),
            Paragraph(f"{r['max_mag']:.1f}", styles['TableCell'])
        ])
        
    t_regions = Table(region_headers, colWidths=[250, 125, 125])
    t_regions_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('LINEBELOW', (0,0), (-1,0), 1.5, ACCENT),
        ('LINEBELOW', (0,-1), (-1,-1), 1.5, PRIMARY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,0), 4),
        ('TOPPADDING', (0,0), (-1,0), 4),
        ('BOTTOMPADDING', (0,1), (-1,-1), 3),
        ('TOPPADDING', (0,1), (-1,-1), 3),
    ])
    for i in range(1, len(region_headers)):
        if i % 2 == 0:
            t_regions_style.add('BACKGROUND', (0, i), (-1, i), BG_ALT)
    t_regions.setStyle(t_regions_style)
    story.append(t_regions)
    story.append(Spacer(1, 15))
    
    # Strongest Earthquakes Table
    story.append(Paragraph("Top 5 Strongest Seismic Events Recorded", styles['H2']))
    
    strong_headers = [
        [
            Paragraph("Date & Time (UTC)", styles['TableHeader']),
            Paragraph("Magnitude (M)", styles['TableHeader']),
            Paragraph("Location", styles['TableHeader']),
            Paragraph("Depth (km)", styles['TableHeader']),
            Paragraph("Felt Reports", styles['TableHeader'])
        ]
    ]
    for ev in analysis_results['strongest_events']:
        # Format time to look cleaner in table
        t_clean = ev['time_readable'].replace(" UTC", "")
        strong_headers.append([
            Paragraph(t_clean, styles['TableCell']),
            Paragraph(f"<b>{ev['mag']:.1f}</b>", styles['TableCellBold']),
            Paragraph(ev['place'], styles['TableCell']),
            Paragraph(f"{ev['depth']:.1f}", styles['TableCell']),
            Paragraph(str(ev['felt']), styles['TableCell'])
        ])
        
    t_strong = Table(strong_headers, colWidths=[110, 75, 185, 65, 65])
    t_strong_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('LINEBELOW', (0,0), (-1,0), 1.5, ACCENT),
        ('LINEBELOW', (0,-1), (-1,-1), 1.5, PRIMARY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,0), 4),
        ('TOPPADDING', (0,0), (-1,0), 4),
        ('BOTTOMPADDING', (0,1), (-1,-1), 3),
        ('TOPPADDING', (0,1), (-1,-1), 3),
    ])
    for i in range(1, len(strong_headers)):
        if i % 2 == 0:
            t_strong_style.add('BACKGROUND', (0, i), (-1, i), BG_ALT)
    t_strong.setStyle(t_strong_style)
    story.append(t_strong)
    story.append(Spacer(1, 20))
    
    # Pipeline info / signature
    story.append(Paragraph("Pipeline Flow Verification", styles['H2']))
    story.append(Paragraph("This PDF report marks the final step in the pipeline. The flow verified for this dataset consists of: (1) Fetching from USGS JSON API endpoint, (2) Clean & Flat-mapping using Pandas, (3) Generating visualizations with Matplotlib, (4) Statistical calculations, and (5) Exporting to PDF (ReportLab) & JSON/CSV files locally.", styles['Body']))
    
    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    return output_path
