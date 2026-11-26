import { Check, Share2, SlidersHorizontal } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { CatalogFiltersResponse } from "../api/types";
import { decodeCategory } from "../lib/categoryLabels";
import { parsePercentileInput, sanitizePercentileInput } from "../lib/formatters";
import type { ExplorerFilters } from "../lib/urlFilters";
import { SearchableSelect, type SelectOption } from "./SearchableSelect";

interface FilterBarProps {
  catalog: CatalogFiltersResponse | undefined;
  catalogLoading: boolean;
  catalogError: string | null;
  onRetryCatalog: () => void;
  activeFilters: ExplorerFilters;
  onApplyFilters: (next: ExplorerFilters) => void;
}

const PRIORITY_CATEGORIES = ["GOPENS", "GOPENH", "GOBCS", "GOBCH", "LOPENS", "LOPENH", "TFWS", "EWS"];

export function FilterBar({
  catalog,
  catalogLoading,
  catalogError,
  onRetryCatalog,
  activeFilters,
  onApplyFilters,
}: FilterBarProps) {
  const [draftPercentile, setDraftPercentile] = useState(activeFilters.percentileText);
  const [draftCategory, setDraftCategory] = useState(activeFilters.category);
  const [draftBranch, setDraftBranch] = useState(activeFilters.branch);
  const [draftDivision, setDraftDivision] = useState(activeFilters.division);
  const [percentileError, setPercentileError] = useState<string | null>(null);
  const [mobileExpanded, setMobileExpanded] = useState(true);
  const [copiedLink, setCopiedLink] = useState(false);

  useEffect(() => {
    setDraftPercentile(activeFilters.percentileText);
    setDraftCategory(activeFilters.category);
    setDraftBranch(activeFilters.branch);
    setDraftDivision(activeFilters.division);
    setPercentileError(null);
  }, [
    activeFilters.percentileText,
    activeFilters.category,
    activeFilters.branch,
    activeFilters.division,
  ]);

  const categoryOptions: SelectOption[] = useMemo(() => {
    const rawCats = catalog?.categories ?? ["GOPENS", "GOBCS", "TFWS", "EWS"];
    const unique = Array.from(new Set(rawCats.filter((c) => c !== "All")));
    unique.sort((a, b) => {
      const idxA = PRIORITY_CATEGORIES.indexOf(a);
      const idxB = PRIORITY_CATEGORIES.indexOf(b);
      if (idxA !== -1 && idxB !== -1) return idxA - idxB;
      if (idxA !== -1) return -1;
      if (idxB !== -1) return 1;
      return a.localeCompare(b);
    });

    const decoded = unique.map((code) => {
      const info = decodeCategory(code);
      return {
        value: code,
        code: info.code,
        label: info.label,
        keywords: `${info.code} ${info.label}`,
      };
    });

    return [
      {
        value: "All",
        code: "All",
        label: "All Categories",
        keywords: "all general reserved",
      },
      ...decoded,
    ];
  }, [catalog?.categories]);

  const branchOptions: SelectOption[] = useMemo(() => {
    const raw = catalog?.branches ?? [];
    return [
      { value: "All", label: "All Branches" },
      ...raw.filter((b) => b !== "All").map((b) => ({ value: b, label: b })),
    ];
  }, [catalog?.branches]);

  const divisionOptions: SelectOption[] = useMemo(() => {
    const raw = catalog?.divisions ?? [];
    return [
      { value: "All", label: "All Divisions" },
      ...raw.filter((d) => d !== "All").map((d) => ({ value: d, label: d })),
    ];
  }, [catalog?.divisions]);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const numeric = parsePercentileInput(draftPercentile);
    if (numeric === null) {
      setPercentileError("Enter a percentile between 0 and 100 (up to 7 decimal places).");
      return;
    }
    setPercentileError(null);
    onApplyFilters({
      percentileText: draftPercentile.trim(),
      percentile: numeric,
      category: draftCategory,
      branch: draftBranch,
      division: draftDivision,
      page: 1,
      pageSize: activeFilters.pageSize,
    });
    if (typeof window !== "undefined" && window.innerWidth < 768) {
      setMobileExpanded(false);
    }
  }

  async function handleShareSearch() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    } catch {
      setCopiedLink(false);
    }
  }

  const activeFilterCount =
    (activeFilters.branch !== "All" ? 1 : 0) + (activeFilters.division !== "All" ? 1 : 0);

  return (
    <section
      aria-label="Eligibility filters"
      className="no-print rounded-[6px] border border-rule-strong bg-surface"
    >
      {/* Mobile compact summary bar */}
      <div className="flex items-center justify-between gap-2 border-b border-rule px-4 py-2 md:hidden">
        <div className="min-w-0 truncate">
          <span className="tabular-nums font-mono text-[13.5px] font-semibold text-ink">
            {activeFilters.percentileText}
          </span>
          <span className="mx-1.5 text-ink-muted">·</span>
          <span className="font-mono text-[12.5px] font-medium text-accent">
            {activeFilters.category}
          </span>
          {activeFilterCount > 0 && (
            <span className="ml-1.5 text-[12px] text-ink-secondary">
              +{activeFilterCount} filter{activeFilterCount > 1 ? "s" : ""}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => setMobileExpanded((prev) => !prev)}
          aria-expanded={mobileExpanded}
          className="flex min-h-[44px] shrink-0 items-center gap-1.5 rounded-[4px] border border-rule-strong bg-recessed px-3 py-1.5 text-[12.5px] font-medium text-ink"
        >
          <SlidersHorizontal size={14} />
          <span>{mobileExpanded ? "Hide filters" : "Edit filters"}</span>
        </button>
      </div>

      {catalogError && (
        <div
          role="alert"
          className="flex flex-wrap items-center justify-between gap-2 border-b border-rule bg-danger-tint px-4 py-2.5 text-[13px] text-danger"
        >
          <span>{catalogError}</span>
          <button
            type="button"
            onClick={onRetryCatalog}
            className="min-h-[34px] rounded-[4px] border border-danger/40 bg-surface px-3 py-1 text-[12.5px] font-medium text-danger hover:bg-hover"
          >
            Retry
          </button>
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className={`${mobileExpanded ? "block" : "hidden"} p-4 md:block sm:p-5`}
        noValidate
      >
        <div className="grid grid-cols-1 gap-3.5 md:grid-cols-12 md:items-end">
          <div className="md:col-span-3">
            <label
              htmlFor="percentile-input"
              className="mb-1.5 block text-[11.5px] font-semibold tracking-[0.04em] text-ink-muted uppercase"
            >
              MHT-CET Percentile
            </label>
            <input
              id="percentile-input"
              type="text"
              inputMode="decimal"
              autoComplete="off"
              value={draftPercentile}
              onChange={(e) => {
                setDraftPercentile(sanitizePercentileInput(e.target.value));
                if (percentileError) setPercentileError(null);
              }}
              placeholder="e.g. 99.4821500"
              aria-invalid={Boolean(percentileError)}
              className="tabular-nums min-h-[44px] w-full rounded-[6px] border border-rule-strong bg-surface px-3 py-2 font-mono text-[16px] font-semibold text-ink placeholder:font-normal placeholder:text-ink-muted"
            />
          </div>

          <div className="md:col-span-4">
            <SearchableSelect
              label="Seat Category"
              value={draftCategory}
              options={categoryOptions}
              onChange={setDraftCategory}
              searchPlaceholder="Search code (GOPENS, LOBCH) or name…"
              disabled={catalogLoading && !catalog}
            />
          </div>

          <div className="md:col-span-3">
            <SearchableSelect
              label="Engineering Branch"
              value={draftBranch}
              options={branchOptions}
              onChange={setDraftBranch}
              searchPlaceholder="Filter branches…"
              disabled={catalogLoading && !catalog}
            />
          </div>

          <div className="md:col-span-2">
            <SearchableSelect
              label="Division"
              value={draftDivision}
              options={divisionOptions}
              onChange={setDraftDivision}
              searchPlaceholder="Filter division…"
              disabled={catalogLoading && !catalog}
            />
          </div>
        </div>

        {percentileError && (
          <p role="alert" className="mt-2 text-[13px] font-medium text-danger">
            {percentileError}
          </p>
        )}

        {draftCategory === "All" && (
          <p className="mt-3 rounded-[4px] border border-competitive/30 bg-competitive-tint px-3 py-2 text-[12.5px] text-competitive">
            <strong>Note:</strong> Selecting &ldquo;All&rdquo; mixes General, Reserved, Defence,
            PWD, and Orphan cutoffs together. Pick your exact CET seat code for accurate
            eligibility.
          </p>
        )}

        <div className="mt-4 flex flex-col gap-2.5 border-t border-rule pt-3.5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-[12.5px] text-ink-muted">
            Enter up to 7 decimal places · Ranked from highest recent cutoff downward
          </p>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={handleShareSearch}
              className="flex min-h-[44px] flex-1 items-center justify-center gap-1.5 rounded-[4px] border border-rule-strong bg-surface px-3.5 py-2 text-[13.5px] font-medium text-ink transition-colors hover:bg-hover sm:flex-none"
            >
              {copiedLink ? <Check size={15} className="text-safe" /> : <Share2 size={15} />}
              <span>{copiedLink ? "Link copied" : "Share Search"}</span>
            </button>

            <button
              type="submit"
              className="min-h-[44px] flex-1 rounded-[4px] bg-accent px-5 py-2 text-[14px] font-semibold text-accent-ink transition-colors hover:bg-accent-hover sm:flex-none"
            >
              Find Colleges
            </button>
          </div>
        </div>
      </form>
    </section>
  );
}
