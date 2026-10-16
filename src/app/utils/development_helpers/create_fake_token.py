from datetime import datetime, timedelta

import jwt

# Dev secret (local only!)
SECRET_KEY = "devsecret"
ALGORITHM = "HS256"


from collections.abc import Iterable


def generate_fake_jwt(
    username: str = "paul.mittelstaedt@testemail",
    name: str = "paul testuser1234",
    roles: Iterable[str] | None = None,
    organization: Iterable[str] | None = None,
) -> str:
    now = datetime.utcnow()
    if roles is None:
        roles = [
            "GRPS_Portal_HMVM_TESTROLE",
            "GRPS_HMVM_Kasse",
            "GRPS_HMVM_Administrator",
            "GRPS_HMVM_TASIOAdmin",
        ]
    if organization is None:
        organization = ["GRPS_Portal_Org_1111111", "GRPS_Portal_Org_2222222"]

    payload = {
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iat": int(now.timestamp()),
        "auth_time": int(now.timestamp()) - 10,
        "proxy": ["proxy"],
        "resource_access": {"proxy": {"roles": ["proxy"]}},
        "email_verified": True,
        "roles": roles,
        "organization": organization,
        "name": name,
        "preferred_username": username,
        "given_name": name.split(maxsplit=1)[0],
        "family_name": name.split()[1],
        "email": username,
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


if __name__ == "__main__":
    print(generate_fake_jwt())
