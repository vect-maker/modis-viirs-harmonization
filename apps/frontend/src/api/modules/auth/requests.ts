import { z } from "zod";

export const RegisterRequestSchema = z.object({
  email: z.email(),
  username: z
    .string()
    .min(3)
    .max(64)
    .regex(/^[a-zA-Z0-9_.-]+$/),
  password: z.string().min(8).max(128),
});

export const AuthenticateRequestSchema = z.object({
  email: z.email(),
  password: z.string().min(1).max(128),
});

export const UpdateProfileRequestSchema = z.object({
  username: z
    .string()
    .min(3)
    .max(64)
    .regex(/^[a-zA-Z0-9_.-]+$/)
    .optional(),
  email: z.email().optional(),
});
