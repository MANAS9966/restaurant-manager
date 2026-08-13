
from __future__ import annotations
import functools
from business_logic.exceptions import AuthorizationError


try:
    import bcrypt
    _USE_BCRYPT = True
except ImportError:
    import hashlib, os
    _USE_BCRYPT = False


# ------------------------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    
    plain = plain.strip().lower()
    if _USE_BCRYPT:
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()
    # Fallback: sha256 with random salt prefix
    salt = os.urandom(16).hex()
    digest = hashlib.sha256((salt + plain).encode()).hexdigest()
    return f"sha256${salt}${digest}"


def verify_password(plain: str, hashed: str) -> bool:

    plain = plain.strip().lower()
    if _USE_BCRYPT and not hashed.startswith("sha256$"):
        try:
            return bcrypt.checkpw(plain.encode(), hashed.encode())
        except Exception:
            return False
    try:
        _, salt, digest = hashed.split("$", 2)
        return hashlib.sha256((salt + plain).encode()).hexdigest() == digest
    except Exception:
        return False


# ---------------------------------------------------------------------------------------

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "view_all_users", "manage_users", "view_all_owners",
        "manage_owners", "verify_owners", "view_all_orders",
        "manage_all_orders", "view_audit_log", "view_sessions",
        "force_logout", "view_all_dishes"
    },
    "owner": {
        "manage_own_dishes", "view_own_orders",
        "update_order_status", "view_own_analytics"
    },
    "customer": {
        "browse_restaurants", "browse_dishes",
        "create_order", "view_own_orders", "cancel_own_order"
    },
}


def check_permission(user_role: str, permission: str) -> bool:
    """Return True if the role has the given permission."""
    return permission in ROLE_PERMISSIONS.get(user_role, set())


def require_permission(permission: str):

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(self, *args, **kwargs):
            # Convention: first positional arg is actor_role
            role = args[0] if args else kwargs.get("actor_role", "")
            if not check_permission(role, permission):
                raise AuthorizationError(
                    f"Role '{role}' is not allowed to perform '{permission}'"
                )
            return fn(self, *args, **kwargs)
        return wrapper
    return decorator
