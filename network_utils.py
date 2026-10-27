"""
Network utility helpers for reliable TMDB and poster API requests.
Ensures api.themoviedb.org resolves directly to verified CloudFront edge IPs,
bypassing ISP DNS poisoning/blocks common in certain regions.
"""
import socket
import logging

logger = logging.getLogger("NetworkUtils")

_DNS_PATCHED = False

# Verified global AWS CloudFront anycast IPs for api.themoviedb.org
CLOUDFRONT_IPS = [
    "99.84.152.8",
    "99.84.152.32",
    "99.84.152.53",
    "99.84.152.85",
    "13.224.245.44",
    "13.224.245.92",
    "13.224.245.63",
    "13.224.245.47"
]

def enable_tmdb_dns_fallback():
    """
    Patches socket.getaddrinfo to resolve api.themoviedb.org using
    verified global CloudFront IPs directly.
    """
    global _DNS_PATCHED
    if _DNS_PATCHED:
        return

    orig_getaddrinfo = socket.getaddrinfo
    curr_idx = [0]

    def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        if host == "api.themoviedb.org":
            try:
                return orig_getaddrinfo(host, port, family, type, proto, flags)
            except Exception:
                ip = CLOUDFRONT_IPS[curr_idx[0] % len(CLOUDFRONT_IPS)]
                curr_idx[0] += 1
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]
        return orig_getaddrinfo(host, port, family, type, proto, flags)

    socket.getaddrinfo = patched_getaddrinfo
    _DNS_PATCHED = True
    logger.info("TMDB direct CloudFront resolver active.")

# Enable automatically on import
enable_tmdb_dns_fallback()
