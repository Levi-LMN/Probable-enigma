# ============================================================================
# FILE: run.py (Main entry point)
# ============================================================================
import os
import pathlib
from dotenv import load_dotenv

# Force load .env before anything else
load_dotenv(dotenv_path=pathlib.Path(__file__).parent / '.env', override=True)

# ── DEBUG: print exactly what Flask will use ─────────────────────────────────
print("\n" + "="*60)
print("  ENV DEBUG")
print("="*60)
print(f"  .env path      : {pathlib.Path(__file__).parent / '.env'}")
print(f"  .env exists    : {(pathlib.Path(__file__).parent / '.env').exists()}")
print(f"  GOOGLE_CLIENT_ID     : {os.environ.get('GOOGLE_CLIENT_ID', '*** NOT SET ***')}")
print(f"  GOOGLE_CLIENT_SECRET : {os.environ.get('GOOGLE_CLIENT_SECRET', '*** NOT SET ***')[:6]}..." if os.environ.get('GOOGLE_CLIENT_SECRET') else "  GOOGLE_CLIENT_SECRET : *** NOT SET ***")
print(f"  ADMIN_EMAIL          : {os.environ.get('ADMIN_EMAIL', '*** NOT SET ***')}")
print(f"  SECRET_KEY           : {'SET' if os.environ.get('SECRET_KEY') else '*** NOT SET — will use random ***'}")
print("="*60 + "\n")
# ─────────────────────────────────────────────────────────────────────────────

from app import create_app, db

app = create_app()

# ── DEBUG: confirm what the app config actually picked up ────────────────────
with app.app_context():
    print("\n" + "="*60)
    print("  APP CONFIG DEBUG")
    print("="*60)
    print(f"  app.config GOOGLE_CLIENT_ID     : {app.config.get('GOOGLE_CLIENT_ID', '*** MISSING ***')}")
    print(f"  app.config GOOGLE_CLIENT_SECRET : {str(app.config.get('GOOGLE_CLIENT_SECRET', '*** MISSING ***'))[:6]}..." if app.config.get('GOOGLE_CLIENT_SECRET') else "  app.config GOOGLE_CLIENT_SECRET : *** MISSING ***")
    print(f"  app.config ADMIN_EMAIL          : {app.config.get('ADMIN_EMAIL', '*** MISSING ***')}")
    print("="*60 + "\n")
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)