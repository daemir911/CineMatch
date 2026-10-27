"""
Script to generate the comprehensive CineMatch Project Technology & Architecture Guide PDF.
Structured into an exact 9-page professional technical dossier:
- Page 1: Executive Summary, System Highlights & 30-Second Elevator Pitch
- Page 2: Complete Languages Inventory (Python, JS, HTML5, CSS3, SVG, Shell)
- Page 3: Applications, Frameworks & Libraries Stack (Backend, ML, NLP, Tools)
- Page 4: External APIs & CloudFront Edge DNS Socket Patching
- Page 5: Internal REST API Specifications (All 10 Endpoints & Payloads)
- Page 6: Multi-Source Datasets & 3-Tier Zero-Broken-Poster Architecture
- Page 7: Machine Learning Algorithms, Mathematical Formulas & Blending
- Page 8: Technical Viva & Interview Guide (2-Minute Script & Questions 1-5)
- Page 9: Questions 6-10, Codebase File Reference & Final Presentation Tips
"""
import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PDF = BASE_DIR / "CineMatch_Project_Architecture_and_Technologies_Guide.pdf"

# =========================================================================
# COLOR PALETTE (Modern Slate & Crimson Theme)
# =========================================================================
PRIMARY = colors.HexColor("#0F172A")       # Deep Slate / Obsidian
PRIMARY_LIGHT = colors.HexColor("#1E293B") # Secondary Slate
ACCENT = colors.HexColor("#E50914")        # Netflix Crimson Accent
ACCENT_MUTED = colors.HexColor("#DC2626")  # Crimson Red
GOLD = colors.HexColor("#D97706")          # Amber Gold
TEXT_DARK = colors.HexColor("#0F172A")     # Body dark text
TEXT_MUTED = colors.HexColor("#475569")    # Gray caption text
BG_LIGHT = colors.HexColor("#F8FAFC")      # Off-white / light slate card background
BG_ALT_ROW = colors.HexColor("#F1F5F9")    # Table alternate row
BORDER_COLOR = colors.HexColor("#CBD5E1")  # Border gray
SUCCESS_GREEN = colors.HexColor("#059669") # Green badge

# =========================================================================
# NUMBERED CANVAS (Header & Footer on all pages except cover)
# =========================================================================
class NumberedCanvas(canvas.Canvas):
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
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        # Top Header (Only on pages > 1)
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(ACCENT)
            self.drawString(40, 756, "CINEMATCH")
            self.setFont("Helvetica", 8)
            self.setFillColor(TEXT_MUTED)
            self.drawString(100, 756, "- Universal AI Hybrid Movie Recommender - Technology & Architecture Guide")
            
            # Subtle header dividing line
            self.setStrokeColor(BORDER_COLOR)
            self.setLineWidth(0.6)
            self.line(40, 748, 572, 748)

            # Footer
            self.line(40, 40, 572, 40)
            self.setFont("Helvetica", 8)
            self.setFillColor(TEXT_MUTED)
            self.drawString(40, 28, "Confidential & Educational - Prepared for Presentations, Vivas & Code Walkthroughs")
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(572, 28, page_text)

        self.restoreState()

# =========================================================================
# STYLES SETUP
# =========================================================================
def setup_styles():
    styles = getSampleStyleSheet()

    # Document Cover / Title Styles
    styles.add(ParagraphStyle(
        name="DocTitle",
        fontName="Helvetica-Bold",
        fontSize=23,
        leading=28,
        textColor=PRIMARY,
        spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        name="DocSubtitle",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=ACCENT,
        spaceAfter=10
    ))
    styles.add(ParagraphStyle(
        name="DocMeta",
        fontName="Helvetica",
        fontSize=8.5,
        leading=13,
        textColor=TEXT_MUTED,
        spaceAfter=12
    ))

    # Section Headings
    styles.add(ParagraphStyle(
        name="SecHeading1",
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=PRIMARY,
        spaceBefore=0,
        spaceAfter=6,
        keepWithNext=True
    ))
    styles.add(ParagraphStyle(
        name="SecHeading2",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=ACCENT_MUTED,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    ))

    # Body Text & List Items
    styles['Normal'].fontName = "Helvetica"
    styles['Normal'].fontSize = 8.5
    styles['Normal'].leading = 12.5
    styles['Normal'].textColor = TEXT_DARK
    styles['Normal'].spaceAfter = 5

    styles.add(ParagraphStyle(
        name="BodyTextCustom",
        fontName="Helvetica",
        fontSize=8.5,
        leading=12.5,
        textColor=TEXT_DARK,
        spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name="BulletCustom",
        fontName="Helvetica",
        fontSize=8.2,
        leading=12,
        textColor=TEXT_DARK,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3
    ))

    # Callout / Box Styles
    styles.add(ParagraphStyle(
        name="CalloutText",
        fontName="Helvetica",
        fontSize=8.2,
        leading=12,
        textColor=PRIMARY_LIGHT
    ))
    styles.add(ParagraphStyle(
        name="CalloutTitle",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=ACCENT,
        spaceAfter=2
    ))

    # Table Text Styles
    styles.add(ParagraphStyle(
        name="TableHeader",
        fontName="Helvetica-Bold",
        fontSize=8.2,
        leading=11,
        textColor=colors.white,
        alignment=0
    ))
    styles.add(ParagraphStyle(
        name="TableCell",
        fontName="Helvetica",
        fontSize=7.8,
        leading=10.8,
        textColor=TEXT_DARK
    ))
    styles.add(ParagraphStyle(
        name="TableCellBold",
        fontName="Helvetica-Bold",
        fontSize=7.8,
        leading=10.8,
        textColor=PRIMARY
    ))

    return styles

def create_callout(title, text, styles, accent_color=ACCENT, width=532):
    """Creates a stylized callout / highlight box."""
    content = [
        Paragraph(f"<b>{title}</b>", styles['CalloutTitle']),
        Spacer(1, 2),
        Paragraph(text, styles['CalloutText'])
    ]
    t = Table([[content]], colWidths=[width])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('LINEBEFORE', (0,0), (0,-1), 3.5, accent_color),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    return t

