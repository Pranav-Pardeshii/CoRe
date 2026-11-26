import { queryClient } from "./queryClient";

export interface AuthCredentials {
  token: string;
  username: string;
}

const STORAGE_KEY = "core_auth_session";

type SessionListener = () => void;

const listeners = new Set<SessionListener>();
let memoryCredentials: AuthCredentials | null = null;
let sessionBannerMessage: string | null = null;

function readStorage(): AuthCredentials | null {
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<AuthCredentials>;
    if (typeof parsed.token === "string" && parsed.token && typeof parsed.username === "string") {
      return { token: parsed.token, username: parsed.username };
    }
    return null;
  } catch {
    return null;
  }
}

function writeStorage(credentials: AuthCredentials | null): void {
  try {
    if (credentials === null) {
      window.sessionStorage.removeItem(STORAGE_KEY);
    } else {
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(credentials));
    }
  } catch {
    // Ignore storage unavailability (private browsing / restricted iframes).
  }
}

function emitChange(): void {
  for (const listener of listeners) {
    listener();
  }
}

export function getAuthSession(): AuthCredentials | null {
  if (memoryCredentials) {
    return memoryCredentials;
  }
  const fromStorage = readStorage();
  if (fromStorage) {
    memoryCredentials = fromStorage;
  }
  return memoryCredentials;
}

export function getSessionBanner(): string | null {
  return sessionBannerMessage;
}

export function dismissSessionBanner(): void {
  sessionBannerMessage = null;
  emitChange();
}

export function setAuthSession(credentials: AuthCredentials): void {
  queryClient.clear();
  memoryCredentials = credentials;
  sessionBannerMessage = null;
  writeStorage(credentials);
  emitChange();
}

export function clearAuthSession(bannerMessage?: string): void {
  memoryCredentials = null;
  writeStorage(null);
  queryClient.clear();
  sessionBannerMessage = bannerMessage ?? null;
  emitChange();
}

export function handleUnauthorizedSession(): void {
  clearAuthSession("Your session timed out. Sign in again to view your saved list.");
}

export function subscribeAuthSession(listener: SessionListener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
