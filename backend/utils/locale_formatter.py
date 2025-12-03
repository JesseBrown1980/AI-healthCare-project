"""
Locale-specific formatting utilities for dates, numbers, and units.

Provides formatting functions that respect user's locale preferences.
"""

import locale
import logging
from datetime import datetime, timezone
from typing import Optional, Union
from decimal import Decimal

from backend.utils.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

# Locale mapping for supported languages
LOCALE_MAP = {
    "en": "en_US",  # English (US)
    "es": "es_ES",  # Spanish (Spain)
    "fr": "fr_FR",  # French (France)
    "ru": "ru_RU",  # Russian (Russia)
    "zh": "zh_CN",  # Chinese (Simplified)
    "pt": "pt_BR",  # Portuguese (Brazil)
    "de": "de_DE",  # German (Germany)
    "nl": "nl_NL",  # Dutch (Netherlands)
    "pl": "pl_PL",  # Polish (Poland)
    "sv": "sv_SE",  # Swedish (Sweden)
}

# Date format preferences by locale
DATE_FORMATS = {
    "en": "%m/%d/%Y",  # MM/DD/YYYY
    "es": "%d/%m/%Y",  # DD/MM/YYYY
    "fr": "%d/%m/%Y",  # DD/MM/YYYY
    "ru": "%d.%m.%Y",  # DD.MM.YYYY
    "zh": "%Y年%m月%d日",  # YYYY年MM月DD日
    "pt": "%d/%m/%Y",  # DD/MM/YYYY
    "de": "%d.%m.%Y",  # DD.MM.YYYY
    "nl": "%d-%m-%Y",  # DD-MM-YYYY
    "pl": "%d.%m.%Y",  # DD.MM.YYYY
    "sv": "%Y-%m-%d",  # YYYY-MM-DD
}

# Time format preferences
TIME_FORMATS = {
    "en": "%I:%M %p",  # 12-hour with AM/PM
    "es": "%H:%M",     # 24-hour
    "fr": "%H:%M",     # 24-hour
    "ru": "%H:%M",     # 24-hour
    "zh": "%H:%M",     # 24-hour
    "pt": "%H:%M",     # 24-hour
    "de": "%H:%M",     # 24-hour
    "nl": "%H:%M",     # 24-hour
    "pl": "%H:%M",     # 24-hour
    "sv": "%H:%M",     # 24-hour
}

# Number formatting (decimal separator)
DECIMAL_SEPARATORS = {
    "en": ".",
    "es": ",",
    "fr": ",",
    "ru": ",",
    "zh": ".",
    "pt": ",",
    "de": ",",
    "nl": ",",
    "pl": ",",
    "sv": ",",
}

# Thousands separator
THOUSANDS_SEPARATORS = {
    "en": ",",
    "es": ".",
    "fr": " ",
    "ru": " ",
    "zh": ",",
    "pt": ".",
    "de": ".",
    "nl": ".",
    "pl": " ",
    "sv": " ",
}


def format_date(
    date: Union[datetime, str],
    language: str = DEFAULT_LANGUAGE,
    include_time: bool = False,
) -> str:
    """
    Format a date according to locale preferences.
    
    Args:
        date: datetime object or ISO format string
        language: Language code for locale
        include_time: Whether to include time
        
    Returns:
        Formatted date string
    """
    if isinstance(date, str):
        try:
            # Try parsing ISO format
            if "T" in date:
                date = datetime.fromisoformat(date.replace("Z", "+00:00"))
            else:
                date = datetime.fromisoformat(date)
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse date string: {date}")
            return date
    
    if not isinstance(date, datetime):
        return str(date)
    
    # Ensure timezone-aware
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    
    # Get format for language
    date_format = DATE_FORMATS.get(language, DATE_FORMATS[DEFAULT_LANGUAGE])
    
    if include_time:
        time_format = TIME_FORMATS.get(language, TIME_FORMATS[DEFAULT_LANGUAGE])
        format_str = f"{date_format} {time_format}"
    else:
        format_str = date_format
    
    try:
        return date.strftime(format_str)
    except Exception as e:
        logger.warning(f"Error formatting date: {e}")
        return date.isoformat()


def format_number(
    value: Union[int, float, Decimal],
    language: str = DEFAULT_LANGUAGE,
    decimals: int = 2,
    use_thousands_separator: bool = True,
) -> str:
    """
    Format a number according to locale preferences.
    
    Args:
        value: Number to format
        language: Language code for locale
        decimals: Number of decimal places
        use_thousands_separator: Whether to use thousands separator
        
    Returns:
        Formatted number string
    """
    try:
        # Convert to float for formatting
        num_value = float(value)
        
        # Get separators
        decimal_sep = DECIMAL_SEPARATORS.get(language, DECIMAL_SEPARATORS[DEFAULT_LANGUAGE])
        thousands_sep = THOUSANDS_SEPARATORS.get(language, THOUSANDS_SEPARATORS[DEFAULT_LANGUAGE]) if use_thousands_separator else ""
        
        # Format with appropriate separators
        if decimals == 0:
            formatted = f"{int(num_value):,}".replace(",", thousands_sep) if thousands_sep else str(int(num_value))
        else:
            # Format with decimals
            formatted = f"{num_value:,.{decimals}f}"
            # Replace separators according to locale
            if thousands_sep:
                # Split by decimal point
                parts = formatted.split(".")
                if len(parts) == 2:
                    integer_part = parts[0].replace(",", thousands_sep)
                    decimal_part = parts[1]
                    formatted = f"{integer_part}{decimal_sep}{decimal_part}"
                else:
                    formatted = formatted.replace(",", thousands_sep)
            else:
                formatted = formatted.replace(",", "").replace(".", decimal_sep)
        
        return formatted
    except Exception as e:
        logger.warning(f"Error formatting number: {e}")
        return str(value)


def format_unit(
    value: Union[int, float, Decimal],
    unit: str,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """
    Format a value with unit according to locale preferences.
    
    Args:
        value: Numeric value
        unit: Unit string (e.g., "mg", "kg", "mmHg")
        language: Language code for locale
        
    Returns:
        Formatted string with value and unit
    """
    formatted_value = format_number(value, language=language, decimals=2 if isinstance(value, float) else 0)
    
    # Some units might need translation, but for now just format the number
    return f"{formatted_value} {unit}"


def format_datetime(
    dt: Union[datetime, str],
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """
    Format a datetime according to locale preferences.
    
    Args:
        dt: datetime object or ISO format string
        language: Language code for locale
        
    Returns:
        Formatted datetime string
    """
    return format_date(dt, language=language, include_time=True)


def parse_locale_date(
    date_str: str,
    language: str = DEFAULT_LANGUAGE,
) -> Optional[datetime]:
    """
    Parse a locale-formatted date string.
    
    Args:
        date_str: Date string in locale format
        language: Language code for locale
        
    Returns:
        datetime object or None if parsing fails
    """
    date_format = DATE_FORMATS.get(language, DATE_FORMATS[DEFAULT_LANGUAGE])
    
    try:
        return datetime.strptime(date_str, date_format)
    except ValueError:
        # Try ISO format as fallback
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse date string: {date_str}")
            return None
