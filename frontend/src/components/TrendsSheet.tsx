import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchTrends } from "../api/client";
import type { EligibleCollege, TrendPoint } from "../api/types";
import { decodeCategory, decodeSeatLevel } from "../lib/categoryLabels";
import { formatAxisPercentile, formatPercentile } from "../lib/formatters";

interface TrendsSheetProps {
  college: EligibleCollege | null;
  submittedCategory: string;
  submittedPercentile: number;
  onClose: () => void;
}

export interface ChartRoundRow {
  roundLabel: string;
  round: number;
  [yearKey: string]: number | string;
}

const YEAR_SERIES_COLORS = [
  "oklch(0.390 0.115 262)", // Deep Gazette Indigo (latest)
  "oklch(0.520 0.110 42)", // Burnt Sienna
  "oklch(0.410 0.095 178)", // Spruce Teal
];

export function groupTrendsByLevel(trends: readonly TrendPoint[]): {
  levels: string[];
  byLevel: Record<string, TrendPoint[]>;
} {
  const byLevel: Record<string, TrendPoint[]> = {};
  for (const pt of trends) {
    const bucket = byLevel[pt.level];
    if (bucket) {
      bucket.push(pt);
    } else {
      byLevel[pt.level] = [pt];
    }
  }
  const levels = Object.keys(byLevel).sort((a, b) => {
    if (a === "SL") return -1;
    if (b === "SL") return 1;
    return a.localeCompare(b);
  });
  return { levels, byLevel };
}

export function buildRoundSeriesForLevel(points: readonly TrendPoint[]): {
  chartData: ChartRoundRow[];
  years: number[];
  yDomain: [number, number];
} {
  if (points.length === 0) {
    return { chartData: [], years: [], yDomain: [0, 100] };
  }

  const years = Array.from(new Set(points.map((p) => p.year))).sort((a, b) => b - a);
  const rounds = Array.from(new Set(points.map((p) => p.round))).sort((a, b) => a - b);

  const chartData: ChartRoundRow[] = rounds.map((round) => {
    const row: ChartRoundRow = {
      roundLabel: `R${round}`,
      round,
    };
    for (const year of years) {
      const match = points.find((p) => p.year === year && p.round === round);
      if (match !== undefined) {
        row[`y_${year}`] = match.percentile;
      }
    }
    return row;
  });

  let minVal = Infinity;
  let maxVal = -Infinity;
  for (const pt of points) {
    if (pt.percentile < minVal) minVal = pt.percentile;
    if (pt.percentile > maxVal) maxVal = pt.percentile;
  }

  const yDomain: [number, number] = [
    Math.max(0, Number((minVal - 1).toFixed(4))),
    Math.min(100, Number((maxVal + 1).toFixed(4))),
  ];

  return { chartData, years, yDomain };
}

