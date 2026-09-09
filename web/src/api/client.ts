import type {
  AnalyticsResponse,
  ApiErrorResponse,
  Post,
  PostCreate,
  RecommendationResponse,
  ValidationErrorResponse,
  ValidationIssue,
  YouTubeImportRequest,
} from "./types";

function apiBasePath(): string {
  const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
  return configuredBaseUrl ? configuredBaseUrl.replace(/\/+$/, "") : "/api";
}

export class ApiError extends Error {
  readonly status: number;
  readonly validationIssues: ValidationIssue[];
  readonly code: string | null;

  constructor(
    message: string,
    status: number,
    validationIssues: ValidationIssue[] = [],
    code: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.validationIssues = validationIssues;
    this.code = code;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${apiBasePath()}${path}`, {
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
    if (errorBody && isApiErrorResponse(errorBody)) {
      throw new ApiError(
        errorBody.detail.message,
        response.status,
        [],
        errorBody.detail.code,
      );
    }
    throw new ApiError(
      `The backend returned HTTP ${response.status}.`,
      response.status,
      errorBody && isValidationErrorResponse(errorBody)
        ? errorBody.detail
        : [],
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError("The backend returned an invalid response.", response.status);
  }
}

async function readErrorBody(response: Response): Promise<unknown | null> {
  try {
    return (await response.json()) as unknown;
  } catch {
    return null;
  }
}

function isApiErrorResponse(value: unknown): value is ApiErrorResponse {
  if (
    typeof value !== "object" ||
    value === null ||
    !("detail" in value) ||
    typeof value.detail !== "object" ||
    value.detail === null
  ) {
    return false;
  }

  return (
    "code" in value.detail &&
    typeof value.detail.code === "string" &&
    "message" in value.detail &&
    typeof value.detail.message === "string"
  );
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

export function deletePost(postId: number): Promise<void> {
  return request<void>(`/posts/${postId}`, {
    method: "DELETE",
  });
}

export function importYouTubeVideo(
  importRequest: YouTubeImportRequest,
): Promise<Post> {
  return request<Post>("/imports/youtube", {
    method: "POST",
    body: JSON.stringify(importRequest),
  });
}
