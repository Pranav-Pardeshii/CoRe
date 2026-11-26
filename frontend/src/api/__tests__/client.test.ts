import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  clearAuthSession,
  getAuthSession,
  getSessionBanner,
  setAuthSession,
} from "../authSession";
import { fetchRecommendations, fetchSavedList, loginUser } from "../client";
import { ApiClientError } from "../errors";
import { queryClient } from "../queryClient";

const BANNED_JARGON = [
  "FastAPI",
  "API",
  "backend",
  "server",
  "MySQL",
  "database",
  "JWT",
  "token",
  "endpoint",
  "Cloud Run",
  "401",
  "404",
  "500",
  "502",
  "503",
];

function assertNoBannedJargon(message: string) {
  for (const term of BANNED_JARGON) {
    expect(message.toLowerCase()).not.toContain(term.toLowerCase());
  }
}

describe("API client error & auth hygiene", () => {
  beforeEach(() => {
    clearAuthSession();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    clearAuthSession();
  });

  it("handles HTML 502 gateway errors cleanly without crashing or leaking jargon", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("<html><body><h1>502 Bad Gateway</h1></body></html>", {
          status: 502,
          headers: { "Content-Type": "text/html" },
        }),
      ),
    );

    await expect(
      fetchRecommendations({
        percentile: 95,
        category: "GOPENS",
        branch: "All",
        division: "All",
        page: 1,
        page_size: 10,
      }),
    ).rejects.toMatchObject({
      name: "ApiClientError",
      status: 502,
    });

    try {
      await fetchRecommendations({
        percentile: 95,
        category: "GOPENS",
        branch: "All",
        division: "All",
        page: 1,
        page_size: 10,
      });
    } catch (err) {
      expect(err).toBeInstanceOf(ApiClientError);
      assertNoBannedJargon((err as ApiClientError).message);
    }
  });

  it("handles network failures and timeouts cleanly without technical jargon", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    try {
      await fetchRecommendations({
        percentile: 95,
        category: "GOPENS",
        branch: "All",
        division: "All",
        page: 1,
        page_size: 10,
      });
      throw new Error("Expected rejection");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiClientError);
      const message = (err as ApiClientError).message;
      expect(message).toContain("internet");
      assertNoBannedJargon(message);
    }
  });

  it("clears auth session and React Query cache on 401 from authenticated endpoints", async () => {
    setAuthSession({ token: "expired-jwt", username: "aarav" });
    queryClient.setQueryData(["saved-list", "aarav"], {
      saved_list: [{ id: 1, college_name: "COEP", branch_name: "CS" }],
    });
    const clearSpy = vi.spyOn(queryClient, "clear");

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Invalid or expired token" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(fetchSavedList()).rejects.toMatchObject({
      status: 401,
      isUnauthorized: true,
    });

    expect(getAuthSession()).toBeNull();
    expect(clearSpy).toHaveBeenCalled();
    expect(queryClient.getQueryData(["saved-list", "aarav"])).toBeUndefined();
    const banner = getSessionBanner();
    expect(banner).toBe("Your session timed out. Sign in again to view your saved list.");
    assertNoBannedJargon(banner ?? "");
  });

  it("sends form-encoded credentials on login and formats 401 as credential mismatch", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Invalid username or password." }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    try {
      await loginUser("aarav", "wrongpass");
      throw new Error("Expected login rejection");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiClientError);
      const msg = (err as ApiClientError).message;
      expect(msg).toBe("That username or password didn't match. Please check and try again.");
      assertNoBannedJargon(msg);
    }

    const [, requestInit] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(requestInit.headers).toMatchObject({
      "Content-Type": "application/x-www-form-urlencoded",
    });
    expect(requestInit.body).toBe("username=aarav&password=wrongpass");
  });
});
