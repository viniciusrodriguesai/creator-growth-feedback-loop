import { useCallback, useEffect, useRef, useState } from "react";

import {
  ApiError,
  getAnalytics,
  getPosts,
  getRecommendation,
} from "../api/client";
import type {
  AnalyticsResponse,
  Post,
  RecommendationResponse,
} from "../api/types";

export interface ResourceState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

interface DashboardState {
  posts: ResourceState<Post[]>;
  analytics: ResourceState<AnalyticsResponse>;
  recommendation: ResourceState<RecommendationResponse>;
}

const emptyResource = <T,>(): ResourceState<T> => ({
  data: null,
  error: null,
  loading: true,
});

const initialState: DashboardState = {
  posts: emptyResource<Post[]>(),
  analytics: emptyResource<AnalyticsResponse>(),
  recommendation: emptyResource<RecommendationResponse>(),
};

function messageFromError(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "An unexpected error occurred while loading this section.";
}

export function useDashboardData() {
  const [state, setState] = useState<DashboardState>(initialState);
  const initialLoadStarted = useRef(false);

  const refreshAll = useCallback(async () => {
    setState((current) => ({
      posts: { ...current.posts, error: null, loading: true },
      analytics: { ...current.analytics, error: null, loading: true },
      recommendation: {
        ...current.recommendation,
        error: null,
        loading: true,
      },
    }));

    const [postsResult, analyticsResult, recommendationResult] =
      await Promise.allSettled([
        getPosts(),
        getAnalytics(),
        getRecommendation(),
      ]);

    setState((current) => ({
      posts:
        postsResult.status === "fulfilled"
          ? { data: postsResult.value, error: null, loading: false }
          : {
              data: current.posts.data,
              error: messageFromError(postsResult.reason),
              loading: false,
            },
      analytics:
        analyticsResult.status === "fulfilled"
          ? { data: analyticsResult.value, error: null, loading: false }
          : {
              data: current.analytics.data,
              error: messageFromError(analyticsResult.reason),
              loading: false,
            },
      recommendation:
        recommendationResult.status === "fulfilled"
          ? { data: recommendationResult.value, error: null, loading: false }
          : {
              data: current.recommendation.data,
              error: messageFromError(recommendationResult.reason),
              loading: false,
            },
    }));
  }, []);

  useEffect(() => {
    if (initialLoadStarted.current) {
      return;
    }
    initialLoadStarted.current = true;
    void refreshAll();
  }, [refreshAll]);

  return { ...state, refreshAll };
}
