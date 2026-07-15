/**
 * Shared types for the EPSCAxplor API.
 * Shapes mirror the FastAPI response models in services/api/src/routes/ —
 * flat envelopes, errors as { detail: string }.
 */

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface Citation {
  source_number: number;
  union_name: string;
  document_title: string;
  document_type: string;
  effective_date: string | null;
  article: string | null;
  section: string | null;
  article_title: string | null;
  page_number: number | null;
  excerpt: string;
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
  model_used: string;
  disclaimer: string;
  query_log_id: string | null;
}

export interface CorpusDocument {
  id: string;
  union_name: string;
  document_type: string;
  title: string;
  effective_date: string | null;
  expiry_date: string | null;
  is_expired: boolean;
  chunk_count: number | null;
  ingested_at: string | null;
}

export interface DocumentListResponse {
  documents: CorpusDocument[];
  total: number;
}

export interface DocumentFilters {
  union_name?: string;
  document_type?: string;
  is_expired?: boolean;
}

export interface QueryHistoryItem {
  id: string;
  query_text: string;
  answer: string;
  model_used: string;
  citations: Citation[];
  created_at: string;
}

export interface QueryHistoryResponse {
  queries: QueryHistoryItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface QueryHistoryParams {
  limit?: number;
  offset?: number;
}
