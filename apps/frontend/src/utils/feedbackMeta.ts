import type { FeedbackClassification, FeedbackSeverity } from "@/api";

export interface ClassificationMeta {
  value: FeedbackClassification;
  label: string;
  badgeClass: string;
}

export const FEEDBACK_CLASSIFICATIONS: ClassificationMeta[] = [
  {
    value: "confirmed_wildfire",
    label: "Confirmed Wildfire",
    badgeClass: "border-red-400/40 bg-red-500/15 text-red-300",
  },
  {
    value: "agricultural_burn",
    label: "Agricultural Burn",
    badgeClass: "border-amber-400/40 bg-amber-500/15 text-amber-300",
  },
  {
    value: "industrial_or_flare",
    label: "Industrial / Flare",
    badgeClass: "border-sky-400/40 bg-sky-500/15 text-sky-300",
  },
  {
    value: "false_positive",
    label: "False Positive",
    badgeClass: "border-emerald-400/40 bg-emerald-500/15 text-emerald-300",
  },
  {
    value: "uncertain",
    label: "Uncertain",
    badgeClass: "border-border-strong bg-surface-elevated text-ink-muted",
  },
];

export const CLASSIFICATION_META_MAP: Record<FeedbackClassification, ClassificationMeta> =
  Object.fromEntries(FEEDBACK_CLASSIFICATIONS.map((item) => [item.value, item])) as Record<
    FeedbackClassification,
    ClassificationMeta
  >;

export const FEEDBACK_SEVERITIES: Array<{ value: FeedbackSeverity; label: string }> = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
];
