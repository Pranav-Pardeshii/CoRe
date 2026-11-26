import { BookmarkCheck, Compass, LogOut, User } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import type { AppView } from "../lib/urlFilters";

interface HeaderProps {
  activeView: AppView;
  onChangeView: (view: AppView) => void;
  savedCount: number;
  onOpenAuthModal: () => void;
}

export function Header({
  activeView,
  onChangeView,
  savedCount,
  onOpenAuthModal,
}: HeaderProps) {
  const { isAuthenticated, username, logout } = useAuth();

  return (
    <header className="no-print sticky top-0 z-30 border-b border-rule bg-surface">
      <div className="mx-auto flex max-w-[1320px] items-center justify-between gap-2 px-3 py-2 sm:px-6 sm:py-2.5">
        <div className="flex min-w-0 items-baseline gap-2.5">
          <button
            type="button"
            onClick={() => onChangeView("explorer")}
            className="min-h-[40px] font-display text-[21px] font-semibold tracking-[-0.02em] text-ink sm:text-[22px]"
          >
            CoRe
          </button>
          <span className="hidden text-[12.5px] font-medium text-ink-muted md:inline">
            MHT-CET Engineering Explorer
          </span>
        </div>

        <nav aria-label="Primary" className="flex shrink-0 items-center gap-1.5 sm:gap-2">
          <div className="flex rounded-[6px] border border-rule bg-recessed p-0.5">
            <button
              type="button"
              onClick={() => onChangeView("explorer")}
              aria-current={activeView === "explorer" ? "page" : undefined}
              className={`flex min-h-[38px] items-center gap-1.5 rounded-[4px] px-2.5 py-1 text-[12.5px] font-medium transition-colors sm:px-3 sm:text-[13px] ${
                activeView === "explorer"
                  ? "bg-surface text-ink shadow-[0_1px_0_rgba(0,0,0,0.06)]"
                  : "text-ink-secondary hover:text-ink"
              }`}
            >
              <Compass size={15} />
              <span>Explorer</span>
            </button>

            <button
              type="button"
              onClick={() => onChangeView("shortlist")}
              aria-current={activeView === "shortlist" ? "page" : undefined}
              className={`flex min-h-[38px] items-center gap-1.5 rounded-[4px] px-2.5 py-1 text-[12.5px] font-medium transition-colors sm:px-3 sm:text-[13px] ${
                activeView === "shortlist"
                  ? "bg-surface text-ink shadow-[0_1px_0_rgba(0,0,0,0.06)]"
                  : "text-ink-secondary hover:text-ink"
              }`}
            >
              <BookmarkCheck size={15} />
              <span className="sm:hidden">Shortlist</span>
              <span className="hidden sm:inline">My Shortlist</span>
              {isAuthenticated && (
                <span className="tabular-nums rounded-full bg-accent-tint px-1.5 py-0.5 font-mono text-[11px] font-semibold text-accent">
                  {savedCount}
                </span>
              )}
            </button>
          </div>

          {isAuthenticated ? (
            <div className="flex items-center gap-1.5">
              <span className="hidden items-center gap-1.5 rounded-[4px] border border-rule bg-recessed px-2.5 py-1.5 text-[12.5px] font-medium text-ink md:inline-flex">
                <User size={13} className="text-ink-muted" />
                <span className="max-w-[120px] truncate">{username}</span>
              </span>
              <button
                type="button"
                onClick={logout}
                aria-label="Sign out"
                className="flex min-h-[40px] items-center gap-1 rounded-[4px] border border-rule-strong bg-surface px-2.5 py-1.5 text-[12.5px] font-medium text-ink-secondary transition-colors hover:bg-hover hover:text-ink"
              >
                <LogOut size={14} />
                <span className="hidden sm:inline">Sign out</span>
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={onOpenAuthModal}
              className="flex min-h-[40px] items-center gap-1.5 rounded-[4px] border border-rule-strong bg-surface px-2.5 py-1.5 text-[12.5px] font-medium text-ink transition-colors hover:bg-hover sm:px-3 sm:text-[13px]"
            >
              <User size={14} />
              <span>Sign in</span>
            </button>
          )}
        </nav>
      </div>
    </header>
  );
}
