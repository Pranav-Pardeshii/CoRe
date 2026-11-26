import { createContext, useCallback, useContext, useSyncExternalStore } from "react";
import {
  clearAuthSession,
  dismissSessionBanner,
  getAuthSession,
  getSessionBanner,
  setAuthSession,
  subscribeAuthSession,
} from "../api/authSession";
import { loginUser, registerUser } from "../api/client";
import { queryClient } from "../api/queryClient";

interface AuthContextValue {
  isAuthenticated: boolean;
  username: string | null;
  token: string | null;
  sessionBanner: string | null;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => void;
  dismissBanner: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const USERNAME_REGEX = /^[A-Za-z0-9_.-]{3,50}$/;

export function validateAuthInputs(
  username: string,
  password: string,
  mode: "login" | "register",
): string | null {
  const cleanedUsername = username.trim();
  if (!cleanedUsername || !password) {
    return "Enter both your username and password.";
  }
  if (mode === "register") {
    if (!USERNAME_REGEX.test(cleanedUsername)) {
      return "Username must be 3–50 characters using letters, digits, '.', '_', or '-'.";
    }
    if (password.length < 8 || password.length > 128) {
      return "Password must be between 8 and 128 characters.";
    }
  }
  return null;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const session = useSyncExternalStore(
    subscribeAuthSession,
    getAuthSession,
    () => null,
  );
  const sessionBanner = useSyncExternalStore(
    subscribeAuthSession,
    getSessionBanner,
    () => null,
  );

  const login = useCallback(async (username: string, password: string) => {
    const cleaned = username.trim();
    // Clear cached user data immediately before completing a new login.
    queryClient.clear();
    const res = await loginUser(cleaned, password);
    setAuthSession({ token: res.access_token, username: cleaned });
  }, []);

  const register = useCallback(async (username: string, password: string) => {
    await registerUser(username.trim(), password);
  }, []);

  const logout = useCallback(() => {
    clearAuthSession();
  }, []);

  const dismissBanner = useCallback(() => {
    dismissSessionBanner();
  }, []);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: Boolean(session?.token),
        username: session?.username ?? null,
        token: session?.token ?? null,
        sessionBanner,
        login,
        register,
        logout,
        dismissBanner,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}
