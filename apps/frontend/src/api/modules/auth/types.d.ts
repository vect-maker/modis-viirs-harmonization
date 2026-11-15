import type { z } from "zod";
import type {
  AuthenticateRequestSchema,
  RegisterRequestSchema,
  UpdateProfileRequestSchema,
} from "./requests";
import type { UserPublicSchema } from "./responses";

export type RegisterRequest = z.infer<typeof RegisterRequestSchema>;
export type AuthenticateRequest = z.infer<typeof AuthenticateRequestSchema>;
export type UpdateProfileRequest = z.infer<typeof UpdateProfileRequestSchema>;
export type UserPublic = z.infer<typeof UserPublicSchema>;
