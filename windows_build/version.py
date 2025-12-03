"""
Version management for the Healthcare AI Assistant application.
"""

__version__ = "1.0.0"
__version_info__ = (1, 0, 0)

def get_version():
    """Get the current version string."""
    return __version__

def get_version_info():
    """Get the version as a tuple."""
    return __version_info__

def compare_versions(version1: str, version2: str) -> int:
    """
    Compare two version strings.
    Returns: -1 if version1 < version2, 0 if equal, 1 if version1 > version2
    """
    def version_tuple(v):
        return tuple(map(int, v.split('.')))
    
    v1 = version_tuple(version1)
    v2 = version_tuple(version2)
    
    if v1 < v2:
        return -1
    elif v1 > v2:
        return 1
    else:
        return 0

