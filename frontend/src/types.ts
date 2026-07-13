export type FacetValue = {
  value: string;
  count: number;
};

export type Facets = {
  regions: FacetValue[];
  provinces: FacetValue[];
  categories: FacetValue[];
  entity_types: FacetValue[];
  areas: FacetValue[];
  statuses: FacetValue[];
};

export type Opportunity = {
  id: string;
  title: string;
  organization: string;
  entity_type: string;
  region: string | null;
  province: string | null;
  municipality: string | null;
  category: string;
  areas: string[];
  status: string;
  deadline: string | null;
  psychology_relevance: string;
  relevance_score: number;
  requirements: string[];
  source_name: string | null;
  official_url: string;
  is_featured: boolean;
  summary: string | null;
  updated_at: string;
};

export type Attachment = {
  id: string;
  title: string;
  url: string;
  file_type: string | null;
};

export type OpportunityDetail = Opportunity & {
  short_description: string | null;
  description: string | null;
  published_at: string | null;
  opens_at: string | null;
  positions: number | null;
  compensation_min: number | null;
  compensation_max: number | null;
  compensation_period: string | null;
  duration: string | null;
  contract_type: string | null;
  application_mode: string | null;
  organization_url: string | null;
  attachments: Attachment[];
};

export type OpportunityListResponse = {
  items: Opportunity[];
  total: number;
  limit: number;
  offset: number;
  facets: Facets;
};

export type Filters = {
  q: string;
  region: string;
  province: string;
  category: string;
  entity_type: string;
  area: string;
  status: string;
  deadline: string;
  featured: boolean;
  sort: string;
};

export type AlertPayload = {
  email: string;
  regions: string[];
  categories: string[];
  areas: string[];
  keywords: string[];
  frequency: string;
};

export type RefreshResponse = {
  status: "completed" | "partial" | "running" | "cooldown";
  message: string;
  created_count: number;
  updated_count: number;
  skipped_count: number;
  retry_after_seconds: number | null;
};
