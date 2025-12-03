"""
Windows build and packaging module.
"""

from .version import get_version, get_version_info, compare_versions
from .auto_update import UpdateChecker, UpdateService

__all__ = [
    'get_version',
    'get_version_info',
    'compare_versions',
    'UpdateChecker',
    'UpdateService',
]

