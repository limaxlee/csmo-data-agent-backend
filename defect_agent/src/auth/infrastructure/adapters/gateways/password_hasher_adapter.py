"""Adapter: implements PasswordEncoder using bcrypt."""

from __future__ import annotations

import bcrypt

from src.auth.application.ports.out.gateways import PasswordEncoder


class PasswordHasherAdapter(PasswordEncoder):
    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, plain: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        except (ValueError, TypeError):
            return False
