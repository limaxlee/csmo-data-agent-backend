#!/usr/bin/env python3
"""Initialize database tables and create a default admin user.

Usage:
    python init_db.py [--email admin@example.com] [--password admin12345]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import uuid

from src.auth.domain.entities import User
from src.auth.infrastructure.adapters.gateways.password_hasher_adapter import PasswordHasherAdapter
from src.auth.infrastructure.adapters.repositories.user_repository_adapter import UserRepositoryAdapter
from src.container.database.engine import SessionLocal
from src.auth.infrastructure.repositories.user_repository_impl import UserRepositoryImpl



def init_tables() -> None:
    """Bring the database up to the latest migration.

    Alembic owns the schema, not create_all: a database built by create_all has
    no alembic_version row, so the next migration would try to create tables
    that already exist. Running the migrations here keeps `python init_db.py`
    working as the one-step setup while producing a database Alembic can go on
    to manage.
    """
    from alembic import command
    from alembic.config import Config

    print("Applying database migrations...")
    ini = Path(__file__).resolve().parent / "alembic.ini"
    command.upgrade(Config(str(ini)), "head")
    print("✓ Database is at the latest migration")


def create_admin(email: str, password: str, name: str = "Admin") -> None:
    """Create a default admin user."""
    db = SessionLocal()
    try:
        adapter = UserRepositoryAdapter(UserRepositoryImpl(db))
        hasher = PasswordHasherAdapter()

        existing = adapter.find_by_email(email)
        if existing:
            print(f"User {email} already exists, skipping.")
            return

        user = User.create(
            email=email,
            password_hash=hasher.hash_password(password),
            name=name,
        )
        user.role = "admin"
        adapter.save(user)
        db.commit()
        print(f"✓ Admin user created: {email}")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize DefectAgent Backend database")
    parser.add_argument("--email", default="admin@example.com", help="Admin email")
    parser.add_argument("--password", default="admin12345", help="Admin password")
    parser.add_argument("--name", default="Admin", help="Admin display name")
    args = parser.parse_args()

    init_tables()
    create_admin(args.email, args.password, args.name)
    print("\n✓ Database initialization complete!")
    print(f"  Admin login: {args.email} / {args.password}")


if __name__ == "__main__":
    sys.exit(main())
