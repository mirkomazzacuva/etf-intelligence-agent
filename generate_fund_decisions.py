from __future__ import annotations

from core.fund_decision_engine import save_decision_cockpit


def main() -> None:
    cockpit, summary = save_decision_cockpit()
    print(
        "Fineco decision cockpit aggiornato: "
        f"{len(cockpit)} strumenti, "
        f"margine netto {summary.get('margine_netto_eur')} EUR, "
        f"decisione: {summary.get('decisione_sintesi')}"
    )


if __name__ == "__main__":
    main()
