import { useEffect, useMemo, useState } from "react";
import { getOpportunity, getRefreshStatus, listOpportunities, refreshSources } from "./api";
import { AlertDialog } from "./components/AlertDialog";
import { FilterPanel } from "./components/FilterPanel";
import { OpportunityCard } from "./components/OpportunityCard";
import { OpportunityDetail } from "./components/OpportunityDetail";
import { SearchToolbar } from "./components/SearchToolbar";
import type { Facets, Filters, Opportunity, OpportunityDetail as Detail } from "./types";
import "./styles/app.css";

const emptyFacets: Facets = {
  regions: [],
  provinces: [],
  categories: [],
  entity_types: [],
  areas: [],
  statuses: []
};

function initialFilters(): Filters {
  const params = new URLSearchParams(window.location.search);
  return {
    q: params.get("q") ?? "",
    region: params.get("region") ?? "",
    province: params.get("province") ?? "",
    category: params.get("category") ?? "",
    entity_type: params.get("entity_type") ?? "",
    area: params.get("area") ?? "",
    status: params.get("defaultStatus") === "open" ? "open" : params.get("status") ?? "",
    deadline: "",
    featured: false,
    sort: "deadline"
  };
}

export default function App() {
  const [filters, setFilters] = useState<Filters>(() => initialFilters());
  const [appliedQuery, setAppliedQuery] = useState(filters.q);
  const [items, setItems] = useState<Opportunity[]>([]);
  const [facets, setFacets] = useState<Facets>(emptyFacets);
  const [total, setTotal] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [alertsOpen, setAlertsOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [refreshNotice, setRefreshNotice] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshVersion, setRefreshVersion] = useState(0);

  const effectiveFilters = useMemo(() => ({ ...filters, q: appliedQuery }), [filters, appliedQuery]);

  useEffect(() => {
    let active = true;
    setLoading(true);

    listOpportunities(effectiveFilters)
      .then((response) => {
        if (!active) return;
        setItems(response.items);
        setFacets(response.facets);
        setTotal(response.total);
        setNotice(null);
        setSelectedId((current) =>
          current && response.items.some((item) => item.id === current)
            ? current
            : response.items[0]?.id ?? null
        );
      })
      .catch(() => {
        if (!active) return;
        setItems([]);
        setFacets(emptyFacets);
        setTotal(0);
        setSelectedId(null);
        setDetail(null);
        setNotice("Backend non raggiungibile: le fonti ufficiali non possono essere caricate ora.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [effectiveFilters, refreshVersion]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }

    let active = true;
    setDetailLoading(true);
    getOpportunity(selectedId)
      .then((response) => {
        if (!active) return;
        setDetail(response);
        setNotice(null);
      })
      .catch(() => {
        if (!active) return;
        setDetail(null);
        setNotice("Dettaglio non disponibile: riprova tra poco o apri la fonte ufficiale dalla scheda.");
      })
      .finally(() => {
        if (active) setDetailLoading(false);
      });

    return () => {
      active = false;
    };
  }, [selectedId]);

  function patchFilters(patch: Partial<Filters>) {
    setFilters((current) => ({ ...current, ...patch }));
  }

  function resetFilters() {
    setFilters({
      q: "",
      region: "",
      province: "",
      category: "",
      entity_type: "",
      area: "",
      status: "",
      deadline: "",
      featured: false,
      sort: "deadline"
    });
    setAppliedQuery("");
  }

  async function handleRefresh() {
    setRefreshing(true);
    setRefreshNotice(null);
    try {
      let response = await refreshSources();
      let checks = 0;
      while (response.status === "running" && checks < 240) {
        await new Promise((resolve) => window.setTimeout(resolve, 3000));
        response = await getRefreshStatus();
        checks += 1;
      }
      if (response.status === "running") {
        throw new Error("Refresh timeout");
      }
      const counts =
        response.status === "completed" || response.status === "partial"
          ? ` Nuovi: ${response.created_count}, aggiornati: ${response.updated_count}.`
          : "";
      setRefreshNotice(`${response.message}${counts}`);
      setRefreshVersion((current) => current + 1);
    } catch {
      setRefreshNotice("Aggiornamento non riuscito. Riprova tra poco.");
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <div className="app-shell">
      <SearchToolbar
        query={filters.q}
        total={total}
        loading={loading}
        refreshing={refreshing}
        onQueryChange={(q) => patchFilters({ q })}
        onSubmit={() => setAppliedQuery(filters.q)}
        onToggleFilters={() => setFiltersOpen((value) => !value)}
        onReset={resetFilters}
        onRefresh={handleRefresh}
        onOpenAlerts={() => setAlertsOpen(true)}
      />

      {notice ? <div className="notice">{notice}</div> : null}
      {refreshNotice ? <div className="notice notice-success">{refreshNotice}</div> : null}

      <main className="workspace">
        <FilterPanel
          open={filtersOpen}
          facets={facets}
          filters={filters}
          onChange={patchFilters}
          onClose={() => setFiltersOpen(false)}
        />

        <section className="result-list" aria-label="Risultati">
          {loading ? <div className="list-state">Caricamento risultati...</div> : null}
          {!loading && items.length === 0 ? (
            <div className="list-state">
              Nessun risultato. Prova ad ampliare regione, ambito o scadenza.
            </div>
          ) : null}
          {!loading
            ? items.map((item) => (
                <OpportunityCard
                  key={item.id}
                  opportunity={item}
                  selected={item.id === selectedId}
                  onSelect={(id) => setSelectedId(id)}
                />
              ))
            : null}
        </section>

        <OpportunityDetail
          detail={detail}
          loading={detailLoading}
          onClose={() => {
            setSelectedId(null);
            setDetail(null);
          }}
        />
      </main>

      <AlertDialog open={alertsOpen} filters={filters} onClose={() => setAlertsOpen(false)} />
    </div>
  );
}
