import { Check, ChevronDown, Search, X } from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState } from "react";

export interface SelectOption {
  value: string;
  label: string;
  code?: string;
  keywords?: string;
}

interface SearchableSelectProps {
  label: string;
  value: string;
  options: readonly SelectOption[];
  onChange: (value: string) => void;
  searchPlaceholder?: string;
  disabled?: boolean;
}

export function SearchableSelect({
  label,
  value,
  options,
  onChange,
  searchPlaceholder = "Type to filter…",
  disabled = false,
}: SearchableSelectProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const buttonId = useId();
  const listboxId = useId();

  const selectedOption = useMemo(
    () => options.find((opt) => opt.value === value) ?? { value, label: value },
    [options, value],
  );

  const filteredOptions = useMemo(() => {
    const trimmed = query.trim().toLowerCase();
    if (!trimmed) {
      return options;
    }
    return options.filter((opt) => {
      const hay = `${opt.label} ${opt.value} ${opt.code ?? ""} ${opt.keywords ?? ""}`.toLowerCase();
      return hay.includes(trimmed);
    });
  }, [options, query]);

  useEffect(() => {
    if (!open) {
      setQuery("");
      return;
    }
    const timer = setTimeout(() => {
      searchInputRef.current?.focus();
    }, 0);

    function handleOutsideClick(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handleOutsideClick);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      clearTimeout(timer);
      document.removeEventListener("mousedown", handleOutsideClick);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <div ref={containerRef} className="relative">
      <label
        htmlFor={buttonId}
        className="mb-1.5 block text-[11.5px] font-semibold tracking-[0.04em] text-ink-muted uppercase"
      >
        {label}
      </label>

      <button
        id={buttonId}
        type="button"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listboxId}
        onClick={() => setOpen((prev) => !prev)}
        className="flex min-h-[44px] w-full items-center justify-between gap-2 rounded-[6px] border border-rule-strong bg-surface px-3 py-2 text-left text-[14px] text-ink transition-colors hover:bg-hover disabled:opacity-60"
      >
        <span className="flex min-w-0 items-center gap-2">
          {selectedOption.code && (
            <span className="shrink-0 rounded-[4px] bg-recessed px-1.5 py-0.5 font-mono text-[12px] font-medium text-ink">
              {selectedOption.code}
            </span>
          )}
          <span className="truncate font-medium">{selectedOption.label}</span>
        </span>
        <ChevronDown
          size={16}
          className={`shrink-0 text-ink-muted transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div className="absolute right-0 left-0 z-40 mt-1.5 overflow-hidden rounded-[6px] border border-rule-strong bg-surface shadow-lg">
          <div className="flex items-center gap-2 border-b border-rule bg-recessed px-2.5 py-2">
            <Search size={15} className="shrink-0 text-ink-muted" />
            <input
              ref={searchInputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={searchPlaceholder}
              aria-label={`Search ${label}`}
              className="w-full bg-transparent text-[13.5px] text-ink placeholder:text-ink-muted focus:outline-none"
            />
            {query && (
              <button
                type="button"
                aria-label="Clear filter text"
                onClick={() => setQuery("")}
                className="rounded p-1 text-ink-muted hover:text-ink"
              >
                <X size={14} />
              </button>
            )}
          </div>

          <ul
            id={listboxId}
            role="listbox"
            aria-label={label}
            className="max-h-[min(16rem,50vh)] overflow-y-auto py-1"
          >
            {filteredOptions.length === 0 ? (
              <li className="px-3 py-3 text-[13px] text-ink-muted">
                No matching options found.
              </li>
            ) : (
              filteredOptions.map((opt) => {
                const isSelected = opt.value === value;
                return (
                  <li key={opt.value} role="option" aria-selected={isSelected}>
                    <button
                      type="button"
                      onClick={() => {
                        onChange(opt.value);
                        setOpen(false);
                      }}
                      className={`flex min-h-[44px] w-full items-center justify-between gap-2 px-3 py-2 text-left text-[13.5px] transition-colors hover:bg-hover ${
                        isSelected ? "bg-accent-tint font-medium text-accent" : "text-ink"
                      }`}
                    >
                      <span className="flex min-w-0 items-center gap-2">
                        {opt.code && (
                          <span className="shrink-0 rounded-[4px] border border-rule bg-surface px-1.5 py-0.5 font-mono text-[11.5px] font-medium text-ink">
                            {opt.code}
                          </span>
                        )}
                        <span className="truncate">{opt.label}</span>
                      </span>
                      {isSelected && <Check size={15} className="shrink-0 text-accent" />}
                    </button>
                  </li>
                );
              })
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
