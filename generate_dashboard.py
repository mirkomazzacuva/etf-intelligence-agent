"""Generate the v12 public landing page; preserve the previous dashboard as legacy."""
from pathlib import Path
from core.fineco_real_engine import ROOT, OUT_DASH_DATA, build_real_portfolio
from core.fineco_real_ui import render_real_dashboard


def generate_dashboard() -> None:
    # Old v11 research kept on a separate page (not as current Fineco P/L).
    try:
        from generate_legacy_dashboard import generate_dashboard as legacy_generator
        legacy_generator()
    except Exception as exc:
        print('Legacy research dashboard could not be generated: %s' % exc)
    if not OUT_DASH_DATA.exists():
        build_real_portfolio(allow_network=False,persist=True)
    render_real_dashboard(ROOT/'index.html')
    print('Dashboard v12 reale generata: index.html; dashboard storica: legacy_alpha_forge.html')


if __name__ == '__main__':
    generate_dashboard()
