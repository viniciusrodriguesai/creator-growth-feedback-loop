import type {
  AnalyticsResponse,
  Post,
  PostCreate,
  RecommendationResponse,
  ValidationErrorResponse,
  ValidationIssue,
} from "./types";

const API_BASE_PATH = "/api";

export class ApiError extends Error {
  readonly status: number;
  readonly validationIssues: ValidationIssue[];

  constructor(
    message: string,
    status: number,
    validationIssues: ValidationIssue[] = [],
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.validationIssues = validationIssues;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_PATH}${path}`, {
      ...options,
      headers: {
        Accept: "application/json",
        ...(options?.body ? { "Content-Type": "application/json" } : {}),
        ...options?.headers,
      },
    });
  } catch {
    throw new ApiError("Unable to connect to the backend.", 0);
  }

  if (!response.ok) {
    const errorBody = await readErrorBody(response);
    throw new ApiError(
      `The backend returned HTTP ${response.status}.`,
      response.status,
      errorBody?.detail ?? [],
    );
  }

  return (await response.json()) as T;
}

async function readErrorBody(
  response: Response,
): Promise<ValidationErrorResponse | null> {
  try {
    const body: unknown = await response.json();
    return isValidationErrorResponse(body) ? body : null;
  } catch {
    return null;
  }
}

function isValidationErrorResponse(
  value: unknown,
): value is ValidationErrorResponse {
  if (typeof value !== "object" || value === null || !("detail" in value)) {
    return false;
  }

  return Array.isArray(value.detail) && value.detail.every(isValidationIssue);
}

function isValidationIssue(value: unknown): value is ValidationIssue {
  return (
    typeof value === "object" &&
    value !== null &&
    "type" in value &&
    typeof value.type === "string" &&
    "loc" in value &&
    Array.isArray(value.loc) &&
    "msg" in value &&
    typeof value.msg === "string"
  );
}

export function getPosts(): Promise<Post[]> {
  return request<Post[]>("/posts");
}

export function getAnalytics(): Promise<AnalyticsResponse> {
  return request<AnalyticsResponse>("/analytics");
}

export function getRecommendation(): Promise<RecommendationResponse> {
  return request<RecommendationResponse>("/recommendations");
}

export function createPost(post: PostCreate): Promise<Post> {
  return request<Post>("/posts", {
    method: "POST",
    body: JSON.stringify(post),
  });
}
