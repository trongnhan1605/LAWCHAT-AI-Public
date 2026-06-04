import type { Dispatch, SetStateAction } from "react";

import type { KnowledgeOverview } from "../../types/lawchat";
import type { UiText } from "../../locales";

export type KnowledgeSetter = Dispatch<SetStateAction<KnowledgeOverview | null>>;

export type SharedAdminOperationParams = {
  loadAdminOperations: () => Promise<void>;
  savingAdmin: boolean;
  setError: (value: string | null) => void;
  setKnowledge: KnowledgeSetter;
  setSavingAdmin: Dispatch<SetStateAction<boolean>>;
  ui: UiText;
};

export type SharedDocumentOperationParams = SharedAdminOperationParams & {
  activeDocumentId: number | null;
};
