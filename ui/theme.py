"""
RailTrack Design System & Visual Theme.
Tokens, CSS injection, responsive styling, and accessibility guidelines.
"""

import streamlit as st


# Color Palette Tokens
THEME_TOKENS = {
    "primary_navy": "#071127",
    "railway_blue": "#1E40AF",
    "electric_cyan": "#0284C7",
    "surface_canvas": "#071127",
    "surface_card": "#101D37",
    "surface_elevated": "#162640",
    "surface_muted": "#0B1730",
    "text_primary": "#F1F5F9",
    "text_secondary": "#A9BAD3",
    "text_muted": "#64748B",
    "border_card": "#2A3B57",
    "border_subtle": "#1E2E4A",
    "border_focus": "#35B9F2",
    "verified_green": "#10B981",
    "verified_bg": "#064E3B",
    "warning_amber": "#F59E0B",
    "warning_bg": "#78350F",
    "danger_red": "#EF4444",
    "danger_bg": "#7F1D1D",
    "info_blue": "#38BDF8",
    "info_bg": "#0C4A6E",
}


CUSTOM_CSS = """
<style>
/* ==============================================================
   RAILTRACK MODERN RAILWAY DARK DESIGN SYSTEM
   ============================================================== */

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}

/* Fluid Container */
.block-container {
    max-width: 1240px !important;
    padding-top: 1.25rem !important;
    padding-bottom: 3.5rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
}

/* Global High-Contrast Headings */
h1, h2, h3, h4, h5, h6,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 {
    color: #F1F5F9 !important;
    font-weight: 700 !important;
    letter-spacing: -0.01em !important;
}

/* Brand Banner & Header */
.rt-brand-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.85rem 1.25rem;
    background: linear-gradient(135deg, #071127 0%, #101D37 100%);
    border-radius: 12px;
    margin-bottom: 1.25rem;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.3);
    border: 1px solid #2A3B57;
}

.rt-brand-title {
    font-size: 1.35rem;
    font-weight: 800;
    color: #F1F5F9 !important;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    letter-spacing: -0.02em;
}

.rt-brand-subtitle {
    font-size: 0.8rem;
    color: #A9BAD3;
    font-weight: 500;
}

/* Reusable Content Cards */
.rt-card {
    background: #101D37;
    border: 1px solid #2A3B57;
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
    color: #F1F5F9;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.rt-card:hover {
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35);
}

.rt-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid #1E2E4A;
    padding-bottom: 0.75rem;
    margin-bottom: 0.85rem;
}

.rt-card-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #F1F5F9;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}

/* Provenance and Status Badges */
.rt-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.25rem 0.65rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}

.rt-badge-live {
    background-color: rgba(16, 185, 129, 0.18);
    color: #34D399;
    border: 1px solid rgba(52, 211, 153, 0.4);
}

.rt-badge-historical {
    background-color: rgba(56, 189, 248, 0.18);
    color: #38BDF8;
    border: 1px solid rgba(56, 189, 248, 0.4);
}

.rt-badge-reference {
    background-color: rgba(148, 163, 184, 0.15);
    color: #CBD5E1;
    border: 1px solid rgba(148, 163, 184, 0.35);
}

.rt-badge-predicted {
    background-color: rgba(168, 85, 247, 0.18);
    color: #C084FC;
    border: 1px solid rgba(168, 85, 247, 0.4);
}

.rt-badge-demo {
    background-color: rgba(245, 158, 11, 0.18);
    color: #FBBF24;
    border: 1px solid rgba(245, 158, 11, 0.4);
}

.rt-badge-caution {
    background-color: rgba(245, 158, 11, 0.18);
    color: #FBBF24;
    border: 1px solid rgba(245, 158, 11, 0.4);
}

.rt-badge-unavailable {
    background-color: rgba(239, 68, 68, 0.18);
    color: #F87171;
    border: 1px solid rgba(239, 68, 68, 0.4);
}

/* Metric Pill */
.rt-metric-pill {
    display: inline-flex;
    flex-direction: column;
    padding: 0.5rem 0.85rem;
    background: #0B1730;
    border: 1px solid #2A3B57;
    border-radius: 8px;
    min-width: 100px;
}

.rt-metric-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: #A9BAD3;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.rt-metric-val {
    font-size: 1.1rem;
    font-weight: 800;
    color: #F1F5F9;
    font-family: 'JetBrains Mono', monospace;
}

/* Streamlit Native Metric Overrides */
[data-testid="stMetricValue"] {
    color: #F1F5F9 !important;
    font-weight: 800 !important;
}

[data-testid="stMetricLabel"] {
    color: #A9BAD3 !important;
    font-weight: 600 !important;
}

/* Streamlit Sidebar Overrides */
[data-testid="stSidebar"] {
    background-color: #071127 !important;
    border-right: 1px solid #2A3B57 !important;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #F1F5F9 !important;
}

/* Quick Service Cards */
.rt-service-tile {
    background: #101D37;
    border: 1px solid #2A3B57;
    border-radius: 12px;
    padding: 1.25rem 1rem;
    text-align: center;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    cursor: pointer;
    transition: all 0.2s ease;
    height: 100%;
}

.rt-service-tile:hover {
    border-color: #38BDF8;
    box-shadow: 0 6px 18px rgba(56, 189, 248, 0.25);
    transform: translateY(-2px);
}

.rt-service-icon {
    font-size: 1.85rem;
    margin-bottom: 0.5rem;
}

.rt-service-name {
    font-weight: 700;
    font-size: 0.95rem;
    color: #F1F5F9;
    margin-bottom: 0.25rem;
}

.rt-service-desc {
    font-size: 0.75rem;
    color: #A9BAD3;
}

/* Station Progression Step Timeline */
.rt-timeline-step {
    display: flex;
    align-items: flex-start;
    position: relative;
    padding-bottom: 1.5rem;
}

.rt-timeline-step:last-child {
    padding-bottom: 0;
}

.rt-timeline-line {
    position: absolute;
    left: 14px;
    top: 24px;
    bottom: 0;
    width: 2px;
    background: #2A3B57;
}

.rt-timeline-step.active .rt-timeline-line {
    background: #38BDF8;
}

.rt-timeline-dot {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    background: #0B1730;
    border: 3px solid #64748B;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 1rem;
    z-index: 2;
    flex-shrink: 0;
    color: #F1F5F9;
}

.rt-timeline-step.active .rt-timeline-dot {
    border-color: #38BDF8;
    background: #101D37;
    color: #38BDF8;
    box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.25);
}

.rt-timeline-step.passed .rt-timeline-dot {
    border-color: #10B981;
    background: #064E3B;
    color: #34D399;
}

/* Horizontal Train Formation */
.rt-rake-diagram {
    display: flex;
    align-items: center;
    overflow-x: auto;
    padding: 1.25rem 0.5rem;
    gap: 6px;
    background: #0B1730;
    border: 1px solid #2A3B57;
    border-radius: 10px;
    margin: 1rem 0;
    scrollbar-width: thin;
}

.rt-rake-coach {
    flex: 0 0 auto;
    width: 72px;
    height: 64px;
    border-radius: 6px;
    background: #162640;
    border: 2px solid #2A3B57;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.8rem;
    color: #F1F5F9;
    position: relative;
    cursor: pointer;
    transition: all 0.15s ease;
}

.rt-rake-coach.selected {
    border-color: #38BDF8;
    background: rgba(14, 165, 233, 0.25);
    color: #38BDF8;
    box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.35);
    transform: translateY(-2px);
}

.rt-rake-coach.loco {
    background: #071127;
    color: #F1F5F9;
    border-color: #38BDF8;
    width: 82px;
}

.rt-rake-class {
    font-size: 0.65rem;
    color: #A9BAD3;
    font-weight: 500;
}

/* Accessibility & High Contrast Focus */
button:focus-visible, input:focus-visible, select:focus-visible {
    outline: 2px solid #38BDF8 !important;
    outline-offset: 2px !important;
}

/* Mobile Responsiveness */
@media (max-width: 768px) {
    .block-container {
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        padding-top: 0.75rem !important;
    }
    .rt-brand-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.5rem;
    }
    .rt-card {
        padding: 0.85rem;
    }
}
</style>
"""


def inject_custom_theme() -> None:
    """Injects RailTrack's cohesive railway styling and meta viewport tags."""
    st.markdown(
        '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">',
        unsafe_allow_html=True,
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
