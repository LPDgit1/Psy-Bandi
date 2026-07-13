import { Bell, X } from "lucide-react";
import type { FormEvent } from "react";
import { useState } from "react";
import { createAlert } from "../api";
import type { Filters } from "../types";

type Props = {
  open: boolean;
  filters: Filters;
  onClose: () => void;
};

export function AlertDialog({ open, filters, onClose }: Props) {
  const [email, setEmail] = useState("");
  const [frequency, setFrequency] = useState("weekly");
  const [status, setStatus] = useState<string | null>(null);

  if (!open) {
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("Invio in corso...");
    try {
      const response = await createAlert({
        email,
        frequency,
        regions: filters.region ? [filters.region] : [],
        categories: filters.category ? [filters.category] : [],
        areas: filters.area ? [filters.area] : [],
        keywords: filters.q ? [filters.q] : []
      });
      setStatus(response.message);
    } catch {
      setStatus("Backend non disponibile: il form e' pronto, ma l'alert non e' stato salvato.");
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <section className="alert-dialog" role="dialog" aria-modal="true" aria-labelledby="alert-title">
        <div className="dialog-header">
          <h2 id="alert-title">
            <Bell size={19} aria-hidden="true" />
            Attiva alert
          </h2>
          <button className="icon-button" type="button" onClick={onClose} title="Chiudi">
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        <form className="alert-form" onSubmit={handleSubmit}>
          <label className="filter-field">
            <span>Email</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="nome@example.it"
              required
            />
          </label>

          <label className="filter-field">
            <span>Frequenza</span>
            <select value={frequency} onChange={(event) => setFrequency(event.target.value)}>
              <option value="weekly">Settimanale</option>
              <option value="daily">Giornaliera</option>
            </select>
          </label>

          <label className="consent-row">
            <input type="checkbox" required />
            <span>Accetto l'informativa privacy e confermo di voler ricevere alert sui bandi.</span>
          </label>

          <button className="primary-button" type="submit">
            <Bell size={18} aria-hidden="true" />
            Salva alert
          </button>
        </form>

        {status ? <p className="dialog-status" aria-live="polite">{status}</p> : null}
      </section>
    </div>
  );
}

