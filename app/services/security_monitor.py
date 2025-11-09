"""Security monitoring service"""

from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Deque, Dict

from app.utils.logger import get_logger

logger = get_logger(__name__)


class SecurityMonitor:
    """Monitor and detect security threats"""

    def __init__(self):
        try:
            self.failed_auth_attempts: Dict[str, Deque[datetime]] = defaultdict(deque)
            self.suspicious_ips: set = set()
            self.blocked_ips: set = set()
        except Exception as e:
            logger.error(f"Failed to initialize SecurityMonitor: {e}")
            # In a real-world scenario, you might want to re-raise or handle this more gracefully
            raise

    def record_failed_auth(self, ip_address: str):
        """Record failed authentication attempt"""
        if not ip_address or not isinstance(ip_address, str):
            logger.warning("Invalid IP address provided to record_failed_auth")
            return

        now = datetime.now()
        attempts = self.failed_auth_attempts[ip_address]
        attempts.append(now)

        # Clean old attempts (older than 1 hour)
        one_hour_ago = now - timedelta(hours=1)
        while attempts and attempts[0] < one_hour_ago:
            attempts.popleft()

        # Check for brute force (5+ failures in 1 hour)
        if len(attempts) >= 5:
            self.block_ip(ip_address, "brute_force")

    def block_ip(self, ip_address: str, reason: str):
        """Block IP address"""
        try:
            if ip_address and ip_address not in self.blocked_ips:
                self.blocked_ips.add(ip_address)
                logger.warning(f"IP blocked: {ip_address} - Reason: {reason}")
        except Exception as e:
            logger.error(f"Failed to block IP {ip_address}: {e}")

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
