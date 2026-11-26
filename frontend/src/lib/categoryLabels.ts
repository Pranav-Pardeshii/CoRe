const PREFIXES: ReadonlyArray<readonly [string, string]> = [
  ["PWDR", "PWD (Common Reserved)"],
  ["DEFR", "Defence (Common Reserved)"],
  ["PWD", "Persons with Disability"],
  ["DEF", "Defence"],
  ["G", "General"],
  ["L", "Ladies-only"],
];

const MIDDLE_CATEGORIES: ReadonlyArray<readonly [string, string]> = [
  ["SEBC", "SEBC"],
  ["OPEN", "Open"],
  ["OBC", "OBC"],
  ["SC", "SC"],
  ["ST", "ST"],
  ["VJ", "VJ"],
  ["NT1", "NT1"],
  ["NT2", "NT2"],
  ["NT3", "NT3"],
];

const SUFFIXES: ReadonlyArray<readonly [string, string]> = [
  ["SS", "State Level"],
  ["S", "State Level"],
  ["H", "Home University"],
  ["O", "Other than Home University"],
];

const STANDALONE: Readonly<Record<string, string>> = {
  TFWS: "Tuition Fee Waiver Scheme",
  EWS: "Economically Weaker Section",
  EWSS: "Economically Weaker Section (State Level)",
  ORPHAN: "Orphan Quota",
  ORPHANS: "Orphan Quota (State Level)",
  MI: "Minority Quota",
  AI: "All India Quota",
};

const LEVEL_LABELS: Readonly<Record<string, string>> = {
  SL: "State Level",
  HU_HU: "Home University (Home Seat)",
  HU_OHU: "Home University (Other Univ. Seat)",
  OHU_HU: "Other Univ. (Home Seat)",
  OHU_OHU: "Other Univ. (Other Seat)",
};

export interface DecodedCategory {
  code: string;
  label: string;
  displayText: string;
}

/**
 * Decode an MHT-CET CAP category code (e.g. "GOPENS", "LOBCH", "TFWS", "All")
 * into plain English alongside the official CET code.
 */
export function decodeCategory(rawCode: string): DecodedCategory {
  const cleaned = rawCode.trim();
  if (!cleaned) {
    return { code: rawCode, label: "Unknown Category", displayText: rawCode };
  }

  if (cleaned.toLowerCase() === "all") {
    return {
      code: "All",
      label: "All Categories",
      displayText: "All Categories (All)",
    };
  }

  const standaloneLabel = STANDALONE[cleaned];
  if (standaloneLabel) {
    return {
      code: cleaned,
      label: standaloneLabel,
      displayText: `${standaloneLabel} (${cleaned})`,
    };
  }

  let remaining = cleaned;
  let prefixLabel: string | null = null;
  for (const [prefixCode, label] of PREFIXES) {
    if (remaining.startsWith(prefixCode)) {
      prefixLabel = label;
      remaining = remaining.slice(prefixCode.length);
      break;
    }
  }

  let suffixLabel: string | null = null;
  for (const [suffixCode, label] of SUFFIXES) {
    if (remaining.endsWith(suffixCode) && remaining.length > suffixCode.length) {
      suffixLabel = label;
      remaining = remaining.slice(0, -suffixCode.length);
      break;
    }
  }

  let middleLabel: string | null = null;
  for (const [middleCode, label] of MIDDLE_CATEGORIES) {
    if (remaining === middleCode) {
      middleLabel = label;
      break;
    }
  }

  if (prefixLabel && middleLabel && suffixLabel) {
    const label = `${prefixLabel} ${middleLabel} — ${suffixLabel}`;
    return {
      code: cleaned,
      label,
      displayText: `${label} (${cleaned})`,
    };
  }

  if (prefixLabel && middleLabel) {
    const label = `${prefixLabel} ${middleLabel}`;
    return {
      code: cleaned,
      label,
      displayText: `${label} (${cleaned})`,
    };
  }

  return {
    code: cleaned,
    label: cleaned,
    displayText: cleaned,
  };
}

export function formatCategoryDisplay(code: string): string {
  return decodeCategory(code).displayText;
}

export function decodeSeatLevel(level: string): string {
  return LEVEL_LABELS[level] ?? level;
}
