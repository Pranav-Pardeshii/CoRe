export type ErrorContext =
  | "catalog"
  | "recommender"
  | "trends"
  | "auth-login"
  | "auth-register"
  | "saved-list-read"
  | "saved-list-add"
  | "saved-list-delete"
  | "saved-list-reorder"
  | "generic";

export class ApiClientError extends Error {
  readonly status: number;
  readonly isTimeout: boolean;
  readonly isUnauthorized: boolean;

  constructor(
    message: string,
    options: { status?: number; isTimeout?: boolean; isUnauthorized?: boolean } = {},
  ) {
    super(message);
    this.name = "ApiClientError";
    this.status = options.status ?? 0;
    this.isTimeout = options.isTimeout ?? false;
    this.isUnauthorized = options.isUnauthorized ?? false;
  }
}

/**
 * Extract backend detail text for internal matching only—never surfaced raw to users.
 */
export function extractDetailText(payload: unknown): string {
  if (typeof payload !== "object" || payload === null) {
    return "";
  }
  const record = payload as Record<string, unknown>;
  const detail = record.detail;
  if (typeof detail === "string") {
    return detail.toLowerCase();
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "object" && item !== null && "msg" in item) {
          return String((item as Record<string, unknown>).msg);
        }
        return String(item);
      })
      .join(" ")
      .toLowerCase();
  }
  return "";
}

/**
 * Translate every HTTP status, network error, or timeout into calm, plain admissions English.
 * Strictly prohibits technical/backend jargon (FastAPI, API, backend, server, MySQL, JWT, etc.).
 */
export function mapHttpErrorToHumanMessage(
  status: number,
  context: ErrorContext,
  rawDetail = "",
): string {
  const detail = rawDetail.toLowerCase();

  if (status === 429) {
    return "Too many attempts in a short time. Please wait a minute and try again.";
  }

  if (status === 401) {
    if (context === "auth-login") {
      return "That username or password didn't match. Please check and try again.";
    }
    return "Your session timed out. Sign in again to view your saved list.";
  }

  if (status === 409) {
    if (context === "auth-register") {
      return "That username is already taken. Try choosing another one.";
    }
    if (context === "saved-list-add") {
      return "This college and branch is already in your shortlist.";
    }
    return "This item already exists. Please refresh and try again.";
  }

  if (status === 400 || status === 404 || status === 422) {
    if (context === "saved-list-add") {
      if (detail.includes("limit") || detail.includes("100")) {
        return "Your shortlist has reached the 100-item limit. Remove an item to add another.";
      }
      return "Couldn't save this college choice right now. Please try again.";
    }
    if (context === "saved-list-delete" || context === "saved-list-reorder") {
      return "Your saved list changed elsewhere. Refreshing your latest shortlist.";
    }
    if (context === "auth-register") {
      return "Please check that your username and password meet the length rules.";
    }
    if (context === "recommender") {
      return "Please enter a percentile between 0 and 100 and check your filters.";
    }
    return "Please check your entries and try again.";
  }

  if (status >= 500) {
    if (context === "catalog") {
      return "Couldn't load categories and branches right now. Please try again.";
    }
    if (context === "trends") {
      return "Couldn't load cutoff history for this branch right now.";
    }
    if (context === "recommender") {
      return "Couldn't load colleges right now. Please try again.";
    }
    return "Something went wrong on our side. Please try again in a moment.";
  }

  if (context === "catalog") {
    return "Couldn't load categories and branches right now. Please try again.";
  }
  if (context === "recommender") {
    return "Couldn't load colleges right now. Please try again.";
  }
  if (context === "trends") {
    return "Couldn't load cutoff history right now. Please try again.";
  }
  return "Couldn't complete your request right now. Please try again.";
}