export function TrendsSheet({
  college,
  submittedCategory,
  submittedPercentile,
  onClose,
}: TrendsSheetProps) {
  const queryCategory = submittedCategory === "All" ? "GOPENS" : submittedCategory;
  const branchCode = college?.branch_code ?? "";

  const trendsQuery = useQuery({
    queryKey: ["trends", branchCode, queryCategory],
    queryFn: ({ signal }) => fetchTrends(branchCode, queryCategory, undefined, signal),
    enabled: Boolean(college),
    staleTime: 10 * 60 * 1000,
  });

  const grouped = useMemo(
    () => groupTrendsByLevel(trendsQuery.data?.trends ?? []),
    [trendsQuery.data?.trends],
  );

  const [selectedLevel, setSelectedLevel] = useState<string>("");

  useEffect(() => {
    if (grouped.levels.length > 0 && !grouped.levels.includes(selectedLevel)) {
      setSelectedLevel(grouped.levels[0] ?? "");
    }
  }, [grouped.levels, selectedLevel]);

  useEffect(() => {
    if (!college) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [college, onClose]);

  if (!college) {
    return null;
  }

  const activeLevel = grouped.levels.includes(selectedLevel)
    ? selectedLevel
    : (grouped.levels[0] ?? "");
  const activePoints = activeLevel ? (grouped.byLevel[activeLevel] ?? []) : [];
  const { chartData, years, yDomain } = buildRoundSeriesForLevel(activePoints);
  const categoryInfo = decodeCategory(queryCategory);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Cutoff history for ${college.college}`}
      className="no-print fixed inset-0 z-50 flex justify-end bg-ink/40"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="flex h-full w-full flex-col overflow-y-auto bg-surface md:max-w-[580px] md:border-l md:border-rule-strong">
        <div className="sticky top-0 z-10 flex items-start justify-between gap-3 border-b border-rule bg-surface px-4 py-4 sm:px-6">
          <div className="min-w-0">
            <span className="tabular-nums rounded-[4px] bg-recessed px-1.5 py-0.5 font-mono text-[11.5px] text-ink-secondary">
              {college.branch_code}
            </span>
            <h2 className="mt-1.5 font-display text-[20px] font-semibold leading-snug text-ink">
              {college.college}
            </h2>
            <p className="mt-0.5 text-[13.5px] text-ink-secondary">{college.branch}</p>
          </div>
          <button
            type="button"
            aria-label="Close cutoff history"
            onClick={onClose}
            className="flex min-h-[44px] min-w-[44px] shrink-0 items-center justify-center rounded-[4px] border border-rule-strong bg-surface text-ink-secondary hover:bg-hover hover:text-ink"
          >
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 space-y-5 px-4 py-5 sm:px-6">
          <div className="border-l-2 border-accent bg-recessed/70 px-3.5 py-2.5 text-[13px] text-ink-secondary">
            Closing cutoffs across past CAP rounds for{" "}
            <span className="font-semibold text-ink">{categoryInfo.displayText}</span>
            {submittedCategory === "All" && (
              <span> (showing General Open State Level when &ldquo;All&rdquo; is selected)</span>
            )}
            .
          </div>

          {trendsQuery.isLoading ? (
            <div className="space-y-3" aria-busy="true">
              <div className="h-[240px] w-full animate-pulse rounded-[6px] bg-recessed" />
              <div className="h-28 w-full animate-pulse rounded-[6px] bg-recessed" />
            </div>
          ) : trendsQuery.isError ? (
            <div role="alert" className="rounded-[6px] border border-danger/30 bg-danger-tint p-4">
              <p className="text-[13.5px] font-medium text-danger">
                {trendsQuery.error instanceof Error
                  ? trendsQuery.error.message
                  : "Couldn't load cutoff history for this branch right now."}
              </p>
              <button
                type="button"
                onClick={() => void trendsQuery.refetch()}
                className="mt-3 min-h-[38px] rounded-[4px] border border-danger/40 bg-surface px-3 py-1.5 text-[13px] font-medium text-danger hover:bg-hover"
              >
                Try again
              </button>
            </div>
          ) : activePoints.length === 0 ? (
            <div className="rounded-[6px] border border-rule bg-canvas p-6 text-center">
              <p className="text-[14px] font-medium text-ink">
                Not enough historical CAP round data for this category.
              </p>
              <p className="mt-1 text-[13px] text-ink-secondary">
                Some reserved or special quotas only appear in years when seats were allotted.
              </p>
            </div>
          ) : (
            <>
              {grouped.levels.length > 1 && (
                <div>
                  <div className="mb-2 text-[11.5px] font-semibold tracking-[0.04em] text-ink-muted uppercase">
                    Seat Allocation Level
                  </div>
                  <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Seat level">
                    {grouped.levels.map((level) => {
                      const active = level === activeLevel;
                      return (
                        <button
                          key={level}
                          type="button"
                          role="tab"
                          aria-selected={active}
                          onClick={() => setSelectedLevel(level)}
                          className={`min-h-[40px] rounded-[4px] border px-2.5 py-1.5 text-[12.5px] font-medium transition-colors ${
                            active
                              ? "border-accent bg-accent-tint text-accent"
                              : "border-rule-strong bg-surface text-ink-secondary hover:bg-hover hover:text-ink"
                          }`}
                        >
                          <span className="font-mono">{level}</span> · {decodeSeatLevel(level)}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="border-y border-rule bg-canvas px-2 py-3 sm:px-3">
                <div className="mb-2 flex items-center justify-between text-[12px] text-ink-secondary">
                  <span>{decodeSeatLevel(activeLevel)}</span>
                  <span className="tabular-nums font-mono">
                    Your score: {formatPercentile(submittedPercentile)}
                  </span>
                </div>

                <div className="h-[240px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={chartData}
                      margin={{ top: 10, right: 16, left: 4, bottom: 4 }}
                    >
                      <CartesianGrid stroke="oklch(0.892 0.006 252)" strokeDasharray="3 3" />
                      <XAxis
                        dataKey="roundLabel"
                        tick={{ fontSize: 12, fill: "oklch(0.425 0.014 260)" }}
                      />
                      <YAxis
                        domain={yDomain}
                        width={54}
                        tickFormatter={(v: number) => formatAxisPercentile(v)}
                        tick={{ fontSize: 11.5, fill: "oklch(0.425 0.014 260)" }}
                      />
                      <Tooltip
                        formatter={(value: unknown, name: unknown) => [
                          formatPercentile(Number(value)),
                          String(name).replace("y_", "Year "),
                        ]}
                        contentStyle={{
                          backgroundColor: "oklch(1 0 0)",
                          border: "1px solid oklch(0.785 0.010 252)",
                          borderRadius: "4px",
                          fontSize: "12.5px",
                        }}
                      />
                      <Legend
                        formatter={(value: string) => value.replace("y_", "Admission ")}
                        wrapperStyle={{ fontSize: "12px" }}
                      />
                      {submittedPercentile >= yDomain[0] && submittedPercentile <= yDomain[1] && (
                        <ReferenceLine
                          y={submittedPercentile}
                          stroke="oklch(0.410 0.095 178)"
                          strokeDasharray="4 4"
                          label={{
                            value: "Your %ile",
                            position: "insideTopRight",
                            fill: "oklch(0.410 0.095 178)",
                            fontSize: 11,
                          }}
                        />
                      )}
                      {years.map((year, idx) => (
                        <Line
                          key={year}
                          type="monotone"
                          dataKey={`y_${year}`}
                          name={`y_${year}`}
                          stroke={YEAR_SERIES_COLORS[idx % YEAR_SERIES_COLORS.length]}
                          strokeWidth={2.25}
                          strokeDasharray={idx === 1 ? "5 4" : undefined}
                          dot={{ r: 4 }}
                          activeDot={{ r: 6 }}
                          connectNulls
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Compact exact-value reference table */}
              <div className="overflow-hidden rounded-[6px] border border-rule">
                <table className="w-full border-collapse text-left">
                  <thead>
                    <tr className="border-b border-rule bg-recessed text-[11.5px] font-semibold tracking-[0.04em] text-ink-muted uppercase">
                      <th className="px-3 py-2">Year</th>
                      <th className="px-3 py-2">CAP Round</th>
                      <th className="px-3 py-2">Seat Level</th>
                      <th className="px-3 py-2 text-right">Closing Percentile</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-rule">
                    {activePoints.map((pt) => (
                      <tr key={`${pt.year}-${pt.round}-${pt.level}`} className="bg-surface">
                        <td className="tabular-nums px-3 py-2 font-mono text-[13px] text-ink">
                          {pt.year}
                        </td>
                        <td className="tabular-nums px-3 py-2 font-mono text-[13px] text-ink-secondary">
                          R{pt.round}
                        </td>
                        <td className="px-3 py-2 text-[12.5px] text-ink-secondary">
                          <span className="font-mono">{pt.level}</span>
                        </td>
                        <td className="tabular-nums px-3 py-2 text-right font-mono text-[13px] font-semibold text-ink">
                          {formatPercentile(pt.percentile)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
