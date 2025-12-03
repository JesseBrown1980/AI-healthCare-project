"""
Internationalization (i18n) utilities for multi-language support.

Provides translation functions and locale management for the backend API.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional, Any
from fastapi import Request

logger = logging.getLogger(__name__)

# Default language
DEFAULT_LANGUAGE = "en"

# Supported languages
SUPPORTED_LANGUAGES = ["en", "es", "fr", "ru", "zh", "pt", "de", "nl", "pl", "sv"]

# Language names for display
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

# Cache for loaded translations
_translation_cache: Dict[str, Dict[str, str]] = {}


def get_locales_dir() -> Path:
    """Get the locales directory path."""
    return Path(__file__).parent.parent / "locales"


def load_translations(language: str) -> Dict[str, str]:
    """
    Load translations for a given language.
    
    Args:
        language: Language code (e.g., 'en', 'es', 'fr')
        
    Returns:
        Dictionary of translation keys to translated strings
    """
    if language in _translation_cache:
        return _translation_cache[language]
    
    # Validate language
    if language not in SUPPORTED_LANGUAGES:
        logger.warning(f"Unsupported language: {language}, falling back to {DEFAULT_LANGUAGE}")
        language = DEFAULT_LANGUAGE
    
    locales_dir = get_locales_dir()
    translation_file = locales_dir / f"{language}.json"
    
    if not translation_file.exists():
        logger.warning(f"Translation file not found: {translation_file}, using English")
        if language != DEFAULT_LANGUAGE:
            return load_translations(DEFAULT_LANGUAGE)
        # If English is missing, return empty dict
        return {}
    
    try:
        with open(translation_file, "r", encoding="utf-8") as f:
            translations = json.load(f)
            _translation_cache[language] = translations
            logger.debug(f"Loaded {len(translations)} translations for {language}")
            return translations
    except Exception as e:
        logger.error(f"Error loading translations for {language}: {e}")
        if language != DEFAULT_LANGUAGE:
            return load_translations(DEFAULT_LANGUAGE)
        return {}


def get_language_from_request(request: Request) -> str:
    """
    Extract language preference from request.
    
    Checks in order:
    1. Query parameter 'lang'
    2. Accept-Language header
    3. Default language
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Language code (e.g., 'en', 'es', 'fr')
    """
    # Check query parameter first
    lang_param = request.query_params.get("lang")
    if lang_param and lang_param in SUPPORTED_LANGUAGES:
        return lang_param
    
    # Check Accept-Language header
    accept_language = request.headers.get("Accept-Language", "")
    if accept_language:
        # Parse Accept-Language header (e.g., "en-US,en;q=0.9,es;q=0.8")
        languages = []
        for part in accept_language.split(","):
            lang = part.split(";")[0].strip().lower()
            # Extract base language (e.g., "en" from "en-US")
            base_lang = lang.split("-")[0]
            if base_lang in SUPPORTED_LANGUAGES:
                languages.append(base_lang)
        
        if languages:
            return languages[0]
    
    return DEFAULT_LANGUAGE


def translate(key: str, language: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """
    Translate a key to the specified language.
    
    Args:
        key: Translation key (e.g., 'errors.not_found')
        language: Target language code
        **kwargs: Format arguments for the translation string
        
    Returns:
        Translated string, or the key if translation not found
    """
    translations = load_translations(language)
    translation = translations.get(key, key)
    
    # Format the translation if kwargs are provided
    if kwargs:
        try:
            translation = translation.format(**kwargs)
        except (KeyError, ValueError) as e:
            logger.warning(f"Error formatting translation '{key}': {e}")
    
    return translation


def t(key: str, language: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """
    Alias for translate() for convenience.
    
    Args:
        key: Translation key
        language: Target language code
        **kwargs: Format arguments
        
    Returns:
        Translated string
    """
    return translate(key, language, **kwargs)


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


# Pre-load default language translations on module import
try:
    load_translations(DEFAULT_LANGUAGE)
except Exception as e:
    logger.warning(f"Failed to pre-load default translations: {e}")
