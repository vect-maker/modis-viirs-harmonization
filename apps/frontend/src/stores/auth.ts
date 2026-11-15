import { defineStore } from "pinia";
import { computed, ref } from "vue";
import type {
  AuthenticateRequest,
  RegisterRequest,
  UpdateProfileRequest,
  UserPublic,
} from "@/api";
import { useAuthApi } from "@/api";

export const useAuthStore = defineStore("auth", () => {
  const authApi = useAuthApi();

  const user = ref<UserPublic | null>(null);
  const isInitialized = ref(false);
  const isSubmitting = ref(false);
  const error = ref<string | null>(null);

  let pendingInit: Promise<void> | null = null;

  const isAuthenticated = computed(() => user.value !== null);

  function clearError() {
    error.value = null;
  }

  async function initSession(): Promise<void> {
    if (isInitialized.value) return;
    if (pendingInit) return pendingInit;

    pendingInit = (async () => {
      try {
        user.value = await authApi.getMe();
      } catch {
        user.value = null;
      } finally {
        isInitialized.value = true;
        pendingInit = null;
      }
    })();

    return pendingInit;
  }

  async function login(payload: AuthenticateRequest): Promise<UserPublic> {
    isSubmitting.value = true;
    error.value = null;
    try {
      const authenticated = await authApi.authenticate(payload);
      user.value = authenticated;
      isInitialized.value = true;
      return authenticated;
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Authentication failed";
      throw err;
    } finally {
      isSubmitting.value = false;
    }
  }

  async function register(payload: RegisterRequest): Promise<UserPublic> {
    isSubmitting.value = true;
    error.value = null;
    try {
      return await authApi.register(payload);
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Registration failed";
      throw err;
    } finally {
      isSubmitting.value = false;
    }
  }

  async function updateProfile(payload: UpdateProfileRequest): Promise<UserPublic> {
    isSubmitting.value = true;
    error.value = null;
    try {
      const updated = await authApi.updateMe(payload);
      user.value = updated;
      return updated;
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Profile update failed";
      throw err;
    } finally {
      isSubmitting.value = false;
    }
  }

  async function logout(): Promise<void> {
    isSubmitting.value = true;
    error.value = null;
    try {
      await authApi.logout();
      user.value = null;
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Logout failed";
      throw err;
    } finally {
      isSubmitting.value = false;
    }
  }

  return {
    user,
    isInitialized,
    isSubmitting,
    error,
    isAuthenticated,
    clearError,
    initSession,
    login,
    register,
    updateProfile,
    logout,
  };
});
