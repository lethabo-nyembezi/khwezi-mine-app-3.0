"""auth.py - login (salted SHA-256) and role-based access control (RBAC)."""
import hashlib
import secrets


def hash_password(password, salt):
    """Salted hash: SHA-256 of (salt + password). The salt stops identical passwords sharing a hash."""
    return hashlib.sha256((salt + password).encode()).hexdigest()


def new_salt():
    return secrets.token_hex(8)


def authenticate(users, username, password):
    """Return the user row if credentials are valid and the account is active, else None."""
    match = users[users["Username"].str.lower() == username.strip().lower()]
    if match.empty:
        return None
    user = match.iloc[0]
    if user["Active"] != "Yes":
        return None
    ok = secrets.compare_digest(hash_password(password, user["Salt"]), user["Password_Hash"])
    return user if ok else None


def has_access(perms, role, function):
    """True if role may use function, according to role_permissions.csv."""
    row = perms[perms["Function"] == function]
    return (not row.empty) and row.iloc[0].get(role) == "Yes"
