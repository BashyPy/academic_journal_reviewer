"""Role definitions and permissions for academic review system"""

from enum import Enum
from typing import List, Set


class UserRole(str, Enum):
    """User roles in the academic review system"""

    AUTHOR = "author"  # Submit manuscripts
    REVIEWER = "reviewer"  # Review manuscripts (future feature)
    EDITOR = "editor"  # Manage reviews and make decisions
    ADMIN = "admin"  # System administration
    SUPER_ADMIN = "super_admin"  # Full system access


class Permission(str, Enum):
    """System permissions"""

    # Submission permissions
    SUBMIT_MANUSCRIPT = "submit_manuscript"
    VIEW_OWN_SUBMISSIONS = "view_own_submissions"
    DELETE_OWN_SUBMISSIONS = "delete_own_submissions"

    # Review permissions
    VIEW_REVIEWS = "view_reviews"
    CONDUCT_REVIEW = "conduct_review"
    EDIT_REVIEW = "edit_review"

    # Editor permissions
    VIEW_ALL_SUBMISSIONS = "view_all_submissions"
    ASSIGN_REVIEWERS = "assign_reviewers"
    MAKE_DECISIONS = "make_decisions"
    MANAGE_WORKFLOW = "manage_workflow"

    # Admin permissions
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MANAGE_API_KEYS = "manage_api_keys"
    VIEW_STATISTICS = "view_statistics"

    # System permissions
    SYSTEM_CONFIG = "system_config"
    MANAGE_SECURITY = "manage_security"


# Role-Permission mapping
ROLE_PERMISSIONS: dict[UserRole, Set[Permission]] = {
    UserRole.AUTHOR: {
        Permission.SUBMIT_MANUSCRIPT,
        Permission.VIEW_OWN_SUBMISSIONS,
        Permission.DELETE_OWN_SUBMISSIONS,
    },
    UserRole.REVIEWER: {
        Permission.SUBMIT_MANUSCRIPT,
        Permission.VIEW_OWN_SUBMISSIONS,
        Permission.VIEW_REVIEWS,
        Permission.CONDUCT_REVIEW,
        Permission.EDIT_REVIEW,
    },
    UserRole.EDITOR: {
        Permission.SUBMIT_MANUSCRIPT,
        Permission.VIEW_OWN_SUBMISSIONS,
        Permission.VIEW_ALL_SUBMISSIONS,
        Permission.VIEW_REVIEWS,
        Permission.ASSIGN_REVIEWERS,
        Permission.MAKE_DECISIONS,
        Permission.MANAGE_WORKFLOW,
        Permission.VIEW_STATISTICS,
    },
    UserRole.ADMIN: {
        Permission.SUBMIT_MANUSCRIPT,
        Permission.VIEW_OWN_SUBMISSIONS,
        Permission.VIEW_ALL_SUBMISSIONS,
        Permission.VIEW_REVIEWS,
        Permission.MANAGE_USERS,
        Permission.MANAGE_ROLES,
        Permission.VIEW_AUDIT_LOGS,
        Permission.MANAGE_API_KEYS,
        Permission.VIEW_STATISTICS,
    },
    UserRole.SUPER_ADMIN: set(Permission),  # All permissions
}


def get_role_permissions(role: str) -> Set[Permission]:
    """Get permissions for a role"""
    try:
        user_role = UserRole(role)
        return ROLE_PERMISSIONS.get(user_role, set())
    except ValueError:
        return set()


def has_permission(role: str, permission: Permission) -> bool:
    """Check if role has specific permission"""
    return permission in get_role_permissions(role)


def get_available_roles() -> List[str]:
    """Get list of available roles"""
    return [role.value for role in UserRole]


_ROLE_DESCRIPTIONS = {
    UserRole.AUTHOR: "Submit manuscripts for review",
    UserRole.REVIEWER: "Review submitted manuscripts (future feature)",
    UserRole.EDITOR: "Manage reviews and make editorial decisions",
    UserRole.ADMIN: "Manage users and system settings",
    UserRole.SUPER_ADMIN: "Full system access and control",
}


def get_role_description(role: str) -> str:
    """Get role description"""
    try:
        return _ROLE_DESCRIPTIONS.get(UserRole(role), "Unknown role")
    except ValueError:
        return "Unknown role"
