"""
gen_coupons.py — [SOLO ADMIN] Genera cupones desde la terminal.

Requiere la variable ADMIN_API_KEY (la misma del .env del servidor).

Uso:
    export ADMIN_API_KEY=...   # o definida en .env
    python scripts/gen_coupons.py --server http://localhost:8000 -n 5 --days 30
"""
import argparse
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--server", default="http://localhost:8000")
    p.add_argument("-n", "--quantity", type=int, default=1, help="Cantidad de cupones")
    p.add_argument("--days", type=int, default=30, help="Días de acceso por cupón")
    args = p.parse_args()

    admin_key = os.getenv("ADMIN_API_KEY", "")
    if not admin_key:
        print("Falta ADMIN_API_KEY en el entorno o en .env")
        sys.exit(1)

    r = requests.post(
        f"{args.server.rstrip('/')}/coupons/admin/generate",
        headers={"X-Admin-Key": admin_key},
        json={"quantity": args.quantity, "duration_days": args.days},
        timeout=15,
    )
    r.raise_for_status()

    print(f"Cupones generados ({args.days} días c/u):")
    for c in r.json():
        print(f"  {c['code']}")


if __name__ == "__main__":
    main()
