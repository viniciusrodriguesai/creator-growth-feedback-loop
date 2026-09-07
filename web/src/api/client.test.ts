import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, importYouTubeVideo } from "./client";
import type { Post, YouTubeImportRequest } from "./types";

const importRequest: YouTubeImportRequest = {
  url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  hook_type: "pain_point",
  format: "short",
};

const importedPost: Post = {
  id: 1,
  platform: "youtube",
  title: "A public video",
  hook_type: "pain_point",
  format: "short",
  creator: "Creator Channel",
  views: 12_000,
  likes: 850,
  comments: 42,
  shares: null,
  duration_seconds: 73,
  published_at: "2026-08-20T14:30:00Z",
};

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("importYouTubeVideo", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts the typed request to the YouTube import endpoint", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(jsonResponse(importedPost, 201));
    vi.stubGlobal("fetch", fetchMock);

    const result: Post = await importYouTubeVideo(importRequest);

    expect(result).toEqual(importedPost);
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledWith("/api/imports/youtube", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(importRequest),
    });
  });

  it("preserves a structured backend API error safely", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(
        jsonResponse(
          {
            detail: {
              code: "youtube_video_not_found",
              message: "The requested YouTube video was not found.",
            },
          },
          404,
        ),
      ),
    );

    await expect(importYouTubeVideo(importRequest)).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      code: "youtube_video_not_found",
      message: "The requested YouTube video was not found.",
      validationIssues: [],
    });
  });

  it("replaces a malformed backend error with a safe fallback", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(
        jsonResponse(
          { detail: { code: 409, message: ["raw", "unexpected"] } },
          409,
        ),
      ),
    );

    await expect(importYouTubeVideo(importRequest)).rejects.toMatchObject({
      name: "ApiError",
      status: 409,
      code: null,
      message: "The backend returned HTTP 409.",
      validationIssues: [],
    });
  });

  it("replaces a non-JSON error response with a safe fallback", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn<typeof fetch>()
        .mockResolvedValue(new Response("<html>proxy failure</html>", { status: 502 })),
    );

    await expect(importYouTubeVideo(importRequest)).rejects.toMatchObject({
      name: "ApiError",
      status: 502,
      code: null,
      message: "The backend returned HTTP 502.",
    });
  });

  it("replaces a network failure with a safe connection error", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn<typeof fetch>()
        .mockRejectedValue(new Error("raw request URL and transport details")),
    );

    let error: unknown;
    try {
      await importYouTubeVideo(importRequest);
    } catch (caughtError) {
      error = caughtError;
    }

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 0,
      code: null,
      message: "Unable to connect to the backend.",
    });
    expect(String(error)).not.toContain("raw request URL");
  });

  it("replaces an invalid success payload with a safe API error", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn<typeof fetch>()
        .mockResolvedValue(new Response("not JSON", { status: 201 })),
    );

    await expect(importYouTubeVideo(importRequest)).rejects.toMatchObject({
      name: "ApiError",
      status: 201,
      code: null,
      message: "The backend returned an invalid response.",
    });
  });
});
