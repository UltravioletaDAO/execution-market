import { useEffect, useState, type ReactNode } from "react";
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useSettingsStore } from "../stores/settings";
import es from "../i18n/es.json";
import en from "../i18n/en.json";
import enSafe from "../i18n/en-safe.json";
import esSafe from "../i18n/es-safe.json";

const LANGUAGE_KEY = "em_language";

i18n.use(initReactI18next).init({
  resources: {
    es: { translation: es },
    en: { translation: en },
  },
  lng: "en",
  fallbackLng: "en",
  interpolation: {
    escapeValue: false,
  },
});

export function I18nProvider({ children }: { children: ReactNode }) {
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    AsyncStorage.getItem(LANGUAGE_KEY)
      .then((lang) => {
        if (lang) i18n.changeLanguage(lang);
      })
      .then(() => useSettingsStore.getState().loadSettings())
      .finally(() => setIsReady(true));
  }, []);

  if (!isReady) return null;

  return <>{children}</>;
}

/**
 * Apply or remove safe i18n overrides based on feature flag mode.
 * Call from a component rendered inside FeatureFlagProvider.
 */
export function applySafeOverrides(mode: "conservative" | "standard") {
  if (mode === "conservative") {
    i18n.addResourceBundle("en", "translation", enSafe, true, true);
    i18n.addResourceBundle("es", "translation", esSafe, true, true);
  } else {
    // Restore base translations (remove safe overrides)
    i18n.addResourceBundle("en", "translation", en, true, false);
    i18n.addResourceBundle("es", "translation", es, true, false);
  }
}

export { i18n };
