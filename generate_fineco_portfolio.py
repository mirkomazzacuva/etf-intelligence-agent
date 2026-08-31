from __future__ import annotations

from core.fineco_portfolio_tracker import (
    analyse_fineco_portfolio,
    ensure_template_files,
    load_fineco_portfolio,
    save_fineco_outputs,
)


def main() -> None:
    ensure_template_files()
    portfolio = load_fineco_portfolio()
    positions, summary, questions = analyse_fineco_portfolio(portfolio)
    save_fineco_outputs(positions, summary, questions)
    print(
        "Fineco portfolio tracker aggiornato: "
        f"{summary.get('numero_strumenti')} strumenti, "
        f"capitale stimato {summary.get('capitale_versato_stimato_eur')} EUR, "
        f"fase {summary.get('fase')}"
    )


if __name__ == "__main__":
    main()
