import { create } from "zustand";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { i18n } from "../providers/I18nProvider";

interface SettingsStore {
  language: "es" | "en";
  notificationsEnabled: boolean;
  preferredNetwork: string;
  setLanguage: (lang: "es" | "en") => void;
  setNotificationsEnabled: (enabled: boolean) => void;
  setPreferredNetwork: (network: string) => void;
  loadSettings: () => Promise<void>;
}

export const useSettingsStore = create<SettingsStore>((set) => ({
  language: "es",
  notificationsEnabled: true,
  preferredNetwork: "base",
  setLanguage: (language) => {
    set({ language });
    i18n.changeLanguage(language);
    AsyncStorage.setItem("em_language", language);
  },
  setNotificationsEnabled: (notificationsEnabled) => {
    set({ notificationsEnabled });
    AsyncStorage.setItem("em_notifications", String(notificationsEnabled));
  },
  setPreferredNetwork: (preferredNetwork) => {
    set({ preferredNetwork });
    AsyncStorage.setItem("em_network", preferredNetwork);
  },
  loadSettings: async () => {
    const [lang, notif, network] = await Promise.all([
      AsyncStorage.getItem("em_language"),
      AsyncStorage.getItem("em_notifications"),
      AsyncStorage.getItem("em_network"),
    ]);
    const updates: Partial<SettingsStore> = {};
    if (lang === "es" || lang === "en") updates.language = lang;
    if (notif !== null) updates.notificationsEnabled = notif === "true";
    if (network) updates.preferredNetwork = network;
    set(updates);
  },
}));
