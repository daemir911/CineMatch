"""
Module to generate clean, high-resolution SVG poster placeholders
featuring the movie title, release year, and genre.
Never displays a broken image or an empty box.
"""
import html
import urllib.parse

def generate_svg_poster(title: str, year: int = None, genre: str = "Movie", width: int = 500, height: int = 750) -> str:
    """
    Generates a standalone, beautiful SVG image for movies that lack
    an external poster image.
    """
    safe_title = html.escape(str(title or "Untitled Movie"))
    year_str = str(year) if year and year > 1800 else ""
    safe_genre = html.escape(str(genre or "Feature Film"))

    # Word wrap title for SVG display
    words = safe_title.split()
    lines = []
    current_line = []
    
    for word in words:
        if len(" ".join(current_line + [word])) > 18:
            lines.append(" ".join(current_line))
            current_line = [word]
        else:
            current_line.append(word)
    if current_line:
        lines.append(" ".join(current_line))
    
    lines = lines[:4]  # Maximum 4 lines
    
    # Calculate starting Y based on number of lines
    start_y = 390 - (len(lines) * 18)
    tspan_elements = ""
    for i, line in enumerate(lines):
        y_pos = start_y + (i * 38)
        tspan_elements += f'<tspan x="250" y="{y_pos}">{line}</tspan>'

    badge_text = f"{year_str} • {safe_genre}" if year_str else safe_genre

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="50%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#020617"/>
    </linearGradient>
    <linearGradient id="accentGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#e50914"/>
      <stop offset="100%" stop-color="#f59e0b"/>
    </linearGradient>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000" flood-opacity="0.6"/>
    </filter>
  </defs>

  <!-- Background -->
  <rect width="{width}" height="{height}" fill="url(#bgGrad)"/>

  <!-- Subtle Decorative Border -->
  <rect x="18" y="18" width="{width - 36}" height="{height - 36}" fill="none" stroke="#334155" stroke-width="2" rx="14" opacity="0.4"/>

  <!-- Top Accent Bar -->
  <rect x="22" y="22" width="{width - 44}" height="4" fill="url(#accentGrad)" rx="2"/>

  <!-- Film Clapper Icon -->
  <g transform="translate(215, 180)" fill="#64748b" opacity="0.85">
    <path d="M60 10 L68 18 L10 18 L2 10 Z" fill="#94a3b8"/>
    <rect x="2" y="22" width="66" height="46" rx="4" fill="#334155"/>
    <circle cx="35" cy="45" r="12" fill="#475569"/>
    <polygon points="32,40 42,45 32,50" fill="#e2e8f0"/>
  </g>

  <!-- Title -->
  <text text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-size="28" font-weight="700" fill="#f8fafc" filter="url(#shadow)">
    {tspan_elements}
  </text>

  <!-- Meta Badge (Year & Genre) -->
  <g transform="translate(250, {start_y + (len(lines) * 38) + 25})">
    <rect x="-110" y="-14" width="220" height="28" rx="14" fill="#1e293b" stroke="#475569" stroke-width="1"/>
    <text text-anchor="middle" y="5" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-size="13" font-weight="500" fill="#94a3b8">
      {badge_text}
    </text>
  </g>

  <!-- Footer Brand -->
  <text x="250" y="700" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-size="11" font-weight="600" fill="#475569" letter-spacing="2">
    CINEMATCH • OFFICIAL POSTER
  </text>
</svg>"""
    return svg

def generate_svg_data_uri(title: str, year: int = None, genre: str = "Movie") -> str:
    """Returns SVG as a data URI string for direct embedding in src attributes."""
    svg = generate_svg_poster(title, year, genre)
    encoded = urllib.parse.quote(svg)
    return f"data:image/svg+xml;utf8,{encoded}"
