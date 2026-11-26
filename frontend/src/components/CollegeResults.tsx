import { Bookmark, BookmarkCheck, ChevronLeft, ChevronRight, LineChart } from "lucide-react";
import { useRef } from "react";
import type { EligibleCollege, SavedListItem } from "../api/types";
import { decodeCategory } from "../lib/categoryLabels";
import { assessCutoffMargin, formatPercentile, type MarginStatus } from "../lib/formatters";
import { ALLOWED_PAGE_SIZES, type ExplorerFilters } from "../lib/urlFilters";

interface CollegeResultsProps {
  filters: ExplorerFilters;
  colleges: EligibleCollege[];
  totalCount: number;
  isLoading: boolean;
  isFetching: boolean;
  errorMessage: string | null;
  onRetry: () => void;
  onResetFilters: () => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  onOpenTrends: (college: EligibleCollege) => void;
  onToggleSave: (college: EligibleCollege) => void;
  getSavedMatch: (
    collegeName: string,
    branchName: string,
  ) => { item: SavedListItem; rank: number } | null;
  savingBranchCode: string | null;
}

const MARGIN_STYLES: Record<MarginStatus, string> = {
  safe: "border-safe/30 bg-safe-tint text-safe",
  competitive: "border-competitive/30 bg-competitive-tint text-competitive",
  borderline: "border-borderline/30 bg-borderline-tint text-borderline",
};

