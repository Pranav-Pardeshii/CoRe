import { getAuthSession, handleUnauthorizedSession } from "./authSession";
import {
  ApiClientError,
  type ErrorContext,
  extractDetailText,
  mapHttpErrorToHumanMessage,
} from "./errors";
import type {
  CatalogFiltersResponse,
  RecommenderParams,
  RecommenderResponse,
  RegisterResponse,
  SavedListMessageResponse,
  SavedListResponse,
  TokenResponse,
  TrendsResponse,
} from "./types";

export const REQUEST_TIMEOUT_MS = 15_000;

export function getApiBaseUrl(): string {
  const raw = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000").trim();
  const normalized = raw.replace(/\/+$/, "");
  return normalized || "http://127.0.0.1:8000";
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  params?: Record<string, string | number | undefined | null>;
  jsonBody?: unknown;
  formBody?: Record<string, string>;
  token?: string | null;
  requireAuth?: boolean;
  context: ErrorContext;
  signal?: AbortSignal;
}

function buildUrl(
  path: string,
  params?: Record<string, string | number | undefined | null>,
): string {
  const base = `${getApiBaseUrl()}${path}`;
  if (!params) {
    return base;
  }
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && String(value) !== "") {
      search.set(key, String(value));
    }
  }
  const queryString = search.toString();
  return queryString ? `${base}?${queryString}` : base;
}

async function safeParseJson(response: Response): Promise<{ ok: boolean; data: unknown }> {
  let rawText = "";
  try {
    rawText = await response.text();
  } catch {
    return { ok: false, data: null };
  }

  const trimmed = rawText.trim();
  if (!trimmed) {
    return { ok: false, data: null };
  }

  const contentType = (response.headers.get("content-type") ?? "").toLowerCase();
  const looksLikeJson = trimmed.startsWith("{") || trimmed.startsWith("[");
  if (!contentType.includes("application/json") && !looksLikeJson) {
    return { ok: false, data: null };
  }

  try {
    return { ok: true, data: JSON.parse(trimmed) as unknown };
  } catch {
    return { ok: false, data: null };
  }
}

export async function requestApi<T>(path: string, options: RequestOptions): Promise<T> {
  const {
    method = "GET",
    params,
    jsonBody,
    formBody,
    token,
    requireAuth = false,
    context,
    signal,
  } = options;

  const activeToken = token ?? (requireAuth ? getAuthSession()?.token ?? null : null);
  if (requireAuth && !activeToken) {
    handleUnauthorizedSession();
    throw new ApiClientError("Your session timed out. Sign in again to view your saved list.", {
      status: 401,
      isUnauthorized: true,
    });
  }

  const headers: Record<string, string> = {};
  let body: string | undefined;

  if (activeToken) {
    headers.Authorization = `Bearer ${activeToken}`;
  }

  if (formBody) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    body = new URLSearchParams(formBody).toString();
  } else if (jsonBody !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(jsonBody);
  }

  const controller = new AbortController();
  let timedOut = false;
  const timeoutId = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, REQUEST_TIMEOUT_MS);

  const onExternalAbort = () => controller.abort();
  if (signal) {
    if (signal.aborted) {
      clearTimeout(timeoutId);
      throw new DOMException("Aborted", "AbortError");
    }
    signal.addEventListener("abort", onExternalAbort, { once: true });
  }

  try {
    const response = await fetch(buildUrl(path, params), {
      method,
      headers,
      body,
      signal: controller.signal,
    });

    if (response.status === 401 && (requireAuth || activeToken !== null)) {
      handleUnauthorizedSession();
      throw new ApiClientError(
        mapHttpErrorToHumanMessage(401, context),
        { status: 401, isUnauthorized: true },
      );
    }

    const parsed = await safeParseJson(response);

    if (!response.ok) {
      if (!parsed.ok && (response.status === 502 || response.status === 503 || response.status === 504)) {
        throw new ApiClientError("Service is temporarily busy. Please try again in a moment.", {
          status: response.status,
        });
      }
      const detail = parsed.ok ? extractDetailText(parsed.data) : "";
      throw new ApiClientError(mapHttpErrorToHumanMessage(response.status, context, detail), {
        status: response.status,
      });
    }

    if (!parsed.ok) {
      throw new ApiClientError(mapHttpErrorToHumanMessage(500, context), {
        status: response.status,
      });
    }

    return parsed.data as T;
  } catch (err: unknown) {
    if (err instanceof ApiClientError) {
      throw err;
    }
    if (err instanceof DOMException && err.name === "AbortError") {
      if (timedOut) {
        throw new ApiClientError("That took longer than expected. Please try again.", {
          status: 0,
          isTimeout: true,
        });
      }
      throw err;
    }
    throw new ApiClientError("Couldn't connect right now. Check your internet and try again.", {
      status: 0,
    });
  } finally {
    clearTimeout(timeoutId);
    signal?.removeEventListener("abort", onExternalAbort);
  }
}

export function fetchCatalogFilters(signal?: AbortSignal): Promise<CatalogFiltersResponse> {
  return requestApi<CatalogFiltersResponse>("/catalog/filters", {
    method: "GET",
    context: "catalog",
    signal,
  });
}

export function fetchRecommendations(
  params: RecommenderParams,
  signal?: AbortSignal,
): Promise<RecommenderResponse> {
  return requestApi<RecommenderResponse>("/recommender/", {
    method: "GET",
    params: {
      percentile: params.percentile,
      category: params.category,
      branch: params.branch,
      division: params.division,
      page: params.page,
      page_size: params.page_size,
    },
    context: "recommender",
    signal,
  });
}

export function fetchTrends(
  branchCode: string,
  category: string,
  level?: string,
  signal?: AbortSignal,
): Promise<TrendsResponse> {
  return requestApi<TrendsResponse>("/trends/", {
    method: "GET",
    params: {
      branch_code: branchCode,
      category,
      level,
    },
    context: "trends",
    signal,
  });
}

export function registerUser(username: string, password: string): Promise<RegisterResponse> {
  return requestApi<RegisterResponse>("/auth/register", {
    method: "POST",
    jsonBody: { username, password },
    context: "auth-register",
  });
}

export function loginUser(username: string, password: string): Promise<TokenResponse> {
  return requestApi<TokenResponse>("/auth/login", {
    method: "POST",
    formBody: { username, password },
    context: "auth-login",
  });
}

export function fetchSavedList(token?: string): Promise<SavedListResponse> {
  return requestApi<SavedListResponse>("/saved-lists/", {
    method: "GET",
    token,
    requireAuth: true,
    context: "saved-list-read",
  });
}

export function addSavedListItem(
  branchCode: string,
  token?: string,
): Promise<SavedListMessageResponse> {
  return requestApi<SavedListMessageResponse>("/saved-lists/", {
    method: "POST",
    jsonBody: { branch_code: branchCode },
    token,
    requireAuth: true,
    context: "saved-list-add",
  });
}

export function deleteSavedListItem(
  itemId: number,
  token?: string,
): Promise<SavedListMessageResponse> {
  return requestApi<SavedListMessageResponse>(`/saved-lists/${itemId}`, {
    method: "DELETE",
    token,
    requireAuth: true,
    context: "saved-list-delete",
  });
}

export function reorderSavedList(
  orderedIds: number[],
  token?: string,
): Promise<SavedListMessageResponse> {
  return requestApi<SavedListMessageResponse>("/saved-lists/", {
    method: "PUT",
    jsonBody: { ordered_list: orderedIds },
    token,
    requireAuth: true,
    context: "saved-list-reorder",
  });
}
