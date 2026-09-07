import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, importYouTubeVideo } from "../api/client";
import type { Post } from "../api/types";
import { YouTubeImportForm } from "./YouTubeImportForm";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    importYouTubeVideo: vi.fn(),
  };
});

const mockedImportYouTubeVideo = vi.mocked(importYouTubeVideo);
const onImported = vi.fn<() => Promise<void>>();

const importedPost: Post = {
  id: 7,
  platform: "youtube",
  title: "A useful creator experiment",
  hook_type: "question",
  format: "long",
  creator: "Creator Channel",
  views: 12_000,
  likes: 850,
  comments: 42,
  shares: null,
  duration_seconds: 73,
  published_at: "2026-08-20T14:30:00Z",
};

async function fillImportForm() {
  const user = userEvent.setup();
  await user.type(
    screen.getByRole("textbox", { name: "YouTube URL" }),
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  );
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Hook type" }),
    "question",
  );
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Format" }),
    "long",
  );
  return user;
}

describe("YouTubeImportForm", () => {
  beforeEach(() => {
    mockedImportYouTubeVideo.mockReset();
    onImported.mockReset();
    onImported.mockResolvedValue(undefined);
    render(<YouTubeImportForm onImported={onImported} />);
  });

  it("renders accessible URL, hook type, format, and submit controls", () => {
    expect(screen.getByLabelText("YouTube URL")).toHaveAttribute("type", "url");
    expect(screen.getByLabelText("Hook type")).toHaveValue("pain_point");
    expect(screen.getByLabelText("Format")).toHaveValue("short");
    expect(screen.getByRole("button", { name: "Import video" })).toBeEnabled();
  });

  it("submits the selected values exactly once with the keyboard", async () => {
    mockedImportYouTubeVideo.mockResolvedValue(importedPost);
    const user = await fillImportForm();

    await user.click(screen.getByRole("textbox", { name: "YouTube URL" }));
    await user.keyboard("{Enter}");

    await waitFor(() => expect(mockedImportYouTubeVideo).toHaveBeenCalledOnce());
    expect(mockedImportYouTubeVideo).toHaveBeenCalledWith({
      url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      hook_type: "question",
      format: "long",
    });
    expect(onImported).toHaveBeenCalledOnce();
  });

  it("disables the form and communicates while the import is pending", async () => {
    let resolveImport: ((post: Post) => void) | undefined;
    mockedImportYouTubeVideo.mockReturnValue(
      new Promise((resolve) => {
        resolveImport = resolve;
      }),
    );
    const user = await fillImportForm();

    await user.click(screen.getByRole("button", { name: "Import video" }));

    const form = screen.getByRole("form", { name: "Import a video" });
    const button = screen.getByRole("button", { name: "Importing..." });
    expect(form).toHaveAttribute("aria-busy", "true");
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(screen.getByLabelText("YouTube URL")).toBeDisabled();
    expect(screen.getByLabelText("Hook type")).toBeDisabled();
    expect(screen.getByLabelText("Format")).toBeDisabled();

    resolveImport?.(importedPost);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Import video" })).toBeEnabled();
    });
  });

  it("shows the imported video, clears the URL, and preserves classification", async () => {
    mockedImportYouTubeVideo.mockResolvedValue(importedPost);
    const user = await fillImportForm();

    await user.click(screen.getByRole("button", { name: "Import video" }));

    expect(
      await screen.findByText(
        'Imported "A useful creator experiment" from YouTube.',
      ),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("YouTube URL")).toHaveValue("");
    expect(screen.getByLabelText("YouTube URL")).toHaveFocus();
    expect(screen.getByLabelText("Hook type")).toHaveValue("question");
    expect(screen.getByLabelText("Format")).toHaveValue("long");
  });

  it("explains a structured duplicate error", async () => {
    mockedImportYouTubeVideo.mockRejectedValue(
      new ApiError(
        "Internal duplicate details",
        409,
        [],
        "youtube_video_already_imported",
      ),
    );
    const user = await fillImportForm();

    await user.click(screen.getByRole("button", { name: "Import video" }));

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent("This YouTube video is already in your content library.");
    expect(screen.getByRole("alert")).not.toHaveTextContent(
      "Internal duplicate details",
    );
    expect(onImported).not.toHaveBeenCalled();
  });

  it("explains another structured YouTube backend error", async () => {
    mockedImportYouTubeVideo.mockRejectedValue(
      new ApiError(
        "Raw quota response",
        503,
        [],
        "youtube_quota_exceeded",
      ),
    );
    const user = await fillImportForm();

    await user.click(screen.getByRole("button", { name: "Import video" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "YouTube importing is temporarily unavailable. Please try again later.",
    );
    expect(screen.getByRole("alert")).not.toHaveTextContent("Raw quota response");
    expect(onImported).not.toHaveBeenCalled();
  });

  it("uses a safe message for an unknown error", async () => {
    mockedImportYouTubeVideo.mockRejectedValue(
      new Error("POST /imports/youtube failed with raw transport details"),
    );
    const user = await fillImportForm();

    await user.click(screen.getByRole("button", { name: "Import video" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "We couldn't import this video. Please try again.",
    );
    expect(screen.getByRole("alert")).not.toHaveTextContent("POST /imports");
    expect(onImported).not.toHaveBeenCalled();
  });

  it("keeps import success when the dashboard callback fails", async () => {
    mockedImportYouTubeVideo.mockResolvedValue(importedPost);
    onImported.mockRejectedValue(new Error("raw refresh failure"));
    const user = await fillImportForm();

    await user.click(screen.getByRole("button", { name: "Import video" }));

    expect(
      await screen.findByText(
        'Imported "A useful creator experiment" from YouTube.',
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "The video was imported, but the dashboard could not be refreshed.",
    );
    expect(screen.getByRole("alert")).not.toHaveTextContent("raw refresh failure");
  });

  it("does not submit twice while the first request is pending", async () => {
    mockedImportYouTubeVideo.mockReturnValue(new Promise(() => undefined));
    await fillImportForm();
    const form = screen.getByRole("form", { name: "Import a video" });

    fireEvent.submit(form);
    fireEvent.submit(form);

    expect(mockedImportYouTubeVideo).toHaveBeenCalledOnce();
    expect(screen.getByRole("button", { name: "Importing..." })).toBeDisabled();
  });
});
