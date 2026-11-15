import { z } from "zod";

export const FeedbackClassificationSchema = z.enum([
  "confirmed_wildfire",
  "agricultural_burn",
  "industrial_or_flare",
  "false_positive",
  "uncertain",
]);

export const FeedbackSeveritySchema = z.enum([
  "low",
  "medium",
  "high",
  "critical",
]);
