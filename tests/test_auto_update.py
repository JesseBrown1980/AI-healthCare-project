"""
Tests for auto-update system.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from windows_build.auto_update import UpdateChecker, UpdateService
from windows_build.version import get_version, compare_versions


def test_version_comparison():
    """Test version comparison logic."""
    assert compare_versions("1.0.0", "1.0.1") == -1  # Older
    assert compare_versions("1.0.1", "1.0.0") == 1   # Newer
    assert compare_versions("1.0.0", "1.0.0") == 0    # Equal
    assert compare_versions("1.0.0", "2.0.0") == -1  # Major version
    assert compare_versions("1.1.0", "1.0.9") == 1   # Minor version


def test_get_version():
    """Test version retrieval."""
    version = get_version()
    assert version == "1.0.0"
    assert isinstance(version, str)


@pytest.mark.asyncio
async def test_update_checker_initialization():
    """Test UpdateChecker initialization."""
    checker = UpdateChecker()
    
    assert checker.current_version == "1.0.0"
    assert checker.app_name == "Healthcare AI Assistant"
    assert checker.update_url is not None


@pytest.mark.asyncio
async def test_check_for_updates_no_update():
    """Test update check when no update is available."""
    checker = UpdateChecker(current_version="2.0.0")
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {"tag_name": "v1.0.0"}
        mock_response.raise_for_status = MagicMock()
        
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        result = await checker.check_for_updates()
        
        assert result is not None
        assert result.get("available") is False


@pytest.mark.asyncio
async def test_check_for_updates_available():
    """Test update check when update is available."""
    checker = UpdateChecker(current_version="1.0.0")
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "tag_name": "v1.0.1",
            "assets": [
                {
                    "name": "HealthcareAIAssistant-Setup-1.0.1.exe",
                    "browser_download_url": "https://github.com/releases/v1.0.1/installer.exe",
                    "size": 1000000
                }
            ],
            "body": "Release notes"
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        result = await checker.check_for_updates()
        
        assert result is not None
        assert result.get("available") is True
        assert result.get("latest_version") == "1.0.1"
        assert result.get("download_url") is not None

