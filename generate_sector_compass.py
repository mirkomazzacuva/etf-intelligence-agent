from __future__ import annotations

from core.sector_compass_engine import build_sector_compass, save_sector_compass


def main() -> int:
    compass = build_sector_compass()
    save_sector_compass(compass)
    print(f"Sector Compass generata: {len(compass)} settori")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
