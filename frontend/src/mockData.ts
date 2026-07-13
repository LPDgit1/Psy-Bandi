import type { Facets, Opportunity, OpportunityDetail, OpportunityListResponse } from "./types";

export const mockFacets: Facets = {
  regions: [
    { value: "Lazio", count: 2 },
    { value: "Lombardia", count: 1 },
    { value: "Veneto", count: 1 }
  ],
  provinces: [
    { value: "RM", count: 1 },
    { value: "FR", count: 1 },
    { value: "MI", count: 1 },
    { value: "PD", count: 1 }
  ],
  categories: [
    { value: "avviso-pubblico", count: 2 },
    { value: "concorso-pubblico", count: 1 },
    { value: "borsa-assegno-ricerca", count: 1 }
  ],
  entity_types: [
    { value: "comune", count: 1 },
    { value: "azienda-sanitaria-ospedaliera", count: 1 },
    { value: "universita", count: 1 },
    { value: "scuola-istituto-scolastico", count: 1 }
  ],
  areas: [
    { value: "minori-famiglia", count: 2 },
    { value: "servizi-sociali", count: 1 },
    { value: "psicoterapia", count: 1 },
    { value: "neuropsicologia", count: 1 }
  ],
  statuses: [
    { value: "open", count: 3 },
    { value: "closing_soon", count: 1 }
  ]
};

export const mockOpportunities: Opportunity[] = [
  {
    id: "demo-001",
    title: "Avviso pubblico per psicologo nei servizi tutela minori",
    organization: "Comune di Frosinone",
    entity_type: "comune",
    region: "Lazio",
    province: "FR",
    municipality: "Frosinone",
    category: "avviso-pubblico",
    areas: ["servizi-sociali", "minori-famiglia"],
    status: "open",
    deadline: "2026-06-18T23:59:00+02:00",
    psychology_relevance: "alta",
    relevance_score: 100,
    requirements: ["iscrizione-albo", "esperienza-minima"],
    source_name: "Fonte demo aggregata",
    official_url: "https://example.test/comune-frosinone/avviso-psicologo-minori",
    is_featured: true,
    summary:
      "Incarico libero professionale per supporto al servizio tutela minori e famiglia.",
    updated_at: "2026-05-29T12:00:00+02:00"
  },
  {
    id: "demo-002",
    title: "Concorso pubblico per dirigente psicologo disciplina psicoterapia",
    organization: "Azienda Sanitaria Locale Roma 2",
    entity_type: "azienda-sanitaria-ospedaliera",
    region: "Lazio",
    province: "RM",
    municipality: "Roma",
    category: "concorso-pubblico",
    areas: ["psicoterapia", "salute-mentale"],
    status: "open",
    deadline: "2026-06-28T23:59:00+02:00",
    psychology_relevance: "alta",
    relevance_score: 100,
    requirements: ["laurea-psicologia", "abilitazione", "iscrizione-albo", "psicoterapia"],
    source_name: "Fonte demo aggregata",
    official_url: "https://example.test/asl-roma-2/concorso-dirigente-psicologo",
    is_featured: true,
    summary: "Concorso per dirigente psicologo con specializzazione in psicoterapia.",
    updated_at: "2026-05-29T12:00:00+02:00"
  },
  {
    id: "demo-003",
    title: "Borsa di ricerca in neuropsicologia dell'invecchiamento",
    organization: "Universita degli Studi di Padova",
    entity_type: "universita",
    region: "Veneto",
    province: "PD",
    municipality: "Padova",
    category: "borsa-assegno-ricerca",
    areas: ["neuropsicologia", "ricerca", "anziani"],
    status: "closing_soon",
    deadline: "2026-06-12T23:59:00+02:00",
    psychology_relevance: "media",
    relevance_score: 50,
    requirements: ["non-determinato"],
    source_name: "Fonte demo aggregata",
    official_url: "https://example.test/unipd/borsa-neuropsicologia",
    is_featured: false,
    summary: "Borsa di ricerca su disturbi cognitivi, demenza e riabilitazione cognitiva.",
    updated_at: "2026-05-29T12:00:00+02:00"
  }
];

export const mockListResponse: OpportunityListResponse = {
  items: mockOpportunities,
  total: mockOpportunities.length,
  limit: 20,
  offset: 0,
  facets: mockFacets
};

export function mockDetail(id: string): OpportunityDetail {
  const item = mockOpportunities.find((opportunity) => opportunity.id === id) ?? mockOpportunities[0];
  return {
    ...item,
    short_description: item.summary,
    description:
      item.summary ??
      "Scheda demo disponibile quando il backend non e' ancora avviato in locale.",
    published_at: "2026-05-20T10:00:00+02:00",
    opens_at: null,
    positions: 1,
    compensation_min: null,
    compensation_max: item.id === "demo-001" ? 18000 : null,
    compensation_period: item.id === "demo-001" ? "forfait" : null,
    duration: item.id === "demo-001" ? "12 mesi" : null,
    contract_type: item.category,
    application_mode: "Consultare la fonte ufficiale.",
    organization_url: null,
    attachments: []
  };
}

