import axios from "axios";

import { lawChatApi } from "../../api/lawchat.api";
import type { AdminUserWritePayload } from "../../types/lawchat";
import type { SharedAdminOperationParams } from "./types";

export function useAdminUsersManager({
  loadAdminOperations,
  savingAdmin,
  setError,
  setSavingAdmin,
  ui,
}: SharedAdminOperationParams) {
  async function handleCreateAdminUser(payload: AdminUserWritePayload) {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.createAdminUser(payload);
      await loadAdminOperations();
    } catch (caught) {
      setError(axios.isAxiosError(caught) ? (caught.response?.data?.message ?? ui.appCreateUserError) : ui.appCreateUserError);
      throw new Error("create-user-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  async function handleUpdateAdminUser(userId: number, payload: AdminUserWritePayload) {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.updateAdminUser(userId, payload);
      await loadAdminOperations();
    } catch (caught) {
      setError(axios.isAxiosError(caught) ? (caught.response?.data?.message ?? ui.appUpdateUserError) : ui.appUpdateUserError);
      throw new Error("update-user-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  async function handleDeleteAdminUser(userId: number) {
    if (savingAdmin) {
      return;
    }
    setSavingAdmin(true);
    try {
      await lawChatApi.deleteAdminUser(userId);
      await loadAdminOperations();
    } catch (caught) {
      setError(axios.isAxiosError(caught) ? (caught.response?.data?.message ?? ui.appDeleteUserError) : ui.appDeleteUserError);
      throw new Error("delete-user-failed");
    } finally {
      setSavingAdmin(false);
    }
  }

  return {
    handleCreateAdminUser,
    handleDeleteAdminUser,
    handleUpdateAdminUser,
  };
}