function SkeletonRows() {
  return (
    <div aria-busy="true" aria-label="Loading eligible colleges" className="divide-y divide-rule">
      {Array.from({ length: 6 }).map((_, idx) => (
        <div key={idx} className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-2 sm:w-1/2">
            <div className="h-4 w-4/5 animate-pulse rounded bg-recessed" />
            <div className="h-3.5 w-3/5 animate-pulse rounded bg-recessed" />
          </div>
          <div className="flex items-center gap-3">
            <div className="h-6 w-28 animate-pulse rounded bg-recessed" />
            <div className="h-9 w-24 animate-pulse rounded bg-recessed" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function CollegeResults({
  filters,
  colleges,
  totalCount,
  isLoading,
  isFetching,
  errorMessage,
  onRetry,
  onResetFilters,
  onPageChange,
  onPageSizeChange,
  onOpenTrends,
  onToggleSave,
  getSavedMatch,
  savingBranchCode,
}: CollegeResultsProps) {
  const resultsTopRef = useRef<HTMLDivElement>(null);
  const totalPages = Math.max(1, Math.ceil(totalCount / filters.pageSize));
  const startRank = totalCount === 0 ? 0 : (filters.page - 1) * filters.pageSize + 1;
  const endRank = Math.min(totalCount, filters.page * filters.pageSize);
  const decodedCategory = decodeCategory(filters.category);

  function goToPage(nextPage: number) {
    onPageChange(nextPage);
    if (resultsTopRef.current && typeof resultsTopRef.current.scrollIntoView === "function") {
      resultsTopRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  return (
    <section ref={resultsTopRef} aria-label="Eligible colleges" className="mt-4">
      <div className="rounded-[6px] border border-rule-strong bg-surface">
        {/* Ledger Header */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-rule bg-recessed px-4 py-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-[15px] font-semibold text-ink">
                {isLoading ? (
                  "Searching eligible colleges…"
                ) : (
                  <>
                    <span className="tabular-nums font-mono">{totalCount}</span> eligible college
                    {totalCount === 1 ? "" : "s"}
                  </>
                )}
              </h2>
              {isFetching && !isLoading && (
                <span className="text-[12px] text-ink-muted">Updating…</span>
              )}
            </div>
            <p className="mt-0.5 text-[12.5px] text-ink-secondary">
              {decodedCategory.displayText}
              {filters.division !== "All" ? ` · ${filters.division}` : ""}
              {filters.branch !== "All" ? ` · ${filters.branch}` : ""}
              {totalCount > 0 ? ` · Showing ${startRank}–${endRank}` : ""}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="page-size-select" className="text-[12px] font-medium text-ink-secondary">
              Per page
            </label>
            <select
              id="page-size-select"
              value={filters.pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              className="tabular-nums min-h-[36px] rounded-[4px] border border-rule-strong bg-surface px-2 py-1 font-mono text-[13px] text-ink"
            >
              {ALLOWED_PAGE_SIZES.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Body */}
        {isLoading ? (
          <SkeletonRows />
        ) : errorMessage ? (
          <div role="alert" className="px-6 py-10 text-center">
            <p className="text-[14.5px] font-medium text-danger">{errorMessage}</p>
            <button
              type="button"
              onClick={onRetry}
              className="mt-4 min-h-[40px] rounded-[4px] border border-rule-strong bg-surface px-4 py-2 text-[13.5px] font-medium text-ink hover:bg-hover"
            >
              Try again
            </button>
          </div>
        ) : colleges.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <h3 className="font-display text-[19px] font-semibold text-ink">
              No colleges matched these filters
            </h3>
            <p className="mx-auto mt-1.5 max-w-md text-[13.5px] text-ink-secondary">
              Try widening Engineering Branch or Division to &ldquo;All&rdquo;, or check your
              selected category and percentile.
            </p>
            <button
              type="button"
              onClick={onResetFilters}
              className="mt-4 min-h-[44px] rounded-[4px] bg-accent px-4 py-2 text-[13.5px] font-semibold text-accent-ink hover:bg-accent-hover"
            >
              Reset branch &amp; division to All
            </button>
          </div>
        ) : (
          <>
            {/* Desktop Table */}
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-rule bg-canvas text-[11.5px] font-semibold tracking-[0.04em] text-ink-muted uppercase">
                    <th className="px-4 py-2.5">Code</th>
                    <th className="px-4 py-2.5">College &amp; Branch</th>
                    <th className="px-4 py-2.5 text-right">Min Cutoff</th>
                    <th className="px-4 py-2.5 text-right">Max Cutoff</th>
                    <th className="px-4 py-2.5">Margin</th>
                    <th className="px-4 py-2.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-rule">
                  {colleges.map((item) => {
                    const margin = assessCutoffMargin(
                      filters.percentile,
                      item.min_cutoff,
                      item.max_cutoff,
                    );
                    const savedMatch = getSavedMatch(item.college, item.branch);
                    const isBusy = savingBranchCode === item.branch_code;

                    return (
                      <tr key={item.branch_code} className="transition-colors hover:bg-hover">
                        <td className="tabular-nums px-4 py-3.5 align-top font-mono text-[12.5px] text-ink-secondary">
                          {item.branch_code}
                        </td>
                        <td className="px-4 py-3.5 align-top">
                          <div className="text-[14.5px] font-semibold leading-snug text-ink">
                            {item.college}
                          </div>
                          <div className="mt-0.5 text-[13px] text-ink-secondary">{item.branch}</div>
                        </td>
                        <td className="tabular-nums px-4 py-3.5 text-right align-top font-mono text-[13.5px] text-ink-secondary">
                          {formatPercentile(item.min_cutoff)}
                        </td>
                        <td className="tabular-nums px-4 py-3.5 text-right align-top font-mono text-[13.5px] font-semibold text-ink">
                          {formatPercentile(item.max_cutoff)}
                        </td>
                        <td className="px-4 py-3.5 align-top">
                          <span
                            title={margin.detail}
                            className={`inline-flex items-center gap-1 rounded-[4px] border px-2 py-0.5 text-[12px] font-medium whitespace-nowrap ${MARGIN_STYLES[margin.status]}`}
                          >
                            <span aria-hidden="true">{margin.symbol}</span>
                            <span>{margin.label}</span>
                          </span>
                        </td>
                        <td className="px-4 py-3.5 text-right align-top">
                          <div className="inline-flex items-center justify-end gap-2">
                            <button
                              type="button"
                              onClick={() => onOpenTrends(item)}
                              className="inline-flex min-h-[36px] items-center gap-1.5 rounded-[4px] border border-rule-strong bg-surface px-2.5 py-1 text-[12.5px] font-medium text-ink transition-colors hover:bg-recessed"
                            >
                              <LineChart size={14} />
                              <span>Cutoff History</span>
                            </button>
                            <button
                              type="button"
                              disabled={isBusy}
                              onClick={() => onToggleSave(item)}
                              className={`inline-flex min-h-[36px] items-center gap-1.5 rounded-[4px] border px-2.5 py-1 text-[12.5px] font-medium transition-colors disabled:opacity-60 ${
                                savedMatch
                                  ? "border-accent/40 bg-accent-tint text-accent hover:bg-hover"
                                  : "border-rule-strong bg-surface text-ink hover:bg-recessed"
                              }`}
                            >
                              {savedMatch ? <BookmarkCheck size={14} /> : <Bookmark size={14} />}
                              <span>
                                {isBusy
                                  ? "Saving…"
                                  : savedMatch
                                    ? `Saved #${savedMatch.rank}`
                                    : "Save"}
                              </span>
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Mobile Stacked Rows */}
            <div className="divide-y divide-rule md:hidden">
              {colleges.map((item) => {
                const margin = assessCutoffMargin(
                  filters.percentile,
                  item.min_cutoff,
                  item.max_cutoff,
                );
                const savedMatch = getSavedMatch(item.college, item.branch);
                const isBusy = savingBranchCode === item.branch_code;

                return (
                  <article key={item.branch_code} className="px-4 py-3.5">
                    <div className="flex items-start justify-between gap-2">
                      <span className="tabular-nums rounded-[4px] bg-recessed px-1.5 py-0.5 font-mono text-[11.5px] text-ink-secondary">
                        {item.branch_code}
                      </span>
                      <span
                        className={`inline-flex items-center gap-1 rounded-[4px] border px-2 py-0.5 text-[11.5px] font-medium ${MARGIN_STYLES[margin.status]}`}
                      >
                        <span aria-hidden="true">{margin.symbol}</span>
                        <span>{margin.label}</span>
                      </span>
                    </div>

                    <h3 className="mt-1.5 text-[15px] font-semibold leading-snug text-ink">
                      {item.college}
                    </h3>
                    <p className="mt-0.5 text-[13px] text-ink-secondary">{item.branch}</p>

                    <div className="mt-2.5 grid grid-cols-2 gap-3 border-t border-rule pt-2.5">
                      <div>
                        <div className="text-[11px] font-semibold tracking-[0.03em] text-ink-muted uppercase">
                          Min Cutoff
                        </div>
                        <div className="tabular-nums font-mono text-[13.5px] text-ink-secondary">
                          {formatPercentile(item.min_cutoff)}
                        </div>
                      </div>
                      <div>
                        <div className="text-[11px] font-semibold tracking-[0.03em] text-ink-muted uppercase">
                          Max Cutoff
                        </div>
                        <div className="tabular-nums font-mono text-[13.5px] font-semibold text-ink">
                          {formatPercentile(item.max_cutoff)}
                        </div>
                      </div>
                    </div>

                    <div className="mt-3 grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => onOpenTrends(item)}
                        className="flex min-h-[44px] items-center justify-center gap-1.5 rounded-[4px] border border-rule-strong bg-surface px-3 text-[13px] font-medium text-ink"
                      >
                        <LineChart size={15} />
                        <span>Cutoff History</span>
                      </button>
                      <button
                        type="button"
                        disabled={isBusy}
                        onClick={() => onToggleSave(item)}
                        className={`flex min-h-[44px] items-center justify-center gap-1.5 rounded-[4px] border px-3 text-[13px] font-medium disabled:opacity-60 ${
                          savedMatch
                            ? "border-accent/40 bg-accent-tint text-accent"
                            : "border-rule-strong bg-surface text-ink"
                        }`}
                      >
                        {savedMatch ? <BookmarkCheck size={15} /> : <Bookmark size={15} />}
                        <span>
                          {isBusy ? "Saving…" : savedMatch ? `Saved #${savedMatch.rank}` : "Save"}
                        </span>
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          </>
        )}

        {/* Pagination */}
        {!isLoading && !errorMessage && totalCount > 0 && (
          <div className="flex items-center justify-between gap-2 border-t border-rule bg-canvas px-4 py-3">
            <button
              type="button"
              disabled={filters.page <= 1}
              onClick={() => goToPage(filters.page - 1)}
              className="flex min-h-[42px] items-center gap-1 rounded-[4px] border border-rule-strong bg-surface px-3 py-1.5 text-[13px] font-medium text-ink transition-colors hover:bg-hover disabled:opacity-45"
            >
              <ChevronLeft size={16} />
              <span>Previous</span>
            </button>

            <span className="tabular-nums font-mono text-[13px] text-ink-secondary">
              Page {filters.page} of {totalPages}
            </span>

            <button
              type="button"
              disabled={filters.page >= totalPages}
              onClick={() => goToPage(filters.page + 1)}
              className="flex min-h-[42px] items-center gap-1 rounded-[4px] border border-rule-strong bg-surface px-3 py-1.5 text-[13px] font-medium text-ink transition-colors hover:bg-hover disabled:opacity-45"
            >
              <span>Next</span>
              <ChevronRight size={16} />
            </button>
          </div>
        )}
      </div>
    </section>
  );
}