def create_table(header_data, rows_data, col_widths, styles, pad_v=3.5):
    """Builds a formatted corporate table with alternating rows."""
    table_content = []
    
    # Header row
    hdr_row = [Paragraph(f"<b>{col}</b>", styles['TableHeader']) for col in header_data]
    table_content.append(hdr_row)
    
    # Data rows
    for r in rows_data:
        row_cells = []
        for cell_idx, val in enumerate(r):
            if isinstance(val, str):
                if cell_idx == 0:
                    row_cells.append(Paragraph(val, styles['TableCellBold']))
                else:
                    row_cells.append(Paragraph(val, styles['TableCell']))
            else:
                row_cells.append(val)
        table_content.append(row_cells)

    t = Table(table_content, colWidths=col_widths, repeatRows=1)
    
    ts = [
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), pad_v),
        ('BOTTOMPADDING', (0, 0), (-1, -1), pad_v),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
    ]
    
    for i in range(1, len(table_content)):
        if i % 2 == 0:
            ts.append(('BACKGROUND', (0, i), (-1, i), BG_ALT_ROW))
        else:
            ts.append(('BACKGROUND', (0, i), (-1, i), colors.white))
            
    t.setStyle(TableStyle(ts))
    return t

# =========================================================================
# DOCUMENT STORY BUILDER
# =========================================================================
def build_pdf():
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=44,
        bottomMargin=44
    )

    styles = setup_styles()
    story = []

    # =====================================================================
    # PAGE 1: TITLE BANNER, EXECUTIVE SUMMARY, VALUE PROPOSITION
    # =====================================================================
    banner_data = [[
        Paragraph("<b>CINEMATCH AI - COMPLETE ARCHITECTURE & TECH STACK GUIDE</b>", ParagraphStyle(
            name="BannerHeader", fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.white
        )),
        Paragraph("<b>VERSION 2.0</b>", ParagraphStyle(
            name="BannerVer", fontName="Helvetica-Bold", fontSize=8.5, textColor=GOLD, alignment=2
        ))
    ]]
    banner_table = Table(banner_data, colWidths=[432, 100])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), PRIMARY),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("CineMatch: Universal AI Hybrid Movie Recommender System", styles['DocTitle']))
    story.append(Paragraph("Complete Technical Reference, Stack Inventory, Algorithms, APIs & Viva Explanation Guide", styles['DocSubtitle']))
    story.append(Paragraph(
        "<b>Catalog Size:</b> 13,906 Verified Films &nbsp;|&nbsp; "
        "<b>Deployment:</b> Full-Stack Web Application (Localhost:5000 / Production Ready)<br/>"
        "<b>Core Architecture:</b> Dual-Engine Machine Learning (Content-Based NLP + Collaborative SVD Matrix Factorization)<br/>"
        "<b>Purpose:</b> Comprehensive reading material to master every language, library, API, dataset, and mathematical algorithm used in the project, enabling effortless, authoritative project presentations, vivas, and technical interviews.",
        styles['DocMeta']
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceBefore=0, spaceAfter=8))

    story.append(Paragraph("1. Executive Summary & Core Value Proposition", styles['SecHeading1']))
    story.append(Paragraph(
        "<b>CineMatch</b> is a production-grade, full-stack movie discovery platform powered by a <b>Dual-Engine Machine Learning Recommender</b>. "
        "It dynamically synthesizes <b>Content-Based Filtering</b> (plot tags, keywords, cast, and director metadata) with <b>Collaborative Filtering</b> "
        "(MovieLens latent matrix factorization using SVD). Rather than forcing users into a static recommendation black-box, CineMatch introduces a real-time "
        "<b>Hybrid Balance Slider (&alpha; &isin; [0.0, 1.0])</b>, empowering users to adjust how much they value plot/thematic similarity versus collective audience ratings.",
        styles['BodyTextCustom']
    ))

    summary_headers = ["Key Dimension", "Legacy Recommenders / Basic 5k Projects", "CineMatch Universal Platform"]
    summary_rows = [
        ["Catalog Coverage", "4,803 static films (TMDB 5k only)", "13,906 curated movies spanning classic cinema to 2026 releases"],
        ["Recommendation Core", "Pure cosine similarity on plot keywords only", "Dual-Engine Hybrid: PorterStemmer NLP + SVD Latent Collaborative Factors"],
        ["User Control", "Static Top-10 list with zero user adjustment", "Interactive alpha slider (adjusts Content vs Audience preference weight in real time)"],
        ["Poster Reliability", "Broken image icons whenever TMDB lacks poster", "3-Tier Fallback: 99.0% Real Posters + 1.0% Dynamic SVG + 0% Broken Images"],
        ["Search & Typo Handling", "Strict exact substring (fails on small typos)", "Difflib fuzzy matching ('dark nite' -&gt; 'The Dark Knight') with live fallback"],
        ["Uncataloged Movies", "Fails completely with 404 error", "Universal On-the-Fly Discovery: Live TMDB/Wiki vectorization in RAM"],
        ["Explainability", "Opaque score or no reasoning provided", "Explainable AI (XAI) rationale chips (Director, Cast, Genre match reasons)"]
    ]
    story.append(create_table(summary_headers, summary_rows, [110, 195, 227], styles, pad_v=3.2))
    story.append(Spacer(1, 8))

    story.append(create_callout(
        "HOW TO EXPLAIN THE CORE CONCEPT (THE 30-SECOND ELEVATOR PITCH)",
        "<i>\"CineMatch is a full-stack movie recommendation system built with Python, Flask, and Vanilla JavaScript. "
        "Unlike basic projects that only look at movie plots, CineMatch uses a dual-engine machine learning algorithm that blends content metadata "
        "with collaborative matrix factorization across 13,906 movies. It features a Netflix-style dark interface, 100% guaranteed working posters "
        "through a 3-tier fallback architecture, typo-tolerant search, and can even recommend brand-new uncataloged films on the fly using live vectorization.\"</i>",
        styles,
        accent_color=ACCENT
    ))
    story.append(PageBreak())

    # =====================================================================
    # PAGE 2: COMPLETE LANGUAGES INVENTORY
    # =====================================================================
    story.append(Paragraph("2. All Programming & Scripting Languages Used", styles['SecHeading1']))
    story.append(Paragraph(
        "A major question in any technical interview or viva is: <i>\"Which programming languages did you use, and exactly where is each language utilized in the codebase?\"</i> "
        "Here is the complete inventory of all 6 languages implemented across CineMatch:",
        styles['BodyTextCustom']
    ))

    lang_headers = ["Language", "Where Used (Exact Files)", "Primary Purpose & Implementation Details"]
    lang_rows = [
        [
            "Python<br/>(3.10 - 3.14)",
            "app.py<br/>train.py<br/>config.py<br/>network_utils.py<br/>poster_service.py<br/>poster_placeholder.py<br/>scripts/build_catalog.py<br/>scripts/update_catalog.py<br/>scripts/verify_posters.py<br/>notebook/model_building.ipynb",
            "<b>The Core Engine:</b> Powers the backend REST API (Flask), ML data pipelines, NLP stemming, matrix factorizations, "
            "poster caching, low-level socket DNS resolution, and automated dataset merging.<br/>"
            "<i>Why chosen:</i> Rich scientific ecosystem (Scikit-Learn, SciPy, Surprise, Pandas, NLTK) and rapid API prototyping with Flask."
        ],
        [
            "JavaScript<br/>(Modern ES6+)",
            "static/js/app.js<br/>static/js/api.js<br/>static/js/ui.js",
            "<b>Frontend Interactivity:</b> Pure modular vanilla ES6+ (no heavy framework overhead). "
            "Handles asynchronous fetch calls, search debouncing, keyboard shortcuts (/ and Esc), modal popup dialogs, "
            "DOM card rendering, and interactive slider events.<br/>"
            "<i>Why chosen:</i> Native in-browser execution, zero compile/build steps, instant 60fps responsiveness."
        ],
        [
            "HTML5<br/>(Semantic)",
            "templates/index.html",
            "<b>Application Structure:</b> Semantic document structure featuring header, main, section, nav, dialog, "
            "and ARIA accessibility attributes. Employs responsive meta viewports, Google Fonts integration, and zero external widget dependencies.<br/>"
            "<i>Why chosen:</i> Standard web markup providing clean DOM hierarchy and accessibility."
        ],
        [
            "CSS3<br/>(Custom Design)",
            "static/css/style.css",
            "<b>Design System:</b> High-end dark theme inspired by Netflix and Letterboxd. Uses CSS custom properties (:root variables), "
            "Flexbox, CSS Grid, frosted-glass blurs (backdrop-filter: blur(20px)), keyframe shimmer loaders, and responsive mobile breakpoints.<br/>"
            "<i>Why chosen:</i> Complete visual control and sleek aesthetic without the bloat of Bootstrap or Tailwind."
        ],
        [
            "SVG<br/>(Scalable Vector)",
            "poster_placeholder.py<br/>templates/index.html",
            "<b>Dynamic Graphics:</b> Programmatically generated vector artwork. Powers the Tier 3 fallback poster engine "
            "(rendering film clapperboards, gradient backgrounds, wrapped typography, and genre badges) and crisp UI icons.<br/>"
            "<i>Why chosen:</i> Infinitely scalable, ultra-lightweight text format, renders cleanly on any device screen."
        ],
        [
            "Shell & Batch<br/>(CMD / Bash)",
            "run.bat<br/>run.sh",
            "<b>DevOps & Bootstrapping:</b> Automated launch scripts for Windows (Batch) and macOS/Linux (Bash) that detect virtual environments, "
            "check dependencies, and bootstrap the local Flask development server in one double-click.<br/>"
            "<i>Why chosen:</i> Zero-friction startup for non-technical users and cross-platform convenience."
        ]
    ]
    story.append(create_table(lang_headers, lang_rows, [85, 145, 302], styles, pad_v=4.0))
    story.append(Spacer(1, 10))

    story.append(create_callout(
        "INTERVIEW TALKING POINT: ARCHITECTURAL SEPARATION OF CONCERNS",
        "<i>\"We strictly separated concerns across languages: Python handles heavy linear algebra and data ingestion on the server, "
        "while modern ES6 JavaScript manages the client lifecycle asynchronously. This decoupled design ensures the UI remains silky smooth "
        "and never freezes during complex recommendation computations.\"</i>",
        styles,
        accent_color=PRIMARY
    ))
    story.append(PageBreak())

    # =====================================================================
    # PAGE 3: SOFTWARE, APPS, FRAMEWORKS & LIBRARIES STACK
    # =====================================================================
    story.append(Paragraph("3. Applications, Frameworks, and Libraries (The Full Stack)", styles['SecHeading1']))
    story.append(Paragraph(
        "CineMatch combines industry-standard Python libraries for machine learning, data engineering, and web serving. Below is the detailed breakdown "
        "categorized by architectural tier:",
        styles['BodyTextCustom']
    ))

    story.append(Paragraph("A. Backend Web Framework & Network Stack", styles['SecHeading2']))
    backend_headers = ["Package / Module", "Version", "Where Used", "Technical Role & Why Used"]
    backend_rows = [
        ["Flask", ">= 3.0.0", "app.py", "Lightweight WSGI web framework exposing RESTful endpoints, serving JSON payloads, and streaming dynamic SVG cards."],
        ["Flask-CORS", ">= 4.0.0", "app.py", "Cross-Origin Resource Sharing middleware enabling secure cross-origin API querying."],
        ["python-dotenv", ">= 1.0.0", "config.py", "Loads environment secrets from .env (e.g. TMDB_API_KEY) into os.environ with fallback defaults."],
        ["requests", ">= 2.31.0", "app.py<br/>poster_service.py<br/>scripts/*.py", "Synchronous HTTP client with session pooling and timeout safeguards to communicate with TMDB and Wikipedia."],
        ["socket (Built-in)", "Standard Lib", "network_utils.py", "Low-level socket interface monkey-patched to bypass ISP DNS blocking of TMDB by routing directly to AWS CloudFront edge IPs."],
        ["difflib (Built-in)", "Standard Lib", "app.py", "Gestalt pattern matching library (SequenceMatcher) powering instant typo-tolerant autocomplete search."]
    ]
    story.append(create_table(backend_headers, backend_rows, [95, 55, 120, 262], styles, pad_v=2.8))
    story.append(Spacer(1, 6))

    story.append(Paragraph("B. Machine Learning, NLP & Data Engineering Stack", styles['SecHeading2']))
    ml_headers = ["Package / Library", "Version", "Where Used", "Technical Role & Implementation Details"]
    ml_rows = [
        ["pandas", ">= 2.0.0", "train.py<br/>app.py<br/>scripts/*.py", "Tabular data engineering: merges 5 CSV datasets, cleans nulls, parses stringified JSON, and manages catalog DataFrame."],
        ["numpy", ">= 1.24.0", "train.py<br/>app.py", "Vectorized linear algebra: performs sub-5ms cosine dot products, matrix slicing, min-max score normalizations."],
        ["scipy (scipy.sparse)", ">= 1.10.0", "train.py<br/>app.py", "Stores high-dimensional feature matrices (13,906 x 6,000) in Compressed Sparse Row (CSR) format, saving over 90% RAM."],
        ["scikit-learn", ">= 1.3.0", "train.py<br/>app.py", "CountVectorizer (6,000 features, stop-words), normalize (L2 unit vector scaling), TruncatedSVD fallback, and Ridge regression."],
        ["nltk (PorterStemmer)", ">= 3.8.0", "train.py<br/>app.py", "Natural Language Toolkit: stems tokenized words (e.g. 'action', 'acting' -&gt; 'actor') so inflected variants match identical root vectors."],
        ["scikit-surprise", ">= 1.1.4", "train.py", "Collaborative filtering library: executes SVD with 20 latent factors on 100,000+ MovieLens ratings (achieves RMSE &lt; 0.88)."],
        ["joblib", ">= 1.3.0", "train.py<br/>app.py", "Fast binary persistence for serializing and loading trained models: movies.pkl, vectors.pkl, vectorizer.pkl, collab_factors.pkl."],
        ["reportlab", ">= 5.1.0", "scripts/*.py", "Programmatic PDF document generation engine used to compile this exact architectural guide."]
    ]
    story.append(create_table(ml_headers, ml_rows, [95, 55, 115, 267], styles, pad_v=2.8))
    story.append(Spacer(1, 6))

    story.append(Paragraph("C. Developer, Exploration & Deployment Tools", styles['SecHeading2']))
    dev_headers = ["Tool / Application", "Environment", "Purpose in Project Lifecycle"]
    dev_rows = [
        ["Jupyter Notebook / ipykernel", "Development / Research", "Used in notebook/model_building.ipynb for exploratory data analysis (EDA), cleaning prototypes, and baseline validation."],
        ["Python Virtual Environment (venv)", "Runtime Environment", "Provides clean dependency isolation preventing library version collisions on host developer machines."],
        ["Visual Studio Code / Cursor", "IDE / Code Editor", "Primary development environment for writing Python backend, client JS, HTML templates, and debugging."]
    ]
    story.append(create_table(dev_headers, dev_rows, [140, 110, 282], styles, pad_v=2.8))
    story.append(PageBreak())

    # =====================================================================
    # PAGE 4: EXTERNAL APIS & NETWORK INTEGRATION
    # =====================================================================
    story.append(Paragraph("4. External APIs Consumed & Network Resiliency", styles['SecHeading1']))
    story.append(Paragraph(
        "A critical question in presentations is: <i>\"Which third-party APIs are you consuming, how do you handle rate-limits, and what happens when an API is unreachable?\"</i> "
        "CineMatch integrates two major external web APIs with deep resilience layers:",
        styles['BodyTextCustom']
    ))

    ext_api_headers = ["External API", "Endpoints Used", "Where Used", "Why & How It Is Used"]
    ext_api_rows = [
        [
            "The Movie Database<br/>(TMDB) API v3",
            "1. /3/movie/{id}<br/>"
            "2. /3/search/movie<br/>"
            "3. /3/discover/movie<br/>"
            "CDN: image.tmdb.org/t/p/w500",
            "poster_service.py<br/>"
            "app.py<br/>"
            "scripts/build_catalog.py<br/>"
            "scripts/update_catalog.py",
            "<b>Metadata & Poster Extraction:</b> Fetches official movie release dates, high-resolution posters (w500), "
            "backdrop stills, and ratings. Powers on-the-fly search for movies outside the catalog and batch ingestion of 2016-2026 releases.<br/>"
            "<i>Fallback:</i> Pre-configured with a reliable demo key so the app works instantly without manual user registration."
        ],
        [
            "Wikipedia / MediaWiki<br/>REST API",
            "1. en.wikipedia.org/w/api.php<br/>"
            "2. /api/rest_v1/page/summary/{title}",
            "poster_service.py<br/>"
            "app.py",
            "<b>Tier 2 Universal Fallback:</b> When obscure, independent, or foreign movies lack TMDB coverage, CineMatch queries Wikipedia's REST API "
            "to retrieve plot summaries, release years, and page thumbnail images for seamless recommendation."
        ]
    ]
    story.append(create_table(ext_api_headers, ext_api_rows, [95, 140, 110, 187], styles, pad_v=5.0))
    story.append(Spacer(1, 12))

    story.append(create_callout(
        "PRODUCTION ENGINEERING HIGHLIGHT: AWS CLOUDFRONT DNS SOCKET PATCHING (network_utils.py)",
        "In many countries, colleges, and enterprise networks, local ISPs or campus firewalls poison or block DNS lookups for <code>api.themoviedb.org</code>. "
        "Standard Python requests would crash with <code>ConnectionError: [Errno 11001] getaddrinfo failed</code>.<br/><br/>"
        "To solve this at the root level, CineMatch includes <code>network_utils.py</code>, which intercepts Python's low-level <code>socket.getaddrinfo</code> "
        "function at runtime. Whenever host <code>api.themoviedb.org</code> is queried, the socket patch automatically maps the domain to verified "
        "global AWS CloudFront anycast IPs (e.g. <code>99.84.152.8</code>, <code>13.224.245.44</code>) in a round-robin rotation. "
        "This completely bypasses local DNS failures and guarantees 100% network uptime for poster fetching and live discovery.",
        styles,
        accent_color=GOLD
    ))
    story.append(Spacer(1, 10))

    story.append(create_callout(
        "PARALLEL THREAD POOLING & DISK CACHING (poster_service.py)",
        "To avoid hitting TMDB rate limits (40 requests per 10 seconds), <code>poster_service.py</code> implements a two-layer cache:<br/>"
        "1. <b>In-Memory Dictionary Cache:</b> Sub-millisecond lookup for repeatedly browsed titles.<br/>"
        "2. <b>Persistent Disk Cache (data/poster_cache.json):</b> Persists poster URLs across server restarts.<br/>"
        "3. <b>Concurrent ThreadPoolExecutor:</b> Employs up to 8 parallel workers with a strict 3.5-second timeout, preventing network stalls from blocking the main Flask thread.",
        styles,
        accent_color=PRIMARY
    ))
    story.append(PageBreak())

    # =====================================================================
    # PAGE 5: INTERNAL REST API SPECIFICATIONS
    # =====================================================================
    story.append(Paragraph("5. Internal CineMatch REST API Specifications", styles['SecHeading1']))
    story.append(Paragraph(
        "The Flask backend acts as a microservice providing 10 dedicated RESTful endpoints consumed by the vanilla JavaScript client (<code>static/js/api.js</code>). "
        "All data endpoints return standard JSON payloads, while <code>/api/placeholder</code> streams SVG XML:",
        styles['BodyTextCustom']
    ))

    int_api_headers = ["Endpoint", "Verb", "Parameters", "Description & Client Consumer"]
    int_api_rows = [
        ["/", "GET", "None", "Serves the single-page application HTML interface (templates/index.html)."],
        ["/api/movies", "GET", "None", "Returns lightweight cached array of all 13,906 movies (id, title, year, rating) for client-side search indexing."],
        ["/api/search_titles", "GET", "q (string)", "Typo-tolerant autocomplete endpoint blending catalog substring search, difflib fuzzy matching, and live TMDB discovery."],
        ["/api/recommend", "GET", "movie (str/int)<br/>n (int, def:12)<br/>alpha (float, def:0.6)", "Core Recommender: Computes dynamic hybrid scores across content and collaborative embeddings; returns top-N movies with 'Why Recommended' rationales."],
        ["/api/movie/<id>", "GET", "id or title", "Returns rich metadata (overview, director, cast chips, backdrop) plus Top 6 'More Like This' similar movies for modal display."],
        ["/api/browse", "GET", "genre, year_min, year_max,<br/>min_rating, sort, page, limit", "Multi-criteria catalog exploration engine supporting pagination, genre filtering, decade/era filtering, and multi-field sorting."],
        ["/api/popular", "GET", "limit (int, def:16)", "Returns trending audience favorite movies sorted by vote counts and popularity metrics."],
        ["/api/top_rated", "GET", "limit (int, def:16)", "Returns critically acclaimed films with minimum vote thresholds to avoid low-vote statistical noise."],
        ["/api/genres", "GET", "None", "Returns distinct genres with exact film counts across the 13,906 catalog for dynamic pill filters."],
        ["/api/placeholder", "GET", "title, year, genre", "Generates and streams standalone high-res SVG poster cards with dynamic title wrapping and badges for zero broken images."]
    ]
    story.append(create_table(int_api_headers, int_api_rows, [95, 45, 125, 267], styles, pad_v=3.2))
    story.append(Spacer(1, 10))

    story.append(create_callout(
        "REST API DESIGN BEST PRACTICES IMPLEMENTED IN CINEMATCH",
        "&bull; <b>Idempotency & Caching:</b> Static assets and generated SVG posters include <code>Cache-Control: public, max-age=86400</code> headers.<br/>"
        "&bull; <b>Defensive Parameter Parsing:</b> All query inputs (e.g. <code>alpha</code>, <code>n</code>, <code>page</code>) are strictly bounded to valid ranges (alpha &isin; [0, 1], n &isin; [1, 48]) preventing server 500 crashes.<br/>"
        "&bull; <b>Decoupled Architecture:</b> The Flask API returns clean JSON, making it trivially easy to connect a mobile app (Flutter/React Native) in the future without changing the backend.",
        styles,
        accent_color=ACCENT
    ))
    story.append(PageBreak())

    # =====================================================================
    # PAGE 6: DATASETS & 3-TIER POSTER ARCHITECTURE
    # =====================================================================
    story.append(Paragraph("6. Multi-Source Datasets & The 3-Tier Poster Architecture", styles['SecHeading1']))
    story.append(Paragraph(
        "A standout engineering accomplishment of CineMatch is how it expanded beyond the standard 4,803-movie Kaggle dataset into a robust "
        "<b>13,906-film unified catalog</b> via automated ETL scripts (<code>scripts/build_catalog.py</code>):",
        styles['BodyTextCustom']
    ))

    data_headers = ["Dataset Source", "Raw File Inside data/", "Records", "Role in Recommendation Pipeline"]
    data_rows = [
        ["TMDB 5,000 Movies & Credits", "tmdb_5000_movies.csv<br/>tmdb_5000_credits.csv", "4,803 movies", "Foundational metadata: rich plot overviews, full crew/director info, cast listings, production budgets, and keyword tags."],
        ["Extended TMDB 10,000+", "tmdb_10k_movies.csv", "10,866 movies", "Expanded historical depth: classic cinema, international cinema, and releases from 1960 through 2015."],
        ["Modern Blockbuster Releases", "Fetched via TMDB Discover API", "~1,000+ movies", "Fresh releases from 2016-2026: Oppenheimer, Dune 1 & 2, Barbie, Spider-Verse, Everything Everywhere All at Once, Avatar 2, etc."],
        ["Bollywood & World Hits", "bollywood_movies.csv", "~800+ movies", "Cultural enrichment: high-rated Hindi and global cinematic milestones to avoid Western-only bias."],
        ["MovieLens 100k Ratings", "ratings.csv<br/>links.csv", "100,000+ ratings<br/>across 610 users", "Collaborative Filtering: user rating matrix factorized into 20 latent item factors; linked to TMDB IDs via links.csv."]
    ]
    story.append(create_table(data_headers, data_rows, [115, 125, 75, 217], styles, pad_v=3.5))
    story.append(Spacer(1, 10))

    story.append(Paragraph("The 3-Tier Poster Architecture: Achieving 100% Poster Reliability", styles['SecHeading2']))
    story.append(Paragraph(
        "In basic movie projects, 15% to 30% of movie cards render with broken image icons due to missing TMDB poster paths. "
        "CineMatch eliminates this completely through a strict 3-tier hierarchy audited via <code>scripts/verify_posters.py</code>:",
        styles['BodyTextCustom']
    ))
    story.append(Paragraph("[1] <b>Tier 1 (High-Res TMDB):</b> Looks up pre-cached official URLs via tmdb_id or title+year matching (13,762 movies = 99.0%).", styles['BulletCustom']))
    story.append(Paragraph("[2] <b>Tier 2 (Alternate Media):</b> Queries Wikipedia REST summaries and OMDb thumbnails when TMDB lacks coverage.", styles['BulletCustom']))
    story.append(Paragraph("[3] <b>Tier 3 (Dynamic SVG Generator):</b> When no image exists anywhere, poster_placeholder.py generates a standalone, branded dark SVG card with title, release year, and genre badge (144 movies = 1.0%).", styles['BulletCustom']))
    story.append(Paragraph("[4] <b>Frontend Failsafe:</b> Native HTML onerror handlers catch any CDN network dropouts and automatically redirect to /api/placeholder.", styles['BulletCustom']))
    story.append(Spacer(1, 8))

    audit_headers = ["Audit Metric", "Exact Value", "Percentage", "Status"]
    audit_rows = [
        ["Total Catalog Movies", "13,906", "100.0%", "Verified in data/movies_catalog.csv"],
        ["Real Posters (TMDB / Wikimedia)", "13,762", "99.0%", "Pre-cached in data/poster_cache.json"],
        ["Clean Dynamic SVG Fallbacks", "144", "1.0%", "Rendered on-the-fly via /api/placeholder"],
        ["Broken / Missing Poster Failures", "0", "0.0%", "Audited via scripts/verify_posters.py"]
    ]
    story.append(create_table(audit_headers, audit_rows, [160, 80, 80, 212], styles, pad_v=3.0))
    story.append(PageBreak())

    # =====================================================================
    # PAGE 7: MACHINE LEARNING ALGORITHMS & MATHEMATICAL FORMULAS
    # =====================================================================
    story.append(Paragraph("7. Machine Learning Architecture & Algorithmic Foundations", styles['SecHeading1']))
    story.append(Paragraph(
        "To explain the recommendation algorithms with complete confidence, understand the mathematics behind the dual engines:",
        styles['BodyTextCustom']
    ))

    story.append(Paragraph("A. Engine 1: Content-Based Feature Vectorization", styles['SecHeading2']))
    story.append(Paragraph(
        "<b>1. Metadata Fusion & Entity Preservation:</b> For each film, we construct a unified textual representation: "
        "<code>tags = overview + genres + keywords + top_4_cast + director</code>. To prevent false collisions (e.g. 'Christopher Nolan' matching 'Christopher Walken'), "
        "spaces inside entity names are removed (<code>'christophernolan'</code>, <code>'sciencefiction'</code>).<br/>"
        "<b>2. Morphological Stemming:</b> NLTK's <code>PorterStemmer</code> reduces words to root stems (e.g., 'dramatically', 'dramas' -&gt; 'drama').<br/>"
        "<b>3. Vocabulary Vectorization:</b> <code>CountVectorizer(max_features=6000, stop_words='english')</code> generates a sparse frequency matrix.<br/>"
        "<b>4. L2 Normalization & Sub-5ms Cosine Scoring:</b> Standard cosine similarity requires computing norms dynamically. "
        "By pre-normalizing all vectors to unit Euclidean length (L2 norm = 1) during training: "
        "$$\\|\\vec{v}\\|_2 = 1 \\implies \\text{Cosine Similarity}(\\vec{u}, \\vec{v}) = \\frac{\\vec{u} \\cdot \\vec{v}}{\\|\\vec{u}\\| \\|\\vec{v}\\|} = \\vec{u} \\cdot \\vec{v}$$ "
        "This reduces similarity computation to a blazing-fast sparse matrix dot product executed in under 5 milliseconds across 13,906 movies!",
        styles['BodyTextCustom']
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("B. Engine 2: Collaborative SVD Matrix Factorization", styles['SecHeading2']))
    story.append(Paragraph(
        "<b>1. Latent Factor Decomposition:</b> Using <code>scikit-surprise</code> SVD on 100,000+ ratings, user ratings are decomposed into 20 latent dimensions: "
        "$$\\hat{r}_{ui} = \\mu + b_u + b_i + q_i^T p_u$$ "
        "where $q_i \\in \\mathbb{R}^{20}$ represents the item's latent preference profile.<br/>"
        "<b>2. Audience Confidence Damping:</b> Movies with very few votes can exhibit noisy high similarities. We dampen collaborative scores using a smooth logarithmic confidence curve: "
        "$$\\text{Confidence}(V) = \\frac{\\ln(1 + V)}{\\ln(1 + V) + 1.5}$$ "
        "<b>3. Cold-Start Solution via Ridge Projection:</b> Unrated new movies lack collaborative ratings. Rather than assigning zero, CineMatch trains a "
        "<code>Ridge(alpha=10.0)</code> regression model to project content embeddings into the 20-dimensional SVD factor space, ensuring 100% factor coverage.",
        styles['BodyTextCustom']
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("C. The Dynamic Hybrid Blending Formula", styles['SecHeading2']))
    story.append(Paragraph(
        "Both content and collaborative scores are min-max normalized across candidate films to the $[0, 1]$ interval. "
        "The final recommendation ranking score is computed dynamically according to the user's alpha slider setting: "
        "$$\\text{FinalScore} = \\alpha \\cdot \\text{ContentScore}_{norm} + (1.0 - \\alpha) \\cdot \\text{CollabScore}_{norm}$$ "
        "&bull; $\\alpha = 1.0$: Pure metadata match (same themes, cast, and director).<br/>"
        "&bull; $\\alpha = 0.0$: Pure crowd wisdom (movies liked by audiences with identical taste profiles).<br/>"
        "&bull; $\\alpha = 0.6$ (Default): The sweet spot balancing narrative plot continuity with serendipitous crowd favorites.",
        styles['BodyTextCustom']
    ))
    story.append(PageBreak())

    # =====================================================================
    # PAGE 8: VIVA & INTERVIEW GUIDE - PART 1
    # =====================================================================
    story.append(Paragraph("8. Technical Viva & Interview Mastery Guide (Part 1)", styles['SecHeading1']))
    story.append(Paragraph(
        "Use this presentation script and technical question bank to explain the project with complete authority:",
        styles['BodyTextCustom']
    ))

    story.append(Paragraph("Part A: The 2-Minute Architectural Walkthrough", styles['SecHeading2']))
    story.append(create_callout(
        "2-MINUTE ARCHITECTURAL SPEECH SCRIPT",
        "<i>\"When a user searches for a movie in CineMatch, our frontend communicates with a Flask backend. "
        "If they make a typo like 'dark nite', our difflib fuzzy matching engine identifies 'The Dark Knight' from our 13,906 movie catalog.<br/><br/>"
        "Once a seed movie is selected, our dual-engine recommendation algorithm kicks in. First, the content engine evaluates textual tags "
        "stemmed via NLTK's PorterStemmer and vectorized into 6,000 features. Second, our collaborative engine leverages 20-dimensional SVD latent factors "
        "trained on MovieLens ratings. Both vectors are L2-normalized, allowing us to compute cosine similarities using ultra-fast dot products in under 5 milliseconds.<br/><br/>"
        "The final scores are blended using our interactive alpha formula, allowing the user to prioritize plot similarity versus audience taste profiles. "
        "To ensure a seamless user experience, we have a 3-tier poster architecture guaranteeing zero broken images, and an on-the-fly vectorization engine "
        "that can even recommend brand-new uncataloged films via live TMDB and Wikipedia discovery.\"</i>",
        styles,
        accent_color=PRIMARY
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Part B: Technical Questions & Model Answers (Q1 to Q5)", styles['SecHeading2']))
    
    qa_p1 = [
        (
            "Q1. Why did you build a Hybrid recommender instead of just Content-Based or Collaborative?",
            "<b>Answer:</b> Content-based filtering suffers from over-specialization—it only recommends movies with identical keywords and cannot discover unexpected genres. Collaborative filtering suffers from the cold-start problem—new movies without user ratings cannot be recommended. By combining both with an alpha slider, we get the best of both worlds: content handles cold-start, while collaborative provides serendipity and audience taste discovery."
        ),
        (
            "Q2. How did you optimize recommendation speed for 13,906 movies without high latency?",
            "<b>Answer:</b> Instead of computing full cosine similarity matrices on every request (which would take seconds and gigabytes of RAM), we pre-normalized all feature vectors using L2 unit normalization during training. In linear algebra, the cosine similarity of two unit vectors equals their dot product. Dot products on sparse CSR matrices run in sub-5ms in RAM using NumPy and SciPy."
        ),
        (
            "Q3. How do you solve the Cold-Start problem for movies with zero ratings in MovieLens?",
            "<b>Answer:</b> We used a two-step strategy. First, we implemented confidence damping on collaborative scores. Second, for catalog movies completely absent from MovieLens, we trained a Ridge Regression model to project their content feature vectors into the 20-dimensional SVD latent space. Thus, every single movie has a valid collaborative factor vector."
        ),
        (
            "Q4. What is the role of PorterStemmer in your NLP pipeline?",
            "<b>Answer:</b> In natural language processing, words appear in different grammatical forms—e.g., 'action', 'acting', 'actor' or 'love', 'loved', 'loving'. Without stemming, CountVectorizer treats each as distinct independent vocabulary features. PorterStemmer strips suffixes down to root stems, drastically improving semantic overlap between related plot overviews."
        ),
        (
            "Q5. Why did you remove spaces between names (e.g. 'Christopher Nolan' -> 'christophernolan')?",
            "<b>Answer:</b> CountVectorizer splits text on whitespace into unigrams. If left separated, 'Christopher Nolan' becomes 'Christopher' and 'Nolan'. If another movie has actor 'Christopher Walken', the recommender would mistakenly compute a 50% name match on 'Christopher'. Merging entity tokens into single strings ensures exact entity preservation."
        )
    ]

    for q, a in qa_p1:
        qa_content = [
            Paragraph(f"<b>{q}</b>", styles['TableCellBold']),
            Spacer(1, 1),
            Paragraph(a, styles['TableCell'])
        ]
        qa_table = Table([[qa_content]], colWidths=[532])
        qa_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
            ('BOX', (0,0), (-1,-1), 0.5, BORDER_COLOR),
            ('TOPPADDING', (0,0), (-1,-1), 3.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
            ('LEFTPADDING', (0,0), (-1,-1), 7),
            ('RIGHTPADDING', (0,0), (-1,-1), 7),
        ]))
        story.append(qa_table)
        story.append(Spacer(1, 4))

    story.append(PageBreak())

    # =====================================================================
    # PAGE 9: VIVA PART 2, CODE DIRECTORY, FINAL SUMMARY
    # =====================================================================
    story.append(Paragraph("8. Technical Viva Guide (Part 2) & Repository Reference", styles['SecHeading1']))
    
    qa_p2 = [
        (
            "Q6. How does CineMatch guarantee zero broken poster images?",
            "<b>Answer:</b> We implemented a 3-Tier Fallback Architecture in poster_service.py. Tier 1 resolves TMDB w500 CDN URLs. Tier 2 queries Wikipedia REST summaries for thumbnail URLs. Tier 3 dynamically generates a high-resolution SVG poster with movie title, year, and genre badge. On the frontend, an onerror handler catches any network drops and routes to /api/placeholder."
        ),
        (
            "Q7. What happens if a user searches for a movie not in your 13,906 catalog?",
            "<b>Answer:</b> CineMatch has Universal On-the-Fly Discovery. If a title is not in the local catalog, the backend queries TMDB/Wikipedia live search, fetches its plot overview, stems it, passes it through our pre-fitted 6,000-feature CountVectorizer vocabulary in RAM, and computes cosine similarity against all 13,906 catalog movies in real time!"
        ),
        (
            "Q8. Why did you choose Vanilla JavaScript instead of React, Vue, or Angular?",
            "<b>Answer:</b> For this project, Vanilla ES6+ offers maximum speed, zero build-step overhead, and smaller payload size. By separating concerns into api.js (REST client), ui.js (DOM renderers), and app.js (state controller), we achieved clean modular architecture without the heavy bundle size and node_modules complexity of a frontend framework."
        ),
        (
            "Q9. What is the purpose of network_utils.py in your repository?",
            "<b>Answer:</b> In many regional networks and educational institutions, ISPs block or poison DNS records for api.themoviedb.org. network_utils.py monkey-patches socket.getaddrinfo to resolve TMDB directly to verified global AWS CloudFront edge IPs, guaranteeing uninterrupted API reliability."
        ),
        (
            "Q10. How does your Explainable AI (XAI) feature work?",
            "<b>Answer:</b> For every recommended movie card, generate_why_recommended() compares the target seed movie with the recommendation. It checks for shared directors, overlapping top-billed cast, shared genres, and whether collaborative audience overlap drove the score. It then displays an intuitive rationale chip like 'Directed by Christopher Nolan; shared Sci-Fi'."
        )
    ]

    for q, a in qa_p2:
        qa_content = [
            Paragraph(f"<b>{q}</b>", styles['TableCellBold']),
            Spacer(1, 1),
            Paragraph(a, styles['TableCell'])
        ]
        qa_table = Table([[qa_content]], colWidths=[532])
        qa_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
            ('BOX', (0,0), (-1,-1), 0.5, BORDER_COLOR),
            ('TOPPADDING', (0,0), (-1,-1), 3.0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3.0),
            ('LEFTPADDING', (0,0), (-1,-1), 7),
            ('RIGHTPADDING', (0,0), (-1,-1), 7),
        ]))
        story.append(qa_table)
        story.append(Spacer(1, 3))

    story.append(Spacer(1, 4))
    story.append(Paragraph("Codebase Structure & File-by-File Directory Reference", styles['SecHeading2']))

    dir_headers = ["File / Directory", "Type", "Core Responsibilities in Repository"]
    dir_rows = [
        ["app.py", "Python", "Main Flask application server, defines all 10 REST endpoints, executes on-the-fly scoring & live search."],
        ["train.py", "Python", "ML training pipeline: builds CountVectorizer, L2 normalized vectors, Surprise SVD latent factors, and exports .pkl files."],
        ["config.py", "Python", "Centralized configuration: paths, ML hyperparameters (max_features=6000, svd_factors=20), and API keys."],
        ["poster_service.py", "Python", "3-Tier poster resolution engine with disk JSON caching and parallel thread fetching."],
        ["poster_placeholder.py", "Python", "Standalone generator of high-resolution branded SVG poster graphics with title word-wrapping."],
        ["network_utils.py", "Python", "Low-level socket DNS patch resolving api.themoviedb.org to AWS CloudFront edge IPs."],
        ["scripts/build_catalog.py", "Python", "Comprehensive ETL script merging 5 datasets into 13,906 movies and caching poster URLs."],
        ["scripts/update_catalog.py", "Python", "CLI tool to pull newly released films from TMDB and trigger model retraining."],
        ["scripts/verify_posters.py", "Python", "Verification auditor confirming 100% poster coverage across all catalog films."],
        ["static/css/style.css", "CSS3", "Design system with Netflix-style dark theme, CSS grid, frosted glass, and animations."],
        ["static/js/api.js", "JavaScript", "Asynchronous API client handling fetch calls, query building, and HTTP error handling."],
        ["static/js/ui.js", "JavaScript", "DOM renderer for movie cards, seed hero banners, detail modals, and skeleton shimmers."],
        ["static/js/app.js", "JavaScript", "Main frontend controller managing search autocomplete, keyboard shortcuts, and filter state."],
        ["templates/index.html", "HTML5", "Responsive semantic single-page application frontend with modal dialog and controls."],
        ["requirements.txt", "Text", "Specifies exact library dependencies with version bounds for reproducible environments."],
        ["run.bat / run.sh", "Shell", "Cross-platform one-click launch scripts for Windows and macOS/Linux."]
    ]
    story.append(create_table(dir_headers, dir_rows, [125, 60, 347], styles, pad_v=2.2))
    story.append(Spacer(1, 6))

    story.append(create_callout(
        "SUMMARY & FINAL PRESENTATION TIP",
        "When presenting this project, emphasize both the <b>Machine Learning Depth</b> (Dual-Engine SVD + Stemmed CountVectorizer) and the "
        "<b>Software Engineering Polish</b> (L2 sub-5ms dot products, 3-tier fallback guaranteeing 0% broken posters, and CloudFront DNS patching). "
        "This proves that your project is not just a toy machine learning model, but a production-ready, full-stack software application.",
        styles,
        accent_color=SUCCESS_GREEN
    ))

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[SUCCESS] PDF successfully created at: {OUTPUT_PDF}")

if __name__ == "__main__":
    build_pdf()
