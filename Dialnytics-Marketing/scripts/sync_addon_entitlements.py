"""Run as separately scheduled worker, not in web request."""
import os
from app.database import make_database
from app.addon_entitlement_sync import EntitlementHTTPAdapter, process_pending

def main():
    engine, sessions = make_database(os.environ['DATABASE_URL'])
    try:
        adapter = EntitlementHTTPAdapter(os.environ['DIALER_BACKEND_URL'], os.environ['DIALER_PROVISION_TOKEN'])
        print(process_pending(sessions, adapter))
    finally:
        engine.dispose()

if __name__ == '__main__': main()
