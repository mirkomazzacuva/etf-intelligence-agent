from __future__ import annotations

from html import escape
from typing import Any

import pandas as pd
import streamlit as st

PREMIUM_CSS = """
<style>
:root {
  --af-bg: #070b18;
  --af-bg-2: #0f1730;
  --af-panel: rgba(18, 27, 54, .78);
  --af-panel-strong: rgba(22, 34, 67, .94);
  --af-border: rgba(255,255,255,.105);
  --af-text: #f3f6ff;
  --af-muted: #a7b4d4;
  --af-accent: #6ee7c8;
  --af-blue: #91b8ff;
  --af-gold: #ffd37a;
  --af-red: #ff8f98;
  --af-green: #6ee7c8;
}
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(circle at 8% 0%, rgba(68, 118, 255, .24), transparent 34%),
    radial-gradient(circle at 95% 6%, rgba(110, 231, 200, .16), transparent 30%),
    linear-gradient(180deg, #070b18 0%, #0a1021 48%, #060913 100%);
  color: var(--af-text);
}
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(11,17,34,.98), rgba(13,22,44,.96));
  border-right: 1px solid var(--af-border);
}
.block-container { padding-top: 2.1rem; padding-bottom: 4rem; max-width: 1320px; }
[data-testid="stMetric"] {
  background: linear-gradient(135deg, rgba(22,34,67,.92), rgba(13,20,41,.86));
  border: 1px solid var(--af-border);
  border-radius: 20px;
  padding: 17px 18px;
  box-shadow: 0 16px 44px rgba(0,0,0,.22);
}
[data-testid="stMetricLabel"] { color: var(--af-muted); }
[data-testid="stMetricValue"] { color: var(--af-text); font-weight: 850; }
.af-hero {
  position: relative;
  overflow: hidden;
  padding: 30px 30px 26px;
  border: 1px solid var(--af-border);
  border-radius: 28px;
  background:
    linear-gradient(135deg, rgba(28,43,86,.92), rgba(11,17,34,.88)),
    radial-gradient(circle at top right, rgba(110,231,200,.18), transparent 35%);
  box-shadow: 0 24px 80px rgba(0,0,0,.36);
  margin-bottom: 1.25rem;
}
.af-hero:after {
  content: "";
  position:absolute; inset:auto -110px -170px auto; width:360px; height:360px;
  background: radial-gradient(circle, rgba(145,184,255,.22), transparent 62%);
  pointer-events:none;
}
.af-kicker {
  display:inline-flex; gap:8px; align-items:center;
  padding: 7px 12px; border-radius: 999px;
  color: var(--af-accent); background: rgba(110,231,200,.12);
  border: 1px solid rgba(110,231,200,.24); font-weight: 800; font-size: 13px;
}
.af-title { margin: 12px 0 8px; font-size: clamp(34px, 5vw, 60px); line-height: .96; letter-spacing: -.052em; font-weight: 900; }
.af-subtitle { max-width: 900px; color: var(--af-muted); font-size: 17px; line-height: 1.58; margin: 0; }
.af-panel {
  border: 1px solid var(--af-border); border-radius: 24px; padding: 18px 20px;
  background: linear-gradient(135deg, rgba(21,33,63,.82), rgba(10,15,31,.72));
  box-shadow: 0 16px 50px rgba(0,0,0,.22);
}
.af-card-row { display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:14px; margin: 18px 0 8px; }
.af-card {
  padding: 16px 17px; border-radius: 20px; border:1px solid var(--af-border);
  background: rgba(255,255,255,.055);
}
.af-card .label { color: var(--af-muted); text-transform:uppercase; letter-spacing:.08em; font-size: 12px; }
.af-card .value { color: var(--af-text); font-size: 24px; font-weight: 880; margin-top: 7px; }
.af-card .hint { color: var(--af-muted); font-size: 12px; margin-top: 5px; }
.af-badge {
  display:inline-flex; align-items:center; gap:6px; padding: 5px 10px; border-radius:999px;
  font-size: 12px; font-weight: 850; white-space: nowrap; border:1px solid rgba(255,255,255,.14);
  background: rgba(255,255,255,.07); color:#dbe6ff;
}
.af-badge.buy, .af-badge.success, .af-badge.priorita { color: var(--af-green); background: rgba(110,231,200,.12); border-color: rgba(110,231,200,.22); }
.af-badge.warn, .af-badge.monitor, .af-badge.pullback { color: var(--af-gold); background: rgba(255,211,122,.12); border-color: rgba(255,211,122,.23); }
.af-badge.risk, .af-badge.avoid, .af-badge.high { color: var(--af-red); background: rgba(255,143,152,.12); border-color: rgba(255,143,152,.24); }
.af-note { color: var(--af-muted); line-height: 1.58; font-size: 14px; }
.af-divider { height:1px; background: linear-gradient(90deg, transparent, rgba(255,255,255,.18), transparent); margin: 20px 0; }
.stDataFrame, [data-testid="stDataFrame"] { border-radius: 18px; overflow: hidden; }
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] {
  background: rgba(255,255,255,.055); border-radius: 999px; padding: 8px 16px;
  border: 1px solid rgba(255,255,255,.08);
}
.stTabs [aria-selected="true"] { background: rgba(110,231,200,.13) !important; color: var(--af-accent) !important; }
button[kind="primary"] { border-radius: 999px !important; }
@media (max-width: 980px) { .af-card-row { grid-template-columns: repeat(2, minmax(0,1fr)); } }
@media (max-width: 620px) { .af-card-row { grid-template-columns: 1fr; } .af-hero { padding: 22px; } }
</style>
"""


def apply_theme() -> None:
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str, badge: str = "AlphaForge v4") -> None:
    st.markdown(
        f"""
        <div class="af-hero">
          <span class="af-kicker">✦ {escape(badge)}</span>
          <div class="af-title">{escape(title)}</div>
          <p class="af-subtitle">{escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def mini_cards(cards: list[tuple[str, Any, str | None]]) -> None:
    html = ["<div class='af-card-row'>"]
    for label, value, hint in cards:
        html.append(
            "<div class='af-card'>"
            f"<div class='label'>{escape(str(label))}</div>"
            f"<div class='value'>{escape(str(value))}</div>"
            f"<div class='hint'>{escape(str(hint or ''))}</div>"
            "</div>"
        )
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def badge(text: Any) -> str:
    raw = str(text or "n/d")
    css = ""
    low = raw.lower()
    if any(x in low for x in ["buy", "success", "priorità", "priorita", "costruttiva", "ok"]):
        css = " buy"
    elif any(x in low for x in ["monitor", "graduale", "pullback", "wait", "watch", "neutral"]):
        css = " warn"
    elif any(x in low for x in ["risk", "alto", "high", "avoid", "evitare", "failed", "weak"]):
        css = " risk"
    return f"<span class='af-badge{css}'>{escape(raw)}</span>"


def info_panel(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="af-panel">
          <h3 style="margin:0 0 8px;">{escape(title)}</h3>
          <div class="af-note">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def style_priority_dataframe(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    numeric_cols = [c for c in ["Score Finale", "Priority Score", "Volatilità %", "Max Drawdown %"] if c in df.columns]
    styler = df.style
    if "Priority Score" in df.columns:
        styler = styler.background_gradient(subset=["Priority Score"])
    if "Score Finale" in df.columns:
        styler = styler.background_gradient(subset=["Score Finale"])
    for col in numeric_cols:
        styler = styler.format({col: "{:.1f}"})
    return styler
