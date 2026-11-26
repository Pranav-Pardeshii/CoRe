import {
  closestCenter,
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { ArrowDown, ArrowUp, Download, GripVertical, Printer, Trash2 } from "lucide-react";
import { useState } from "react";
import { ApiClientError } from "../api/errors";
import type { SavedListItem } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { MAX_SHORTLIST_ITEMS } from "../hooks/useSavedShortlist";
import { buildShortlistCsv } from "../lib/formatters";
import { AuthPanel } from "./AuthPanel";

interface ShortlistViewProps {
  items: SavedListItem[];
  isLoading: boolean;
  errorMessage: string | null;
  onRetry: () => void;
  onReorder: (orderedIds: number[]) => Promise<unknown>;
  onRemove: (itemId: number) => Promise<unknown>;
  onBrowseExplorer: () => void;
}

interface SortableRowProps {
  item: SavedListItem;
  index: number;
  total: number;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onRemove: () => void;
}

function SortableShortlistRow({
  item,
  index,
  total,
  onMoveUp,
  onMoveDown,
  onRemove,
}: SortableRowProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: item.id,
  });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <li
      ref={setNodeRef}
      style={style}
      className={`print-list-row flex flex-col gap-2.5 bg-surface px-4 py-3.5 sm:flex-row sm:items-center sm:justify-between ${
        isDragging ? "z-20 ring-2 ring-accent" : ""
      }`}
    >
      <div className="flex min-w-0 items-start gap-3">
        <button
          type="button"
          aria-label={`Drag to reorder preference ${index + 1}`}
          {...attributes}
          {...listeners}
          className="no-print mt-0.5 hidden h-9 w-8 shrink-0 cursor-grab items-center justify-center rounded text-ink-muted hover:bg-recessed hover:text-ink active:cursor-grabbing sm:flex"
        >
          <GripVertical size={16} />
        </button>

        <span className="tabular-nums mt-0.5 inline-flex min-w-[36px] shrink-0 items-center justify-center rounded-[4px] border border-rule-strong bg-recessed px-2 py-0.5 font-mono text-[12.5px] font-semibold text-ink">
          #{index + 1}
        </span>

        <div className="min-w-0">
          <div className="text-[14.5px] font-semibold leading-snug text-ink">
            {item.college_name}
          </div>
          <div className="mt-0.5 text-[13px] text-ink-secondary">{item.branch_name}</div>
        </div>
      </div>

      <div className="no-print flex items-center justify-end gap-1.5">
        <button
          type="button"
          disabled={index === 0}
          aria-label={`Move ${item.college_name} up`}
          onClick={onMoveUp}
          className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-[4px] border border-rule-strong bg-surface text-ink hover:bg-hover disabled:opacity-40"
        >
          <ArrowUp size={16} />
        </button>
        <button
          type="button"
          disabled={index === total - 1}
          aria-label={`Move ${item.college_name} down`}
          onClick={onMoveDown}
          className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-[4px] border border-rule-strong bg-surface text-ink hover:bg-hover disabled:opacity-40"
        >
          <ArrowDown size={16} />
        </button>
        <button
          type="button"
          aria-label={`Remove ${item.college_name} from shortlist`}
          onClick={onRemove}
          className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-[4px] border border-danger/30 bg-surface text-danger hover:bg-danger-tint"
        >
          <Trash2 size={16} />
        </button>
      </div>
    </li>
  );
}

