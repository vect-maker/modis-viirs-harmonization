import { z } from "zod";

export const UserPublicSchema = z.object({
  id: z.uuid(),
  email: z.email(),
  username: z.string(),
  role: z.string(),
  is_active: z.boolean(),
  created_at: z.iso.datetime({ offset: true }),
});
