import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { fetchRecommendations } from "./api/client";
import { ApiClientError } from "./api/errors";
import type { EligibleCollege } from "./api/types";
import { AuthModal } from "./components/AuthModal";
import { CollegeResults } from "./components/CollegeResults";
import { FilterBar } from "./components/FilterBar";
import { Header } from "./components/Header";
import { ShortlistView } from "./components/ShortlistView";
import { TrendsSheet } from "./components/TrendsSheet";
import { useAuth } from "./context/AuthContext";
import { useCatalogFilters } from "./hooks/useCatalogFilters";
import { useSavedShortlist } from "./hooks/useSavedShortlist";
import {
  type AppView,
  type ExplorerFilters,
  parseFiltersFromSearch,
  serializeFiltersToSearch,
} from "./lib/urlFilters";

export function App() {
  const { isAuthenticated, sessionBanner, dismissBanner } = useAuth();
  const catalogQuery = useCatalogFilters();

  const initialParsed = parseFiltersFromSearch(
    typeof window !== "undefined" ? window.location.search : "",
  );
  const [activeView, setActiveView] = useState<AppView>(initialParsed.view);
  const [filters, setFilters] = useState<ExplorerFilters>(initialParsed.filters);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [trendsCollege, setTrendsCollege] = useState<EligibleCollege | null>(null);
  const [toastMessage, setToastMessage] = useState<{ text: string; tone: "ok" | "error" } | null>(
    null,
  );
  const [savingBranchCode, setSavingBranchCode] = useState<string | null>(null);
  const hasSyncedCatalogDefault = useRef(false);

  // Sync default category to GOPENS (if available) when no category was explicitly in URL.
  useEffect(() => {
    if (hasSyncedCatalogDefault.current || !catalogQuery.data) {
      return;
    }
    hasSyncedCatalogDefault.current = true;
    const params = new URLSearchParams(window.location.search);
    if (!params.has("category")) {
      const preferred = catalogQuery.data.categories.includes("GOPENS") ? "GOPENS" : "All";
      setFilters((prev) =>
        prev.category === preferred ? prev : { ...prev, category: preferred, page: 1 },
      );
    }
  }, [catalogQuery.data]);

  // Keep URL query parameters synchronized with active filters & view.
  useEffect(() => {
    const nextSearch = serializeFiltersToSearch(filters, activeView);
    if (window.location.search !== nextSearch) {
      window.history.replaceState(null, "", `${window.location.pathname}${nextSearch}`);
    }
  }, [filters, activeView]);

  // Handle browser back/forward navigation.
  useEffect(() => {
    function handlePopState() {
      const parsed = parseFiltersFromSearch(
        window.location.search,
        catalogQuery.data?.categories,
      );
      setActiveView(parsed.view);
      setFilters(parsed.filters);
    }
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [catalogQuery.data?.categories]);

  const recommenderQuery = useQuery({
    queryKey: [
      "recommender",
      filters.percentile,
      filters.category,
      filters.branch,
      filters.division,
      filters.page,
      filters.pageSize,
    ],
    queryFn: ({ signal }) =>
      fetchRecommendations(
        {
          percentile: filters.percentile,
          category: filters.category,
          branch: filters.branch,
          division: filters.division,
          page: filters.page,
          page_size: filters.pageSize,
        },
        signal,
      ),
    placeholderData: keepPreviousData,
    staleTime: 5 * 60 * 1000,
  });

  const shortlist = useSavedShortlist();

  function showToast(text: string, tone: "ok" | "error") {
    setToastMessage({ text, tone });
    setTimeout(() => {
      setToastMessage((current) => (current?.text === text ? null : current));
    }, 3500);
  }

  async function handleToggleSave(college: EligibleCollege) {
    if (!isAuthenticated) {
      setAuthModalOpen(true);
      return;
    }

    const existing = shortlist.getSavedMatch(college.college, college.branch);
    setSavingBranchCode(college.branch_code);
    try {
      if (existing) {
        await shortlist.removeItem(existing.item.id);
        showToast("Removed from your Option Form.", "ok");
      } else {
        await shortlist.addItem(college.branch_code);
        showToast("Saved to your Option Form.", "ok");
      }
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        if (!err.isUnauthorized) {
          showToast(err.message, "error");
        }
      } else {
        showToast("Couldn't update your shortlist right now.", "error");
      }
    } finally {
      setSavingBranchCode(null);
    }
  }

  const catalogErrorMessage =
    catalogQuery.error instanceof Error ? catalogQuery.error.message : null;
  const recommenderErrorMessage =
    recommenderQuery.error instanceof Error ? recommenderQuery.error.message : null;
  const shortlistErrorMessage =
    shortlist.error instanceof Error ? shortlist.error.message : null;

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <Header
        activeView={activeView}
        onChangeView={setActiveView}
        savedCount={shortlist.items.length}
        onOpenAuthModal={() => setAuthModalOpen(true)}
      />

      <main className="mx-auto max-w-[1320px] px-4 py-4 sm:px-6 sm:py-5">
        {sessionBanner && (
          <div
            role="alert"
            className="no-print mb-4 flex items-center justify-between gap-3 rounded-[6px] border border-competitive/40 bg-competitive-tint px-4 py-2.5 text-[13.5px] font-medium text-competitive"
          >
            <span>{sessionBanner}</span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  dismissBanner();
                  setAuthModalOpen(true);
                }}
                className="min-h-[34px] rounded-[4px] border border-competitive/40 bg-surface px-2.5 py-1 text-[12.5px] font-semibold text-ink hover:bg-hover"
              >
                Sign in
              </button>
              <button
                type="button"
                aria-label="Dismiss notice"
                onClick={dismissBanner}
                className="rounded p-1 text-competitive hover:bg-hover"
              >
                <X size={15} />
              </button>
            </div>
          </div>
        )}

        {toastMessage && (
          <div
            role="status"
            aria-live="polite"
            className={`no-print mb-4 rounded-[6px] border px-4 py-2.5 text-[13.5px] font-medium ${
              toastMessage.tone === "error"
                ? "border-danger/30 bg-danger-tint text-danger"
                : "border-safe/30 bg-safe-tint text-safe"
            }`}
          >
            {toastMessage.text}
          </div>
        )}

        {activeView === "explorer" ? (
          <>
            <FilterBar
              catalog={catalogQuery.data}
              catalogLoading={catalogQuery.isLoading}
              catalogError={catalogErrorMessage}
              onRetryCatalog={() => void catalogQuery.refetch()}
              activeFilters={filters}
              onApplyFilters={(next) => setFilters(next)}
            />

            <CollegeResults
              filters={filters}
              colleges={recommenderQuery.data?.eligible_colleges ?? []}
              totalCount={recommenderQuery.data?.count ?? 0}
              isLoading={recommenderQuery.isLoading}
              isFetching={recommenderQuery.isFetching}
              errorMessage={recommenderErrorMessage}
              onRetry={() => void recommenderQuery.refetch()}
              onResetFilters={() =>
                setFilters((prev) => ({
                  ...prev,
                  branch: "All",
                  division: "All",
                  page: 1,
                }))
              }
              onPageChange={(page) => setFilters((prev) => ({ ...prev, page }))}
              onPageSizeChange={(pageSize) =>
                setFilters((prev) => ({ ...prev, pageSize, page: 1 }))
              }
              onOpenTrends={(college) => setTrendsCollege(college)}
              onToggleSave={(college) => void handleToggleSave(college)}
              getSavedMatch={shortlist.getSavedMatch}
              savingBranchCode={savingBranchCode}
            />
          </>
        ) : (
          <ShortlistView
            items={shortlist.items}
            isLoading={shortlist.isLoading}
            errorMessage={shortlistErrorMessage}
            onRetry={() => void shortlist.refetch()}
            onReorder={shortlist.reorderItems}
            onRemove={shortlist.removeItem}
            onBrowseExplorer={() => setActiveView("explorer")}
          />
        )}
      </main>

      <TrendsSheet
        college={trendsCollege}
        submittedCategory={filters.category}
        submittedPercentile={filters.percentile}
        onClose={() => setTrendsCollege(null)}
      />

      <AuthModal open={authModalOpen} onClose={() => setAuthModalOpen(false)} />
    </div>
  );
}

export default App;
