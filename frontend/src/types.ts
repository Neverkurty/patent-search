export interface PatentSummary {
  patent_number: string;
  title: string;
  abstract: string;
  ipc_codes: string[];
  publication_date: string | null;
  status: string;
}

export interface PatentDetail extends PatentSummary {
  claims: string;
  application_date: string | null;
  applicants: string[];
  inventors: string[];
}

export interface SearchScores {
  semantic: number | null;
  keyword: number | null;
  final: number;
}

export interface SearchResultItem {
  patent: PatentSummary;
  scores: SearchScores;
}

export interface SearchResponse {
  query: string;
  mode: string;
  results: SearchResultItem[];
  total: number;
  live: boolean;
  fips_message: string | null;
  fips_fetched: number;
}

export type SearchMode = "hybrid" | "semantic" | "keyword";
