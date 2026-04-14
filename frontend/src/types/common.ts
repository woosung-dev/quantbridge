// 전역 공통 타입 — 도메인 무관

export type Uuid = string & { readonly __brand: "Uuid" };

export interface Timestamped {
  created_at: string;
  updated_at: string;
}

// FastAPI 표준 페이지네이션 응답
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// FastAPI 표준 에러 응답 (backend exceptions.py와 1:1 매핑)
export interface ApiErrorBody {
  code: string;
  message: string;
  detail?: Record<string, unknown>;
}

export type Nullable<T> = T | null;
export type Maybe<T> = T | undefined;
