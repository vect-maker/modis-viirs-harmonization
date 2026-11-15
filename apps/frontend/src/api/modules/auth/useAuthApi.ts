import { useApiFetch } from "@/api/useApiFetch";
import {
  AuthenticateRequestSchema,
  RegisterRequestSchema,
  UpdateProfileRequestSchema,
} from "./requests";
import { UserPublicSchema } from "./responses";
import type {
  AuthenticateRequest,
  RegisterRequest,
  UpdateProfileRequest,
  UserPublic,
} from "./types";

export const useAuthApi = () => {
  // POST /auth/register
  async function register(payload: RegisterRequest): Promise<UserPublic> {
    const validated = RegisterRequestSchema.parse(payload);
    const { data, error } = await useApiFetch("/auth/register").post(validated).json();

    if (error.value || !data.value) {
      throw error.value || new Error("Register request failed");
    }

    return UserPublicSchema.parse(data.value);
  }

  // POST /auth/authenticate
  async function authenticate(payload: AuthenticateRequest): Promise<UserPublic> {
    const validated = AuthenticateRequestSchema.parse(payload);
    const { data, error } = await useApiFetch("/auth/authenticate").post(validated).json();

    if (error.value || !data.value) {
      throw error.value || new Error("Authentication request failed");
    }

    return UserPublicSchema.parse(data.value);
  }

  // GET /auth/me
  async function getMe(): Promise<UserPublic> {
    const { data, error } = await useApiFetch("/auth/me").get().json();

    if (error.value || !data.value) {
      throw error.value || new Error("Failed to fetch current user");
    }

    return UserPublicSchema.parse(data.value);
  }

  // PATCH /auth/me
  async function updateMe(payload: UpdateProfileRequest): Promise<UserPublic> {
    const validated = UpdateProfileRequestSchema.parse(payload);
    const { data, error } = await useApiFetch("/auth/me").patch(validated).json();

    if (error.value || !data.value) {
      throw error.value || new Error("Failed to update profile");
    }

    return UserPublicSchema.parse(data.value);
  }

  // POST /auth/logout
  async function logout(): Promise<void> {
    const { error } = await useApiFetch("/auth/logout").post();

    if (error.value) {
      throw error.value || new Error("Logout request failed");
    }
  }

  return {
    register,
    authenticate,
    getMe,
    updateMe,
    logout,
  };
};
