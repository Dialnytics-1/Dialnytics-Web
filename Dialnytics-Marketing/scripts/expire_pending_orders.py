"""Scheduled worker: python -m scripts.expire_pending_orders (website project root)."""
import os
from app.database import make_database
from app.pending_expiry import expire_manual_orders


def main():
    url = os.environ.get('DATABASE_URL', '')
    if not url:
        raise SystemExit('DATABASE_URL is required; no changes made')
    engine, session_factory = make_database(url)
    try:
        with session_factory.begin() as db:
            expired = expire_manual_orders(db)
        print(f'Expired {len(expired)} unpaid manual orders')
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
