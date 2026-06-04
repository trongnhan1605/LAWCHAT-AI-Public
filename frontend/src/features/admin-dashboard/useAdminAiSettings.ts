import { useEffect, useState } from "react";

import type { AdminDashboardProps } from "./types";
import { CHATBOT_PROVIDER_MODEL_OPTIONS, METADATA_PROVIDER_MODEL_OPTIONS } from "./helpers";

type UseAdminAiSettingsParams = Pick<AdminDashboardProps, "adminData" | "savingAdmin" | "onUpdateMetadataSettings">;

export function useAdminAiSettings({ adminData, savingAdmin, onUpdateMetadataSettings }: UseAdminAiSettingsParams) {
  const [metadataEnabled, setMetadataEnabled] = useState(false);
  const [metadataProvider, setMetadataProvider] = useState("openai");
  const [metadataModel, setMetadataModel] = useState("gpt-4.1-mini");
  const [metadataWebSearchEnabled, setMetadataWebSearchEnabled] = useState(false);
  const [embeddingEnabled, setEmbeddingEnabled] = useState(false);
  const [embeddingModel, setEmbeddingModel] = useState("text-embedding-3-small");
  const [chatbotEnabled, setChatbotEnabled] = useState(false);
  const [chatbotProvider, setChatbotProvider] = useState("openai");
  const [publicChatbotModel, setPublicChatbotModel] = useState("gpt-4.1-mini");
  const [customerChatbotModel, setCustomerChatbotModel] = useState("gpt-4.1-mini");
  const [consultantChatbotModel, setConsultantChatbotModel] = useState("gpt-4.1-mini");
  const [graphBackend, setGraphBackend] = useState("relational");

  useEffect(() => {
    if (!adminData?.metadata_ai_settings) {
      return;
    }
    setMetadataEnabled(adminData.metadata_ai_settings.enabled);
    setMetadataProvider(adminData.metadata_ai_settings.provider);
    setMetadataModel(adminData.metadata_ai_settings.model);
    setMetadataWebSearchEnabled(adminData.metadata_ai_settings.web_search_enabled);
    setEmbeddingEnabled(adminData.embedding_ai_settings.enabled);
    setEmbeddingModel(adminData.embedding_ai_settings.model);
    setChatbotEnabled(adminData.chatbot_ai_settings.enabled);
    setChatbotProvider(adminData.chatbot_ai_settings.provider);
    setPublicChatbotModel(adminData.chatbot_ai_settings.public_model);
    setCustomerChatbotModel(adminData.chatbot_ai_settings.customer_model);
    setConsultantChatbotModel(adminData.chatbot_ai_settings.consultant_model);
    setGraphBackend(adminData.graph_backend_settings.backend);
  }, [adminData?.chatbot_ai_settings, adminData?.embedding_ai_settings, adminData?.graph_backend_settings, adminData?.metadata_ai_settings]);

  useEffect(() => {
    const availableModels = METADATA_PROVIDER_MODEL_OPTIONS[metadataProvider] ?? [];
    if (availableModels.length > 0 && !availableModels.includes(metadataModel)) {
      setMetadataModel(availableModels[0]);
    }
  }, [metadataModel, metadataProvider]);

  useEffect(() => {
    const availableModels = CHATBOT_PROVIDER_MODEL_OPTIONS[chatbotProvider] ?? [];
    if (availableModels.length === 0) {
      return;
    }
    if (!availableModels.includes(publicChatbotModel)) {
      setPublicChatbotModel(availableModels[0]);
    }
    if (!availableModels.includes(customerChatbotModel)) {
      setCustomerChatbotModel(availableModels[0]);
    }
    if (!availableModels.includes(consultantChatbotModel)) {
      setConsultantChatbotModel(availableModels[0]);
    }
  }, [chatbotProvider, publicChatbotModel, customerChatbotModel, consultantChatbotModel]);

  async function handleMetadataSettingsSubmit() {
    if (!adminData?.metadata_ai_settings || savingAdmin) {
      return;
    }
    await onUpdateMetadataSettings(
      metadataEnabled,
      metadataProvider,
      metadataModel,
      metadataWebSearchEnabled,
      embeddingEnabled,
      embeddingModel,
      chatbotEnabled,
      chatbotProvider,
      publicChatbotModel,
      customerChatbotModel,
      consultantChatbotModel,
      graphBackend,
    );
  }

  return {
    chatbotEnabled,
    chatbotProvider,
    consultantChatbotModel,
    customerChatbotModel,
    embeddingEnabled,
    embeddingModel,
    graphBackend,
    metadataEnabled,
    metadataModel,
    metadataProvider,
    metadataWebSearchEnabled,
    publicChatbotModel,
    setChatbotEnabled,
    setChatbotProvider,
    setConsultantChatbotModel,
    setCustomerChatbotModel,
    setEmbeddingEnabled,
    setEmbeddingModel,
    setGraphBackend,
    setMetadataEnabled,
    setMetadataModel,
    setMetadataProvider,
    setMetadataWebSearchEnabled,
    setPublicChatbotModel,
    handleMetadataSettingsSubmit,
  };
}
