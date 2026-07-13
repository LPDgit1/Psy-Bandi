# Contratto API MVP

Base URL locale:

```text
http://localhost:8000
```

## Health

```http
GET /health
```

Risposta:

```json
{ "status": "ok", "environment": "local" }
```

## Lista opportunita

```http
GET /api/public/opportunities
```

Query supportate:

- `q`
- `region`
- `province`
- `category`
- `entity_type`
- `area`
- `status`
- `deadline`: `7d`, `30d`, `future`, `past`, `missing`
- `featured`: `true`/`false`
- `sort`: `deadline`, `recent`, `relevance`, `organization`, `region`
- `limit`
- `offset`

Esempio:

```http
GET /api/public/opportunities?region=Lazio&status=open&q=minori&sort=deadline
```

## Dettaglio opportunita

```http
GET /api/public/opportunities/{id}
```

Restituisce scheda completa con requisiti, ambiti, fonte, allegati e date.

## Faccette

```http
GET /api/public/facets
```

Restituisce conteggi per regione, provincia, tipologia, ente, ambito e stato.

## Alert

```http
POST /api/public/alerts
```

Payload:

```json
{
  "email": "utente@example.it",
  "regions": ["Lazio"],
  "categories": ["avviso-pubblico"],
  "areas": ["minori-famiglia"],
  "keywords": ["tutela minori"],
  "frequency": "weekly"
}
```

Conferma via link email o chiamata API:

```http
POST /api/public/alerts/confirm?token=...
GET /api/public/alerts/confirm?token=...
```

Disiscrizione via link email o chiamata API:

```http
POST /api/public/alerts/unsubscribe?token=...
GET /api/public/alerts/unsubscribe?token=...
```

Invio immediato del report per un alert attivo:

```http
POST /api/public/alerts/send-report?token=...
```

In ambiente locale le email vengono salvate come file `.eml` nella outbox
configurata con `EMAIL_OUTBOX_DIR`; ogni tentativo viene registrato in
`email_logs`.

## Segnalazione

```http
POST /api/public/reports
```

Payload:

```json
{
  "opportunity_id": "opp_123",
  "email": "utente@example.it",
  "message": "La scadenza sembra errata."
}
```

## Admin login

```http
POST /api/admin/auth/login
```

Payload:

```json
{
  "email": "<ADMIN_EMAIL>",
  "password": "<ADMIN_PASSWORD>"
}
```

Risposta:

```json
{
  "access_token": "<ADMIN_API_TOKEN>",
  "token_type": "bearer"
}
```

## Endpoint admin protetti

Usare header:

```http
Authorization: Bearer <ADMIN_API_TOKEN>
```

Endpoint:

- `GET /api/admin/opportunities`
- `PATCH /api/admin/opportunities/{id}`
- `POST /api/admin/opportunities/{id}/approve`
- `POST /api/admin/opportunities/{id}/hide`
- `POST /api/admin/opportunities/{id}/feature?featured=true`
- `GET /api/admin/sources`
- `POST /api/admin/sources/demo/run-import`
- `DELETE /api/admin/sources/demo`
- `POST /api/admin/sources/inpa/run-import?remove_demo=true`
- `POST /api/admin/sources/azienda-zero/run-import`
- `POST /api/admin/sources/asl-roma2/run-import`
- `POST /api/admin/sources/comune-venezia/run-import`
- `POST /api/admin/sources/myportal-treviso/run-import`
- `POST /api/admin/sources/probe`
- `GET /api/admin/import-runs`
