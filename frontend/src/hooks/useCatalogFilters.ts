import { useQuery } from "@tanstack/react-query";
import { fetchCatalogFilters } from "../api/client";

const THIRTY_MINUTES_MS = 30 * 60 * 1000;

export function useCatalogFilters() {
  return useQuery({
    queryKey: ["catalog", "filters"],
    queryFn: ({ signal }) => fetchCatalogFilters(signal),
    staleTime: THIRTY_MINUTES_MS,
    gcTime: THIRTY_MINUTES_MS * 2,
    retry: 2,
  });
}
