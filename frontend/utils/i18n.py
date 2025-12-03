"""
Internationalization utilities for Streamlit frontend.

Loads translations from backend locale files and provides translation functions.
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Default language
DEFAULT_LANGUAGE = "en"

# Supported languages (matching backend)
SUPPORTED_LANGUAGES = ["en", "es", "fr", "ru", "zh", "pt", "de", "nl", "pl", "sv"]

LANGUAGE_NAMES = {
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "ru": "Русский",
    "zh": "中文",
    "pt": "Português",
    "de": "Deutsch",
    "nl": "Nederlands",
    "pl": "Polski",
    "sv": "Svenska",
}

# Translation cache
_translation_cache: Dict[str, Dict[str, str]] = {}


def get_locale_path() -> Path:
    """
    Get the path to the backend locales directory.
    
    Returns:
        Path to locales directory
    """
    # Get project root (parent of frontend directory)
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    return project_root / "backend" / "locales"


def load_translations(language: str = DEFAULT_LANGUAGE) -> Dict[str, str]:
    """
    Load translations for a given language.
    
    Args:
        language: Language code (e.g., 'en', 'es', 'fr')
        
    Returns:
        Dictionary of translation keys to translated strings
    """
    if language in _translation_cache:
        return _translation_cache[language]
    
    locale_path = get_locale_path()
    locale_file = locale_path / f"{language}.json"
    
    translations = {}
    
    if locale_file.exists():
        try:
            with open(locale_file, "r", encoding="utf-8") as f:
                translations = json.load(f)
            _translation_cache[language] = translations
            logger.debug(f"Loaded translations for language: {language}")
        except Exception as e:
            logger.warning(f"Failed to load translations for {language}: {e}")
            # Fallback to English if available
            if language != DEFAULT_LANGUAGE:
                return load_translations(DEFAULT_LANGUAGE)
    else:
        logger.warning(f"Locale file not found: {locale_file}")
        # Fallback to English if available
        if language != DEFAULT_LANGUAGE:
            return load_translations(DEFAULT_LANGUAGE)
    
    return translations


def translate(key: str, language: Optional[str] = None, default: Optional[str] = None, **kwargs) -> str:
    """
    Translate a key to the specified language.
    
    Args:
        key: Translation key (supports dot notation, e.g., 'ui.home.title')
        language: Target language (uses default if not provided)
        default: Default value if translation not found
        **kwargs: Format arguments for string interpolation
        
    Returns:
        Translated string
    """
    if language is None:
        language = DEFAULT_LANGUAGE
    
    translations = load_translations(language)
    
    # Support dot notation for nested keys
    value = translations
    for part in key.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        else:
            value = None
            break
    
    if value is None:
        # Try fallback to English if not already English
        if language != DEFAULT_LANGUAGE:
            return translate(key, language=DEFAULT_LANGUAGE, default=default, **kwargs)
        
        # Return default or key if not found
        if default is not None:
            return default.format(**kwargs) if kwargs else default
        return key
    
    # Format string if kwargs provided
    if kwargs and isinstance(value, str):
        try:
            return value.format(**kwargs)
        except (KeyError, ValueError):
            logger.warning(f"Failed to format translation key '{key}' with kwargs: {kwargs}")
            return value
    
    return value


def t(key: str, language: Optional[str] = None, default: Optional[str] = None, **kwargs) -> str:
    """
    Alias for translate() for convenience.
    """
    return translate(key, language=language, default=default, **kwargs)


def get_supported_languages() -> Dict[str, str]:
    """
    Get dictionary of supported language codes and their display names.
    
    Returns:
        Dictionary mapping language codes to display names
    """
    return LANGUAGE_NAMES.copy()


def clear_translation_cache():
    """Clear the translation cache (useful for testing or hot-reloading)."""
    global _translation_cache
    _translation_cache.clear()
    logger.debug("Translation cache cleared")
