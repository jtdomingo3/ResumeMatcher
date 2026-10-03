"""
Theme Design Tokens and Glassmorphic Dark Styles for NiceGUI Frontend.
Includes Google Fonts (Outfit, Inter, JetBrains Mono), HSL tailored color palette,
smooth micro-animations, glass cards, and status pill badges.
"""

from nicegui import ui

GLASS_DARK_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --bg-base: #07090e;
    --bg-surface: #0e131f;
    --bg-card: rgba(17, 24, 39, 0.72);
    --bg-card-hover: rgba(26, 34, 53, 0.85);
    
    --border-subtle: rgba(255, 255, 255, 0.08);
    --border-glow: rgba(99, 102, 241, 0.35);
    
    --primary: #6366f1;
    --primary-light: #818cf8;
    --primary-gradient: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
    --card-gradient: linear-gradient(145deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.8) 100%);
    
    --success: #10b981;
    --success-bg: rgba(16, 185, 129, 0.15);
    --warning: #f59e0b;
    --warning-bg: rgba(245, 158, 11, 0.15);
    --danger: #f43f5e;
    --danger-bg: rgba(244, 63, 94, 0.15);
    --info: #0ea5e9;
    --info-bg: rgba(14, 165, 233, 0.15);
    
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
    --text-dim: #64748b;
}

body {
    background-color: var(--bg-base) !important;
    background-image: 
        radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.12) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(236, 72, 153, 0.08) 0px, transparent 50%),
        radial-gradient(at 50% 100%, rgba(16, 185, 129, 0.06) 0px, transparent 50%) !important;
    background-attachment: fixed !important;
    color: var(--text-main) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    margin: 0;
    padding: 0;
}

h1, h2, h3, h4, h5, h6, .brand-font {
    font-family: 'Outfit', sans-serif !important;
    letter-spacing: -0.02em;
}

.mono-font {
    font-family: 'JetBrains Mono', monospace !important;
}

/* Glassmorphism Cards */
.glass-card {
    background: var(--bg-card) !important;
    backdrop-filter: blur(16px) saturate(180%) !important;
    -webkit-backdrop-filter: blur(16px) saturate(180%) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 16px !important;
    box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5) !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

.glass-card:hover {
    border-color: var(--border-glow) !important;
    box-shadow: 0 16px 36px -10px rgba(99, 102, 241, 0.2) !important;
    transform: translateY(-2px);
}

.glass-header {
    background: rgba(10, 14, 23, 0.85) !important;
    backdrop-filter: blur(20px) !important;
    border-bottom: 1px solid var(--border-subtle) !important;
}

/* Gradient Text */
.gradient-text {
    background: var(--primary-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    display: inline-block;
}

/* Skill Chips */
.chip-matched {
    background: var(--success-bg) !important;
    color: var(--success) !important;
    border: 1px solid rgba(16, 185, 129, 0.3) !important;
    border-radius: 9999px !important;
    padding: 4px 12px !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
}

.chip-preferred {
    background: var(--info-bg) !important;
    color: var(--info) !important;
    border: 1px solid rgba(14, 165, 233, 0.3) !important;
    border-radius: 9999px !important;
    padding: 4px 12px !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
}

.chip-missing {
    background: var(--danger-bg) !important;
    color: var(--danger) !important;
    border: 1px solid rgba(244, 63, 94, 0.3) !important;
    border-radius: 9999px !important;
    padding: 4px 12px !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
}

/* Glow Buttons */
.glow-btn {
    background: var(--primary-gradient) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.39) !important;
    transition: all 0.2s ease !important;
}

.glow-btn:hover {
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.6) !important;
    transform: translateY(-1px);
}

/* Status Badges */
.status-pill {
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.status-online {
    background: rgba(16, 185, 129, 0.15);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.3);
}

.status-indicator {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background-color: #10b981;
    box-shadow: 0 0 8px #10b981;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0% { transform: scale(0.95); opacity: 0.8; }
    50% { transform: scale(1.15); opacity: 1; }
    100% { transform: scale(0.95); opacity: 0.8; }
}

/* Custom Scrollbar */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: rgba(10, 14, 23, 0.5);
}
::-webkit-scrollbar-thumb {
    background: rgba(99, 102, 241, 0.3);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(99, 102, 241, 0.6);
}
"""


def apply_theme():
    """
    Injects custom typography, responsive dark tokens, and glassmorphic styling.
    """
    ui.add_head_html(f"<style>{GLASS_DARK_CSS}</style>")
    ui.dark_mode().enable()
