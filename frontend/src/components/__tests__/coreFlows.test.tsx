import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { clearAuthSession, setAuthSession } from "../../api/authSession";
import { AuthProvider } from "../../context/AuthContext";
import { buildShortlistCsv } from "../../lib/formatters";
import { parseFiltersFromSearch, serializeFiltersToSearch } from "../../lib/urlFilters";
import { FilterBar } from "../FilterBar";
import { ShortlistView } from "../ShortlistView";
import {
  buildRoundSeriesForLevel,
  groupTrendsByLevel,
  TrendsSheet,
} from "../TrendsSheet";

describe("URL filter synchronization", () => {
  it("parses and serializes 7-decimal percentile and filters cleanly", () => {
    const parsed = parseFiltersFromSearch(
      "?percentile=99.4821500&category=LOBCH&branch=Computer%20Engineering&division=Pune%20Division&page=2&page_size=20",
    );
    expect(parsed.filters).toEqual({
      percentileText: "99.4821500",
      percentile: 99.48215,
      category: "LOBCH",
      branch: "Computer Engineering",
      division: "Pune Division",
      page: 2,
      pageSize: 20,
    });

    const serialized = serializeFiltersToSearch(parsed.filters, "explorer");
    expect(serialized).toContain("percentile=99.4821500");
    expect(serialized).toContain("category=LOBCH");
    expect(serialized).toContain("page=2");
    expect(serialized).toContain("page_size=20");
  });

  it("shows advisory note when All category is chosen and submits 7-decimal percentile", () => {
    const onApply = vi.fn();
    render(
      <FilterBar
        catalog={{
          categories: ["GOPENS", "LOBCH"],
          branches: ["Computer Engineering"],
          divisions: ["Pune Division"],
          years: [2024, 2025],
          levels: ["SL"],
        }}
        catalogLoading={false}
        catalogError={null}
        onRetryCatalog={vi.fn()}
        activeFilters={{
          percentileText: "98.7654321",
          percentile: 98.7654321,
          category: "All",
          branch: "All",
          division: "All",
          page: 1,
          pageSize: 10,
        }}
        onApplyFilters={onApply}
      />,
    );

    expect(screen.getByText(/mixes General, Reserved, Defence/i)).toBeInTheDocument();
    const input = screen.getByLabelText(/MHT-CET Percentile/i) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "99.1234567" } });
    fireEvent.click(screen.getByRole("button", { name: /Find Colleges/i }));

    expect(onApply).toHaveBeenCalledWith(
      expect.objectContaining({
        percentileText: "99.1234567",
        percentile: 99.1234567,
      }),
    );
  });
});

describe("Trends level grouping & Y-axis clamping", () => {
  it("separates multiple seat levels cleanly and clamps Y-axis to [max(0, min-1), min(100, max+1)]", () => {
    const points = [
      { year: 2024, round: 1, level: "SL", percentile: 99.5 },
      { year: 2024, round: 2, level: "SL", percentile: 99.2 },
      { year: 2025, round: 1, level: "SL", percentile: 99.6 },
      { year: 2024, round: 1, level: "HU_HU", percentile: 98.1 },
      { year: 2025, round: 1, level: "HU_HU", percentile: 98.4 },
    ];

    const { levels, byLevel } = groupTrendsByLevel(points);
    expect(levels).toEqual(["SL", "HU_HU"]);

    const slSeries = buildRoundSeriesForLevel(byLevel.SL ?? []);
    expect(slSeries.years).toEqual([2025, 2024]);
    expect(slSeries.chartData).toHaveLength(2);
    expect(slSeries.yDomain).toEqual([98.2, 100]);

    const lowSeries = buildRoundSeriesForLevel([
      { year: 2025, round: 1, level: "SL", percentile: 0.4 },
    ]);
    expect(lowSeries.yDomain).toEqual([0, 1.4]);
  });

  it("queries trends with the submitted category and switches seat levels cleanly", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          branch_code: "0600624510",
          count: 3,
          trends: [
            { year: 2025, round: 1, level: "SL", percentile: 99.8123456 },
            { year: 2025, round: 1, level: "HU_HU", percentile: 99.1234567 },
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <TrendsSheet
          college={{
            college: "COEP Technological University",
            branch: "Computer Engineering",
            branch_code: "0600624510",
            min_cutoff: 99.1,
            max_cutoff: 99.8,
          }}
          submittedCategory="LOBCH"
          submittedPercentile={99.5}
          onClose={vi.fn()}
        />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("99.8123456")).toBeInTheDocument();
    });

    const [calledUrl] = fetchMock.mock.calls[0] as [string];
    expect(calledUrl).toContain("branch_code=0600624510");
    expect(calledUrl).toContain("category=LOBCH");

    fireEvent.click(screen.getByRole("tab", { name: /HU_HU/i }));
    expect(screen.getByText("99.1234567")).toBeInTheDocument();
  });
});

describe("Shortlist reorder & CSV export", () => {
  afterEach(() => {
    act(() => {
      clearAuthSession();
    });
  });

  it("supports Move Up / Move Down reordering and formats CSV export cleanly", async () => {
    setAuthSession({ token: "jwt-abc", username: "meera" });
    const onReorder = vi.fn().mockResolvedValue({ message: "ok" });
    const onRemove = vi.fn().mockResolvedValue({ message: "ok" });

    const items = [
      { id: 101, college_name: "VJTI Mumbai", branch_name: "Computer Engineering" },
      { id: 102, college_name: "COEP Pune", branch_name: "Information Technology" },
    ];

    render(
      <AuthProvider>
        <ShortlistView
          items={items}
          isLoading={false}
          errorMessage={null}
          onRetry={vi.fn()}
          onReorder={onReorder}
          onRemove={onRemove}
          onBrowseExplorer={vi.fn()}
        />
      </AuthProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /Move COEP Pune up/i }));
    await waitFor(() => {
      expect(onReorder).toHaveBeenCalledWith([102, 101]);
    });

    const csv = buildShortlistCsv(items);
    expect(csv).toContain("Preference Order,College Name,Branch Name");
    expect(csv).toContain('1,"VJTI Mumbai","Computer Engineering"');
    expect(csv).toContain('2,"COEP Pune","Information Technology"');
  });
});
