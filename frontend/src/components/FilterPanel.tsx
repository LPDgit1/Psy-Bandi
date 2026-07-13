import { X } from "lucide-react";
import type { FacetValue, Facets, Filters } from "../types";
import { labelFor } from "../labels";

type Props = {
  open: boolean;
  facets: Facets;
  filters: Filters;
  onChange: (patch: Partial<Filters>) => void;
  onClose: () => void;
};

function SelectFilter({
  label,
  value,
  options,
  onChange
}: {
  label: string;
  value: string;
  options: FacetValue[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="filter-field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Tutte</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {labelFor(option.value)} ({option.count})
          </option>
        ))}
      </select>
    </label>
  );
}

export function FilterPanel({ open, facets, filters, onChange, onClose }: Props) {
  return (
    <aside className={`filters ${open ? "filters-open" : ""}`} aria-label="Filtri ricerca">
      <div className="filters-header">
        <h2>Filtri</h2>
        <button className="icon-button mobile-only" type="button" onClick={onClose} title="Chiudi filtri">
          <X size={18} aria-hidden="true" />
        </button>
      </div>

      <div className="quick-filters">
        <button
          className={filters.status === "open" ? "chip chip-active" : "chip"}
          type="button"
          onClick={() => onChange({ status: filters.status === "open" ? "" : "open" })}
        >
          Aperte
        </button>
        <button
          className={filters.deadline === "7d" ? "chip chip-active" : "chip"}
          type="button"
          onClick={() => onChange({ deadline: filters.deadline === "7d" ? "" : "7d" })}
        >
          Scadenza 7 giorni
        </button>
        <button
          className={filters.featured ? "chip chip-active" : "chip"}
          type="button"
          onClick={() => onChange({ featured: !filters.featured })}
        >
          In evidenza
        </button>
      </div>

      <SelectFilter
        label="Regione"
        value={filters.region}
        options={facets.regions}
        onChange={(region) => onChange({ region, province: "" })}
      />
      <SelectFilter
        label="Provincia"
        value={filters.province}
        options={facets.provinces}
        onChange={(province) => onChange({ province })}
      />
      <SelectFilter
        label="Tipologia"
        value={filters.category}
        options={facets.categories}
        onChange={(category) => onChange({ category })}
      />
      <SelectFilter
        label="Ente"
        value={filters.entity_type}
        options={facets.entity_types}
        onChange={(entity_type) => onChange({ entity_type })}
      />
      <SelectFilter
        label="Ambito"
        value={filters.area}
        options={facets.areas}
        onChange={(area) => onChange({ area })}
      />

      <label className="filter-field">
        <span>Scadenza</span>
        <select value={filters.deadline} onChange={(event) => onChange({ deadline: event.target.value })}>
          <option value="">Qualsiasi</option>
          <option value="7d">Entro 7 giorni</option>
          <option value="30d">Entro 30 giorni</option>
          <option value="future">Solo future</option>
          <option value="missing">Da verificare</option>
        </select>
      </label>

      <label className="filter-field">
        <span>Ordina</span>
        <select value={filters.sort} onChange={(event) => onChange({ sort: event.target.value })}>
          <option value="deadline">Scadenza piu vicina</option>
          <option value="recent">Piu recenti</option>
          <option value="relevance">Pertinenza</option>
          <option value="organization">Ente A-Z</option>
          <option value="region">Regione A-Z</option>
        </select>
      </label>
    </aside>
  );
}

