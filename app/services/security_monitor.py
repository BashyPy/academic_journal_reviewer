"""Security monitoring service"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

from app.utils.logger import get_logger

logger = get_logger(__name__)


class SecurityMonitor:
    """Monitor and detect security threats"""

    def __init__(self):
        self.failed_auth_attempts: Dict[str, List[datetime]] = defaultdict(list)
        self.suspicious_ips: set = set()
        self.blocked_ips: set = set()

    def record_failed_auth(self, ip_address: str):
        """Record failed authentication attempt"""
        now = datetime.now()
        self.failed_auth_attempts[ip_address].append(now)

        # Clean old attempts (older than 1 hour)
        self.failed_auth_attempts[ip_address] = [
            ts
            for ts in self.failed_auth_attempts[ip_address]
            if now - ts < timedelta(hours=1)
        ]

        # Check for brute force (5+ failures in 1 hour)
        if len(self.failed_auth_attempts[ip_address]) >= 5:
            self.block_ip(ip_address, "brute_force")

    def block_ip(self, ip_address: str, reason: str):
        """Block IP address"""
        if ip_address not in self.blocked_ips:
            self.blocked_ips.add(ip_address)
            logger.warning(f"IP blocked: {ip_address} - Reason: {reason}")

    def is_blocked(self, ip_address: str) -> bool:
        """Check if IP is blocked"""
        return ip_address in self.blocked_ips

    def mark_suspicious(self, ip_address: str):
        """Mark IP as suspicious"""
        self.suspicious_ips.add(ip_address)
        logger.warning(f"IP marked suspicious: {ip_address}")

    def is_suspicious(self, ip_address: str) -> bool:
        """Check if IP is suspicious"""
        return ip_address in self.suspicious_ips

    def get_stats(self) -> dict:
        """Get security statistics"""
        return {
            "blocked_ips": len(self.blocked_ips),
            "suspicious_ips": len(self.suspicious_ips),
            "monitored_ips": len(self.failed_auth_attempts),
        }


security_monitor = SecurityMonitor()
