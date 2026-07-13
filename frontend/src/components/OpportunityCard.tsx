import { CalendarDays, ExternalLink, MapPin, Star } from "lucide-react";
import type { Opportunity } from "../types";
import { formatDate, labelFor } from "../labels";

type Props = {
  opportunity: Opportunity;
  selected: boolean;
  onSelect: (id: string) => void;
};

export function OpportunityCard({ opportunity, selected, onSelect }: Props) {
  return (
    <article className={`opportunity-card ${selected ? "selected-card" : ""}`}>
      <button className="card-main" type="button" onClick={() => onSelect(opportunity.id)}>
        <div className="card-topline">
          <span className={`status-pill status-${opportunity.status}`}>{labelFor(opportunity.status)}</span>
          {opportunity.is_featured ? (
            <span className="featured-pill">
              <Star size={14} aria-hidden="true" />
              Evidenza
            </span>
          ) : null}
        </div>

        <h3>{opportunity.title}</h3>
        <p className="organization">{opportunity.organization}</p>

        <div className="meta-row">
          <span>
            <MapPin size={15} aria-hidden="true" />
            {[opportunity.region, opportunity.province].filter(Boolean).join(", ") || "Italia"}
          </span>
          <span>
            <CalendarDays size={15} aria-hidden="true" />
            Scade {formatDate(opportunity.deadline)}
          </span>
        </div>

        <div className="tag-row">
          <span className="tag">{labelFor(opportunity.category)}</span>
          {opportunity.areas.slice(0, 2).map((area) => (
            <span className="tag tag-muted" key={area}>
              {labelFor(area)}
            </span>
          ))}
        </div>

        {opportunity.summary ? <p className="summary">{opportunity.summary}</p> : null}
      </button>

      <a className="source-link" href={opportunity.official_url} target="_blank" rel="noreferrer">
        <ExternalLink size={15} aria-hidden="true" />
        Fonte ufficiale
      </a>
    </article>
  );
}

