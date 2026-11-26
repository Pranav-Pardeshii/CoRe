export interface CatalogFiltersResponse {
  categories: string[];
  branches: string[];
  divisions: string[];
  years: number[];
  levels: string[];
}

export interface EligibleCollege {
  college: string;
  branch: string;
  branch_code: string;
  min_cutoff: number;
  max_cutoff: number;
}

export interface RecommenderResponse {
  eligible_colleges: EligibleCollege[];
  count: number;
}

export interface RecommenderParams {
  percentile: number;
  category: string;
  branch: string;
  division: string;
  page: number;
  page_size: number;
}

export interface TrendPoint {
  year: number;
  round: number;
  level: string;
  percentile: number;
}

export interface TrendsResponse {
  branch_code: string;
  count: number;
  trends: TrendPoint[];
}

export interface RegisterResponse {
  message: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface SavedListItem {
  id: number;
  college_name: string;
  branch_name: string;
}

export interface SavedListResponse {
  saved_list: SavedListItem[];
}

export interface SavedListMessageResponse {
  message: string;
}
