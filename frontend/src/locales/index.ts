import { enHomeContent, enText } from "./en";
import { viHomeContent, viText } from "./vi";
import type { HomeContent, Locale, UiText } from "./types";

const LOCALE_STORAGE_KEY = "lawchat.ui.locale";

export type { HomeContent, Locale, UiText } from "./types";

export const UI_TEXT: Record<Locale, UiText> = {
  vi: viText,
  en: enText,
};

export const HOME_CONTENT: Record<Locale, HomeContent> = {
  vi: viHomeContent,
  en: enHomeContent,
};

export function resolveStoredLocale(): Locale {
  if (typeof window === "undefined") {
    return "vi";
  }

  const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY);
  return stored === "en" ? "en" : "vi";
}