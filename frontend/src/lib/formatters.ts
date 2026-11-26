import type { SavedListItem } from "../api/types";

export type MarginStatus = "safe" | "competitive" | "borderline";

export interface MarginAssessment {
  status: MarginStatus;
  label: string;
  symbol: string;
  detail: string;
}

/**
 * Format a percentile cleanly to 7 decimal places for tabular numeric alignment.
 */
export function formatPercentile(value: number): string {
  if (!Number.isFinite(value)) {
    return "0.0000000";
  }
  return value.toFixed(7);
}

/**
 * Format a percentile concisely for compact chart axes (2 decimals) while preserving precision in tables/tooltips.
 */
export function formatAxisPercentile(value: number): string {
  if (!Number.isFinite(value)) {
    return "0";
  }
  return Number.isInteger(value) ? value.toFixed(0) : value.toFixed(2);
}

/**
 * Assess how comfortably the student's percentile clears the historical cutoff range.
 * Always pairs status with a text label and geometric symbol (never color alone).
 */
export function assessCutoffMargin(
  userPercentile: number,
  minCutoff: number,
  maxCutoff: number,
): MarginAssessment {
  if (userPercentile >= maxCutoff) {
    const diff = userPercentile - maxCutoff;
    return {
      status: "safe",
      label: "Safe margin",
      symbol: "●",
      detail: `+${diff.toFixed(4)} above past peak`,
    };
  }
  if (userPercentile >= minCutoff + 0.5) {
    return {
      status: "competitive",
      label: "In range",
      symbol: "◐",
      detail: "Within recent round range",
    };
  }
  return {
    status: "borderline",
    label: "Borderline",
    symbol: "△",
    detail: "Close to lowest recent cutoff",
  };
}

/**
 * Sanitize raw user percentile text input: digits and at most one decimal point with up to 7 decimal places.
 */
export function sanitizePercentileInput(raw: string): string {
  const cleaned = raw.replace(/[^0-9.]/g, "");
  const dotIndex = cleaned.indexOf(".");
  if (dotIndex === -1) {
    return cleaned;
  }
  const integerPart = cleaned.slice(0, dotIndex);
  const fractionalPart = cleaned.slice(dotIndex + 1).replace(/\./g, "").slice(0, 7);
  return `${integerPart}.${fractionalPart}`;
}

/**
 * Validate a percentile string against MHT-CET bounds [0, 100].
 */
export function parsePercentileInput(raw: string): number | null {
  const trimmed = raw.trim();
  if (!trimmed || trimmed === ".") {
    return null;
  }
  const numeric = Number(trimmed);
  if (!Number.isFinite(numeric) || numeric < 0 || numeric > 100) {
    return null;
  }
  return numeric;
}

function escapeCsvCell(value: string): string {
  const normalized = value.replace(/\r?\n/g, " ").trim();
  const safePrefix = /^[=+\-@]/.test(normalized) ? `'${normalized}` : normalized;
  return `"${safePrefix.replace(/"/g, '""')}"`;
}

/**
 * Build a CSV export string for the ordered CAP Option Form shortlist.
 */
export function buildShortlistCsv(items: readonly SavedListItem[]): string {
  const header = "Preference Order,College Name,Branch Name";
  const rows = items.map(
    (item, index) =>
      `${index + 1},${escapeCsvCell(item.college_name)},${escapeCsvCell(item.branch_name)}`,
  );
  return [header, ...rows].join("\r\n");
}

export function buildShortlistPlainText(items: readonly SavedListItem[]): string {
  return items
    .map((item, index) => `${index + 1}. ${item.college_name} — ${item.branch_name}`)
    .join("\n");
}
