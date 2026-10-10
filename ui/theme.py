"""
RailTrack Design System & Visual Theme.
Tokens, CSS injection, responsive styling, and accessibility guidelines.
"""

import streamlit as st


# Color Palette Tokens
THEME_TOKENS = {
    "primary_navy": "#071530",
    "railway_blue": "#1E40AF",
    "electric_cyan": "#0284C7",
    "surface_white": "#FFFFFF",
    "surface_card": "#FFFFFF",
    "surface_muted": "#F1F5F9",
    "text_dark": "#0F172A",
    "text_muted": "#475569",
    "text_light": "#94A3B8",
    "border_light": "#E2E8F0",
    "border_focus": "#2563EB",
    "verified_green": "#059669",
    "verified_bg": "#ECFDF5",
    "warning_amber": "#D97706",
    "warning_bg": "#FFFBEB",
    "danger_red": "#DC2626",
    "danger_bg": "#FEF2F2",
    "info_blue": "#2563EB",
    "info_bg": "#EFF6FF",
}


CUSTOM_CSS = """
<style>
/* ==============================================================
   RAILTRACK MODERN RAILWAY DESIGN SYSTEM
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

/* Brand Banner & Header */
.rt-brand-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.85rem 1.25rem;
    background: linear-gradient(135deg, #071530 0%, #0F275A 100%);
    border-radius: 12px;
    margin-bottom: 1.25rem;
    box-shadow: 0 4px 14px rgba(7, 21, 48, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.rt-brand-title {
    font-size: 1.35rem;
    font-weight: 800;
    color: #FFFFFF !important;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    letter-spacing: -0.02em;
}

.rt-brand-subtitle {
    font-size: 0.8rem;
    color: #94A3B8;
    font-weight: 500;
}

/* Reusable Content Cards */
.rt-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.rt-card:hover {
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
}

.rt-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid #F1F5F9;
    padding-bottom: 0.75rem;
    margin-bottom: 0.85rem;
}

.rt-card-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #0F172A;
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
    background-color: #ECFDF5;
    color: #059669;
    border: 1px solid #A7F3D0;
}

.rt-badge-historical {
    background-color: #EFF6FF;
    color: #1D4ED8;
    border: 1px solid #BFDBFE;
}

.rt-badge-reference {
    background-color: #F8FAFC;
    color: #475569;
    border: 1px solid #CBD5E1;
}

.rt-badge-predicted {
    background-color: #F5F3FF;
    color: #6D28D9;
    border: 1px solid #DDD6FE;
}

.rt-badge-demo {
    background-color: #FFFBEB;
    color: #B45309;
    border: 1px solid #FDE68A;
}

.rt-badge-unavailable {
    background-color: #FEF2F2;
    color: #B91C1C;
    border: 1px solid #FECACA;
}

/* Metric Pill */
.rt-metric-pill {
    display: inline-flex;
    flex-direction: column;
    padding: 0.5rem 0.85rem;
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    min-width: 100px;
}

.rt-metric-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.rt-metric-val {
    font-size: 1.1rem;
    font-weight: 800;
    color: #0F172A;
    font-family: 'JetBrains Mono', monospace;
}

/* Quick Service Cards */
.rt-service-tile {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 1.25rem 1rem;
    text-align: center;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
    cursor: pointer;
    transition: all 0.2s ease;
    height: 100%;
}

.rt-service-tile:hover {
    border-color: #1E40AF;
    box-shadow: 0 6px 16px rgba(30, 64, 175, 0.1);
    transform: translateY(-2px);
}

.rt-service-icon {
    font-size: 1.85rem;
    margin-bottom: 0.5rem;
}

.rt-service-name {
    font-weight: 700;
    font-size: 0.95rem;
    color: #0F172A;
    margin-bottom: 0.25rem;
}

.rt-service-desc {
    font-size: 0.75rem;
    color: #64748B;
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
    background: #CBD5E1;
}

.rt-timeline-step.active .rt-timeline-line {
    background: #1E40AF;
}

.rt-timeline-dot {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    background: #FFFFFF;
    border: 3px solid #94A3B8;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 1rem;
    z-index: 2;
    flex-shrink: 0;
}

.rt-timeline-step.active .rt-timeline-dot {
    border-color: #1E40AF;
    background: #EFF6FF;
    color: #1E40AF;
    box-shadow: 0 0 0 4px rgba(30, 64, 175, 0.15);
}

.rt-timeline-step.passed .rt-timeline-dot {
    border-color: #059669;
    background: #059669;
    color: #FFFFFF;
}

/* Horizontal Train Formation */
.rt-rake-diagram {
    display: flex;
    align-items: center;
    overflow-x: auto;
    padding: 1.25rem 0.5rem;
    gap: 6px;
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    margin: 1rem 0;
    scrollbar-width: thin;
}

.rt-rake-coach {
    flex: 0 0 auto;
    width: 72px;
    height: 64px;
    border-radius: 6px;
    background: #FFFFFF;
    border: 2px solid #CBD5E1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.8rem;
    color: #0F172A;
    position: relative;
    cursor: pointer;
    transition: all 0.15s ease;
}

.rt-rake-coach.selected {
    border-color: #1E40AF;
    background: #EFF6FF;
    color: #1E40AF;
    box-shadow: 0 0 0 3px rgba(30, 64, 175, 0.2);
    transform: translateY(-2px);
}

.rt-rake-coach.loco {
    background: #1E293B;
    color: #F8FAFC;
    border-color: #0F172A;
    width: 82px;
}

.rt-rake-class {
    font-size: 0.65rem;
    color: #64748B;
    font-weight: 500;
}

/* Accessibility & High Contrast Focus */
button:focus-visible, input:focus-visible, select:focus-visible {
    outline: 2px solid #2563EB !important;
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