export function ShortlistView({
  items,
  isLoading,
  errorMessage,
  onRetry,
  onReorder,
  onRemove,
  onBrowseExplorer,
}: ShortlistViewProps) {
  const { isAuthenticated, username } = useAuth();
  const [actionError, setActionError] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  if (!isAuthenticated) {
    return (
      <section aria-label="CAP Option Form Shortlist" className="py-4 sm:py-8">
        <div className="mx-auto flex max-w-4xl flex-col items-center gap-6 md:flex-row md:items-start md:justify-between">
          <div className="max-w-md space-y-2.5 pt-1">
            <p className="text-[11.5px] font-semibold tracking-[0.05em] text-accent uppercase">
              CAP Option Form Planner
            </p>
            <h1 className="font-display text-[26px] font-semibold leading-tight text-ink sm:text-[30px]">
              Order your MHT-CET preferences with confidence
            </h1>
            <p className="text-[14px] leading-relaxed text-ink-secondary">
              Save up to {MAX_SHORTLIST_ITEMS} college and branch choices, drag or tap to set your
              exact preference order, and download or print your Option Form before visiting the
              CET Cell portal.
            </p>
          </div>
          <AuthPanel
            title="Sign in or create an account"
            subtitle="Keep your CAP preference list saved across your devices and sessions."
          />
        </div>
      </section>
    );
  }

  async function commitOrder(nextList: SavedListItem[]) {
    setActionError(null);
    try {
      await onReorder(nextList.map((item) => item.id));
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setActionError(err.message);
      } else {
        setActionError("Couldn't update preference order right now. Please try again.");
      }
    }
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = items.findIndex((i) => i.id === active.id);
    const newIndex = items.findIndex((i) => i.id === over.id);
    if (oldIndex === -1 || newIndex === -1) return;
    void commitOrder(arrayMove(items, oldIndex, newIndex));
  }

  function handleStepMove(index: number, delta: -1 | 1) {
    const target = index + delta;
    if (target < 0 || target >= items.length) return;
    void commitOrder(arrayMove(items, index, target));
  }

  async function handleDelete(itemId: number) {
    setActionError(null);
    try {
      await onRemove(itemId);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setActionError(err.message);
      } else {
        setActionError("Couldn't remove that item right now. Please try again.");
      }
    }
  }

  function handleDownloadCsv() {
    const csv = buildShortlistCsv(items);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "core-cap-option-form.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  return (
    <section aria-label="My CAP Option Form Shortlist" className="mt-2">
      {/* Print-only A4 Header */}
      <div className="print-only mb-4 hidden border-b border-black pb-2">
        <h1 className="font-display text-[20px] font-semibold">
          CoRe — MHT-CET CAP Option Form Preference Sheet
        </h1>
        <p className="mt-1 text-[12px]">
          Account: {username} · Total preferences: {items.length}
        </p>
      </div>

      <div className="print-list-container rounded-[6px] border border-rule-strong bg-surface">
        <div className="no-print flex flex-wrap items-center justify-between gap-3 border-b border-rule bg-recessed px-4 py-3.5 sm:px-5">
          <div>
            <h1 className="font-display text-[21px] font-semibold text-ink">
              My CAP Option Form
            </h1>
            <p className="mt-0.5 text-[13px] text-ink-secondary">
              <span className="tabular-nums font-mono font-semibold text-ink">
                {items.length} / {MAX_SHORTLIST_ITEMS}
              </span>{" "}
              choices saved · Top choice is Preference #1
            </p>
          </div>

          {items.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={handleDownloadCsv}
                className="flex min-h-[44px] items-center gap-1.5 rounded-[4px] border border-rule-strong bg-surface px-3 py-1.5 text-[13px] font-medium text-ink hover:bg-hover"
              >
                <Download size={15} />
                <span>Download Option Form (CSV)</span>
              </button>
              <button
                type="button"
                onClick={() => window.print()}
                className="flex min-h-[44px] items-center gap-1.5 rounded-[4px] border border-rule-strong bg-surface px-3 py-1.5 text-[13px] font-medium text-ink hover:bg-hover"
              >
                <Printer size={15} />
                <span>Print</span>
              </button>
            </div>
          )}
        </div>

        {actionError && (
          <div
            role="alert"
            className="no-print border-b border-danger/30 bg-danger-tint px-4 py-2.5 text-[13px] text-danger"
          >
            {actionError}
          </div>
        )}

        {isLoading ? (
          <div className="divide-y divide-rule p-4" aria-busy="true">
            {Array.from({ length: 4 }).map((_, idx) => (
              <div key={idx} className="py-3">
                <div className="h-4 w-2/3 animate-pulse rounded bg-recessed" />
              </div>
            ))}
          </div>
        ) : errorMessage ? (
          <div role="alert" className="px-6 py-10 text-center">
            <p className="text-[14px] font-medium text-danger">{errorMessage}</p>
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 min-h-[40px] rounded-[4px] border border-rule-strong bg-surface px-4 py-2 text-[13px] font-medium text-ink hover:bg-hover"
            >
              Retry
            </button>
          </div>
        ) : items.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <h2 className="font-display text-[19px] font-semibold text-ink">
              Your Option Form is empty
            </h2>
            <p className="mx-auto mt-1.5 max-w-md text-[13.5px] text-ink-secondary">
              Search eligible colleges in the Explorer and tap &ldquo;Save&rdquo; on branches you
              want to include in your CAP preference order.
            </p>
            <button
              type="button"
              onClick={onBrowseExplorer}
              className="mt-4 min-h-[42px] rounded-[4px] bg-accent px-4 py-2 text-[13.5px] font-semibold text-accent-ink hover:bg-accent-hover"
            >
              Open College Explorer
            </button>
          </div>
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext items={items.map((i) => i.id)} strategy={verticalListSortingStrategy}>
              <ol className="divide-y divide-rule">
                {items.map((item, idx) => (
                  <SortableShortlistRow
                    key={item.id}
                    item={item}
                    index={idx}
                    total={items.length}
                    onMoveUp={() => handleStepMove(idx, -1)}
                    onMoveDown={() => handleStepMove(idx, 1)}
                    onRemove={() => void handleDelete(item.id)}
                  />
                ))}
              </ol>
            </SortableContext>
          </DndContext>
        )}
      </div>
    </section>
  );
}
