"""Account linking and provisioning after both identities have been verified."""

from __future__ import annotations

from src.auth.application.ports.out.repositories import UserRepository
from src.auth.domain.entities import User
from src.auth.domain.exceptions import SsoAccountConflict, SsoEmailMismatch
from src.auth.application.dto.sso import SsoIdentity, normalize_email


class SsoAccountService:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def link(self, local_user: User, identity: SsoIdentity) -> User:
        # The caller must supply a valid local access token and a valid service JWT.
        if not identity.email or normalize_email(local_user.email) != identity.email:
            raise SsoEmailMismatch("SSO and local account emails differ")
        if local_user.sso_loginid and local_user.sso_loginid != identity.loginid:
            raise SsoAccountConflict("Local account is linked to another SSO identity")
        mapped = self._users.find_by_sso_loginid(identity.loginid)
        if mapped and mapped.id != local_user.id:
            raise SsoAccountConflict("SSO identity is linked to another account")
        if mapped:
            return mapped
        return self._users.link_sso_loginid(local_user.id.value, identity.loginid)

    def provision(self, identity: SsoIdentity) -> User:
        mapped = self._users.find_by_sso_loginid(identity.loginid)
        if mapped:
            return mapped
        if not identity.email:
            raise SsoAccountConflict("SSO identity has no usable email")
        if self._users.find_by_email(identity.email):
            raise SsoAccountConflict("Email belongs to an existing account")
        user = User.create(
            email=identity.email,
            password_hash=None,
            name=identity.name,
            sso_loginid=identity.loginid,
        )
        return self._users.provision_sso_user(user)
