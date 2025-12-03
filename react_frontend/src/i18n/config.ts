/**
 * i18next configuration for React frontend
 * Loads translations from backend locale files
 */

import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

// Supported languages (matching backend)
export const SUPPORTED_LANGUAGES = ['en', 'es', 'fr', 'ru', 'zh', 'pt', 'de', 'nl', 'pl', 'sv']

export const LANGUAGE_NAMES: Record<string, string> = {
  en: 'English',
  es: 'Español',
  fr: 'Français',
  ru: 'Русский',
  zh: '中文',
  pt: 'Português',
  de: 'Deutsch',
  nl: 'Nederlands',
  pl: 'Polski',
  sv: 'Svenska',
}

// Load translations from backend locale files
async function loadTranslations(language: string): Promise<Record<string, any>> {
  try {
    // Try loading from public folder first (for production builds)
    const publicResponse = await fetch(`/locales/${language}.json`)
    if (publicResponse.ok) {
      return await publicResponse.json()
    }
    
    // Fallback: try loading from backend (for development)
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    // Remove /api/v1 from base URL to get backend root
    const backendRoot = apiBaseUrl.replace(/\/api\/v1$/, '')
    const response = await fetch(`${backendRoot}/backend/locales/${language}.json`)
    
    if (response.ok) {
      return await response.json()
    }
    
    // If both fail, return empty object (will fallback to English)
    console.warn(`Failed to load translations for ${language}`)
    return {}
  } catch (error) {
    console.error(`Error loading translations for ${language}:`, error)
    return {}
  }
}

// Initialize i18next
i18n
  .use(LanguageDetector) // Detects user language from browser
  .use(initReactI18next) // Passes i18n down to react-i18next
  .init({
    fallbackLng: 'en',
    defaultNS: 'translation',
    supportedLngs: SUPPORTED_LANGUAGES,
    
    // Language detection options
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
      lookupLocalStorage: 'i18nextLng',
    },
    
    // Interpolation options
    interpolation: {
      escapeValue: false, // React already escapes values
    },
    
    // React-specific options
    react: {
      useSuspense: false, // Disable suspense for now
    },
    
    // Resources will be loaded dynamically
    resources: {},
  })

// Load translations for all supported languages
async function loadAllTranslations() {
  for (const lang of SUPPORTED_LANGUAGES) {
    try {
      const translations = await loadTranslations(lang)
      if (Object.keys(translations).length > 0) {
        i18n.addResourceBundle(lang, 'translation', translations, true, true)
      }
    } catch (error) {
      console.error(`Failed to load translations for ${lang}:`, error)
    }
  }
}

// Load translations on initialization
loadAllTranslations()

export default i18n
