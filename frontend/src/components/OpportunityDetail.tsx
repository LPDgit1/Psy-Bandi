import { ExternalLink, FileText, X } from "lucide-react";
import type { OpportunityDetail as Detail } from "../types";
import { formatDate, formatDateTime, labelFor } from "../labels";

type Props = {
  detail: Detail | null;
  loading: boolean;
  onClose: () => void;
};

function DetailRow({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="detail-row">
      <dt>{label}</dt>
      <dd>{value ?? "Non indicato"}</dd>
    </div>
  );
}

export function OpportunityDetail({ detail, loading, onClose }: Props) {
  if (loading) {
    return (
      <section className="detail-panel detail-empty" aria-live="polite">
        Caricamento scheda...
      </section>
    );
  }

  if (!detail) {
    return (
      <section className="detail-panel detail-empty">
        <p>Seleziona un risultato per vedere requisiti, scadenze e fonte ufficiale.</p>
      </section>
    );
  }

  const compensation =
    detail.compensation_min || detail.compensation_max
      ? `${detail.compensation_min ?? ""}${detail.compensation_min && detail.compensation_max ? " - " : ""}${
          detail.compensation_max ?? ""
        } euro${detail.compensation_period ? ` (${detail.compensation_period})` : ""}`
      : null;

  return (
    <section className="detail-panel">
      <div className="detail-header">
        <div>
          <span className={`status-pill status-${detail.status}`}>{labelFor(detail.status)}</span>
          <h2>{detail.title}</h2>
        </div>
        <button className="icon-button mobile-only" type="button" onClick={onClose} title="Chiudi dettaglio">
          <X size={18} aria-hidden="true" />
        </button>
      </div>

      <p className="detail-org">{detail.organization}</p>
      <p className="official-note">
        Le informazioni sono riassunte per facilitare la consultazione. Prima di candidarti verifica sempre il testo
        ufficiale pubblicato dall'ente.
      </p>

      <div className="detail-actions">
        <a className="primary-button link-button" href={detail.official_url} target="_blank" rel="noreferrer">
          <ExternalLink size={18} aria-hidden="true" />
          Apri fonte ufficiale
        </a>
      </div>

      <dl className="detail-grid">
        <DetailRow label="Scadenza" value={formatDate(detail.deadline)} />
        <DetailRow label="Pubblicazione" value={formatDate(detail.published_at)} />
        <DetailRow label="Regione" value={detail.region} />
        <DetailRow label="Provincia" value={detail.province} />
        <DetailRow label="Tipologia" value={labelFor(detail.category)} />
        <DetailRow label="Tipo ente" value={labelFor(detail.entity_type)} />
        <DetailRow label="Posti" value={detail.positions} />
        <DetailRow label="Compenso" value={compensation} />
        <DetailRow label="Durata" value={detail.duration} />
        <DetailRow label="Contratto" value={detail.contract_type} />
      </dl>

      <section className="detail-section">
        <h3>Ambiti</h3>
        <div className="tag-row">
          {detail.areas.map((area) => (
            <span className="tag" key={area}>
              {labelFor(area)}
            </span>
          ))}
        </div>
      </section>

      <section className="detail-section">
        <h3>Requisiti estratti</h3>
        <div className="tag-row">
          {detail.requirements.map((requirement) => (
            <span className="tag tag-muted" key={requirement}>
              {labelFor(requirement)}
            </span>
          ))}
        </div>
      </section>

      {detail.description ? (
        <section className="detail-section">
          <h3>Riepilogo</h3>
          <p>{detail.description}</p>
        </section>
      ) : null}

      {detail.attachments.length > 0 ? (
        <section className="detail-section">
          <h3>Allegati</h3>
          <ul className="attachment-list">
            {detail.attachments.map((attachment) => (
              <li key={attachment.id}>
                <a href={attachment.url} target="_blank" rel="noreferrer">
                  <FileText size={16} aria-hidden="true" />
                  {attachment.title}
                </a>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <footer className="detail-footer">
        Fonte: {detail.source_name ?? "non indicata"} | Ultimo aggiornamento: {formatDateTime(detail.updated_at)}
      </footer>
    </section>
  );
}

