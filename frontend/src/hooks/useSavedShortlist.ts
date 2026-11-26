import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addSavedListItem,
  deleteSavedListItem,
  fetchSavedList,
  reorderSavedList,
} from "../api/client";
import { ApiClientError } from "../api/errors";
import type { SavedListItem, SavedListResponse } from "../api/types";
import { useAuth } from "../context/AuthContext";

export const MAX_SHORTLIST_ITEMS = 100;

function makePairKey(collegeName: string, branchName: string): string {
  return `${collegeName.trim()}::${branchName.trim()}`;
}

export function useSavedShortlist() {
  const { isAuthenticated, username } = useAuth();
  const qc = useQueryClient();
  const queryKey = ["saved-list", username] as const;

  const listQuery = useQuery({
    queryKey,
    queryFn: () => fetchSavedList(),
    enabled: isAuthenticated && Boolean(username),
    staleTime: 60_000,
    retry: (failureCount, error) => {
      if (error instanceof ApiClientError && error.isUnauthorized) {
        return false;
      }
      return failureCount < 1;
    },
  });

  const addMutation = useMutation({
    mutationFn: (branchCode: string) => addSavedListItem(branchCode),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (itemId: number) => deleteSavedListItem(itemId),
    onMutate: async (itemId: number) => {
      await qc.cancelQueries({ queryKey });
      const previous = qc.getQueryData<SavedListResponse>(queryKey);
      if (previous) {
        qc.setQueryData<SavedListResponse>(queryKey, {
          saved_list: previous.saved_list.filter((item) => item.id !== itemId),
        });
      }
      return { previous };
    },
    onError: (_err, _itemId, context) => {
      if (context?.previous) {
        qc.setQueryData(queryKey, context.previous);
      }
      void qc.invalidateQueries({ queryKey });
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey });
    },
  });

  const reorderMutation = useMutation({
    mutationFn: (orderedIds: number[]) => reorderSavedList(orderedIds),
    onMutate: async (orderedIds: number[]) => {
      await qc.cancelQueries({ queryKey });
      const previous = qc.getQueryData<SavedListResponse>(queryKey);
      if (previous) {
        const byId = new Map(previous.saved_list.map((item) => [item.id, item]));
        const nextList: SavedListItem[] = [];
        for (const id of orderedIds) {
          const found = byId.get(id);
          if (found) {
            nextList.push(found);
          }
        }
        if (nextList.length === previous.saved_list.length) {
          qc.setQueryData<SavedListResponse>(queryKey, { saved_list: nextList });
        }
      }
      return { previous };
    },
    onError: (_err, _orderedIds, context) => {
      if (context?.previous) {
        qc.setQueryData(queryKey, context.previous);
      }
      void qc.invalidateQueries({ queryKey });
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey });
    },
  });

  const items = listQuery.data?.saved_list ?? [];
  const savedLookup = new Map<string, { item: SavedListItem; rank: number }>();
  items.forEach((item, index) => {
    savedLookup.set(makePairKey(item.college_name, item.branch_name), {
      item,
      rank: index + 1,
    });
  });

  return {
    items,
    isLoading: listQuery.isLoading,
    isFetching: listQuery.isFetching,
    error: listQuery.error,
    refetch: listQuery.refetch,
    addItem: addMutation.mutateAsync,
    isAdding: addMutation.isPending,
    removeItem: deleteMutation.mutateAsync,
    isRemoving: deleteMutation.isPending,
    reorderItems: reorderMutation.mutateAsync,
    isReordering: reorderMutation.isPending,
    getSavedMatch: (collegeName: string, branchName: string) =>
      savedLookup.get(makePairKey(collegeName, branchName)) ?? null,
  };
}
