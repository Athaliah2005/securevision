#!/usr/bin/env python
"""
Seed script — creates the initial admin user and adds localhost to the allow-list.
Run once:  python scripts/seed.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app, db
from app.models import User, AllowedIP


def seed():
    app = create_app("development")
    with app.app_context():
        db.create_all()

        # ── Create admin user if not present ──────────────────────────────────
        if not User.query.filter_by(username="admin").first():
            admin = User(
                username="admin",
                email="admin@example.com",
                role="admin",
            )
            admin.set_password("ChangeMe123!")   # CHANGE THIS IMMEDIATELY
            db.session.add(admin)
            print("✓ Admin user created  (username: admin  password: ChangeMe123!)")
            print("  ⚠  Change the password immediately after first login!")
        else:
            print("· Admin user already exists — skipping.")

        # ── Seed default allowed IPs ──────────────────────────────────────────
        for ip, label in [("127.0.0.1", "Localhost IPv4"), ("::1", "Localhost IPv6")]:
            if not AllowedIP.query.filter_by(ip_address=ip).first():
                db.session.add(AllowedIP(ip_address=ip, label=label, added_by="seed"))
                print(f"✓ Added {ip} to allow-list ({label})")

        db.session.commit()
        print("Seed complete.")


if __name__ == "__main__":
    seed()
