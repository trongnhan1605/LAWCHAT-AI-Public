import { enMetadata } from "./en";
import { viMetadata } from "./vi";
import type { Locale } from "./types";

const METADATA = {
  vi: viMetadata,
  en: enMetadata,
};

export function translateTicketStatus(locale: Locale, status: string | null | undefined): string {
  if (!status) {
    return "--";
  }
  return METADATA[locale].ticketStatus[status] ?? status;
}

export function translateSessionStatus(locale: Locale, status: string | null | undefined): string {
  if (!status) {
    return "--";
  }
  return METADATA[locale].sessionStatus[status] ?? status;
}

export function translatePriority(locale: Locale, priority: string | null | undefined): string {
  if (!priority) {
    return "--";
  }
  return METADATA[locale].priority[priority] ?? priority;
}

export function translateTopic(locale: Locale, topic: string | null | undefined): string {
  if (!topic) {
    return METADATA[locale].topic.unknown ?? topic ?? "--";
  }
  return METADATA[locale].topic[topic] ?? topic;
}

export function translateSourceType(locale: Locale, sourceType: string | null | undefined): string {
  if (!sourceType) {
    return "--";
  }
  return METADATA[locale].sourceType[sourceType] ?? sourceType.toUpperCase();
}

export function translateBooleanState(locale: Locale, isActive: boolean): string {
  return isActive ? METADATA[locale].booleanState.active : METADATA[locale].booleanState.inactive;
}

export function translateAdminTabLabel(locale: Locale, tab: string): string {
  return METADATA[locale].adminTabLabel[tab] ?? tab;
}

export function translateAdminTabDescription(locale: Locale, tab: string): string {
  return METADATA[locale].adminTabDescription[tab] ?? tab;
}