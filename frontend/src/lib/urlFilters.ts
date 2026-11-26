import { parsePercentileInput } from "./formatters";

export type AppView = "explorer" | "shortlist";

export interface ExplorerFilters {
  percentileText: string;
  percentile: number;
  category: string;
  branch: string;
  division: string;
  page: number;
  pageSize: number;
}

export const DEFAULT_PAGE_SIZE = 10;
export const ALLOWED_PAGE_SIZES = [10, 20, 30] as const;

export function getDefaultFilters(availableCategories?: readonly string[]): ExplorerFilters {
  const defaultCategory =
    availableCategories && availableCategories.length > 0
      ? availableCategories.includes("GOPENS")
        ? "GOPENS"
        : "All"
      : "GOPENS";

  return {
    percentileText: "95.0000000",
    percentile: 95,
    category: defaultCategory,
    branch: "All",
    division: "All",
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
  };
}

export function parseFiltersFromSearch(
  search: string,
  availableCategories?: readonly string[],
): { view: AppView; filters: ExplorerFilters; hasExplicitQuery: boolean } {
  const params = new URLSearchParams(search);
  const defaults = getDefaultFilters(availableCategories);

  const rawView = params.get("view");
  const view: AppView = rawView === "shortlist" ? "shortlist" : "explorer";

  const rawPercentile = params.get("percentile");
  const parsedPercentile = rawPercentile !== null ? parsePercentileInput(rawPercentile) : null;

  const rawCategory = params.get("category");
  const category = rawCategory && rawCategory.trim() ? rawCategory.trim() : defaults.category;

  const rawBranch = params.get("branch");
  const branch = rawBranch && rawBranch.trim() ? rawBranch.trim() : "All";

  const rawDivision = params.get("division");
  const division = rawDivision && rawDivision.trim() ? rawDivision.trim() : "All";

  const rawPage = Number(params.get("page"));
  const page = Number.isInteger(rawPage) && rawPage >= 1 ? rawPage : 1;

  const rawPageSize = Number(params.get("page_size"));
  const pageSize =
    Number.isInteger(rawPageSize) && rawPageSize >= 5 && rawPageSize <= 30
      ? rawPageSize
      : DEFAULT_PAGE_SIZE;

  const hasExplicitQuery =
    params.has("percentile") ||
    params.has("category") ||
    params.has("branch") ||
    params.has("division");

  return {
    view,
    hasExplicitQuery,
    filters: {
      percentileText:
        parsedPercentile !== null && rawPercentile !== null
          ? rawPercentile.trim()
          : defaults.percentileText,
      percentile: parsedPercentile ?? defaults.percentile,
      category,
      branch,
      division,
      page,
      pageSize,
    },
  };
}

export function serializeFiltersToSearch(
  filters: ExplorerFilters,
  view: AppView = "explorer",
): string {
  const params = new URLSearchParams();
  if (view === "shortlist") {
    params.set("view", "shortlist");
  }
  params.set("percentile", filters.percentileText.trim() || String(filters.percentile));
  params.set("category", filters.category);
  if (filters.branch !== "All") {
    params.set("branch", filters.branch);
  }
  if (filters.division !== "All") {
    params.set("division", filters.division);
  }
  if (filters.page > 1) {
    params.set("page", String(filters.page));
  }
  if (filters.pageSize !== DEFAULT_PAGE_SIZE) {
    params.set("page_size", String(filters.pageSize));
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}
