"""Input validation utilities"""

import re
from typing import Tuple


def validate_password(password: str) -> Tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if len(password) > 128:
        return False, "Password must not exceed 128 characters"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    if not re.search(r"[^a-zA-Z0-9]", password):
        return False, "Password must contain at least one special character"
    return True, "Password is strong"


def validate_username(username: str) -> Tuple[bool, str]:
    """Validate username format"""
    if not username:
        return True, ""  # Username is optional
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    if len(username) > 30:
        return False, "Username must not exceed 30 characters"
    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        return False, "Username can only contain letters, numbers, hyphens, and underscores"
    if username[0] in "-_" or username[-1] in "-_":
        return False, "Username cannot start or end with hyphen or underscore"
    return True, "Username is valid"
