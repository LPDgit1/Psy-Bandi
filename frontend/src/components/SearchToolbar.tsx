import { Bell, RefreshCw, RotateCcw, Search, SlidersHorizontal } from "lucide-react";
import type { FormEvent } from "react";

type Props = {
  query: string;
  total: number;
  loading: boolean;
  refreshing: boolean;
  onQueryChange: (value: string) => void;
  onSubmit: () => void;
  onToggleFilters: () => void;
  onReset: () => void;
  onRefresh: () => void;
  onOpenAlerts: () => void;
};

export function SearchToolbar({
  query,
  total,
  loading,
  refreshing,
  onQueryChange,
  onSubmit,
  onToggleFilters,
  onReset,
  onRefresh,
  onOpenAlerts
}: Props) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <header className="toolbar">
      <h1 className="toolbar-brand">
        Ricerca Bandi Psicologi
      </h1>

      <form className="search-form" onSubmit={handleSubmit}>
        <label className="sr-only" htmlFor="search">
          Cerca bandi
        </label>
        <div className="search-input-wrap">
          <Search size={18} aria-hidden="true" />
          <input
            id="search"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Cerca per parola chiave, ente, ambito..."
          />
        </div>
        <button className="primary-button" type="submit" title="Cerca">
          <Search size={18} aria-hidden="true" />
          <span>Cerca</span>
        </button>
      </form>

      <div className="toolbar-actions">
        <span className="result-count" aria-live="polite">
          {loading ? "Aggiornamento..." : `${total} risultati`}
        </span>
        <button
          className="secondary-button refresh-button"
          type="button"
          onClick={onRefresh}
          title="Aggiorna tutte le fonti"
          aria-label="Aggiorna tutte le fonti"
          aria-busy={refreshing}
          disabled={refreshing}
        >
          <RefreshCw className={refreshing ? "spin" : undefined} size={18} aria-hidden="true" />
          <span>{refreshing ? "Aggiorno..." : "Aggiorna fonti"}</span>
        </button>
        <button className="icon-button" type="button" onClick={onToggleFilters} title="Filtri">
          <SlidersHorizontal size={19} aria-hidden="true" />
        </button>
        <button className="icon-button" type="button" onClick={onReset} title="Reset filtri">
          <RotateCcw size={18} aria-hidden="true" />
        </button>
        <button className="secondary-button" type="button" onClick={onOpenAlerts}>
          <Bell size={18} aria-hidden="true" />
          <span>Alert</span>
        </button>
      </div>
    </header>
  );
}
