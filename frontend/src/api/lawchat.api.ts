import { adminApi } from "./admin.api";
import { chatApi } from "./chat.api";
import { knowledgeApi } from "./knowledge.api";
import { ticketsApi } from "./tickets.api";

export const lawChatApi = {
  ...chatApi,
  ...knowledgeApi,
  ...ticketsApi,
  ...adminApi,
};
