import type {
  AlertPayload,
  Facets,
  Filters,
  OpportunityDetail,
  OpportunityListResponse,
  RefreshResponse
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function withParams(path: string, params: Record<string, string | boolean | undefined>) {
  const url = new URL(`${API_BASE_URL}${path}`);
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === "" || value === false) {
      continue;
    }
    url.searchParams.set(key, String(value));
  }
  return url.toString();
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers
    },
    ...options
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function listOpportunities(filters: Filters): Promise<OpportunityListResponse> {
  return request<OpportunityListResponse>(
    withParams("/api/public/opportunities", {
      q: filters.q,
      region: filters.region,
      province: filters.province,
      category: filters.category,
      entity_type: filters.entity_type,
      area: filters.area,
      status: filters.status,
      deadline: filters.deadline,
      featured: filters.featured,
      sort: filters.sort
    })
  );
}

export function getOpportunity(id: string): Promise<OpportunityDetail> {
  return request<OpportunityDetail>(`${API_BASE_URL}/api/public/opportunities/${id}`);
}

export function getFacets(): Promise<Facets> {
  return request<Facets>(`${API_BASE_URL}/api/public/facets`);
}

export function createAlert(payload: AlertPayload): Promise<{ message: string; status: string }> {
  return request<{ message: string; status: string }>(`${API_BASE_URL}/api/public/alerts`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function refreshSources(): Promise<RefreshResponse> {
  return request<RefreshResponse>(`${API_BASE_URL}/api/public/refresh`, {
    method: "POST"
  });
}

export function getRefreshStatus(): Promise<RefreshResponse> {
  return request<RefreshResponse>(`${API_BASE_URL}/api/public/refresh/status`);
}
