import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import {
  ApiError,
  createPost,
  getAnalytics,
  getPosts,
  getRecommendation,
} from "../api/client";
import { localDateTimeToIso } from "../lib/datetime";
import {
  analytics,
  insufficientRecommendation,
  posts,
  recommendation,
} from "./fixtures";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    createPost: vi.fn(),
    getAnalytics: vi.fn(),
    getPosts: vi.fn(),
    getRecommendation: vi.fn(),
  };
});

const mockedCreatePost = vi.mocked(createPost);
const mockedGetAnalytics = vi.mocked(getAnalytics);
const mockedGetPosts = vi.mocked(getPosts);
const mockedGetRecommendation = vi.mocked(getRecommendation);

function mockPopulatedDashboard() {
  mockedGetPosts.mockResolvedValue(posts);
  mockedGetAnalytics.mockResolvedValue(analytics);
  mockedGetRecommendation.mockResolvedValue(recommendation);
}

async function fillRequiredForm(title = "Created content") {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Title"), title);
  await user.type(screen.getByLabelText("Hook type"), "pain_point");
  await user.type(screen.getByLabelText("Format"), "short");
  await user.type(screen.getByLabelText("Creator"), "Alex");
  await user.type(screen.getByLabelText("Views"), "1000");
  await user.type(screen.getByLabelText("Likes"), "120");
  await user.type(screen.getByLabelText("Comments"), "15");
  fireEvent.change(screen.getByLabelText("Published date and time"), {
    target: { value: "2026-09-05T09:30" },
  });
  return user;
}

describe("App", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mockPopulatedDashboard();
  });

  it("renders analytics summaries and grouped performance", async () => {
    render(<App />);

    const totalPostsCard = (await screen.findByText("Total posts")).parentElement;
    expect(totalPostsCard).not.toBeNull();
    expect(within(totalPostsCard!).getByText("2")).toBeInTheDocument();
    expect(screen.getByText("2,000")).toBeInTheDocument();
    expect(screen.getByText("14%")).toBeInTheDocument();

    const hookTable = screen.getByRole("table", {
      name: "Engagement performance grouped by hook type",
    });
    expect(within(hookTable).getByText("Pain point")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Format" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Creator" })).toBeInTheDocument();
  });

  it("renders the recommendation before supporting analytics", async () => {
    render(<App />);

    const recommendationHeading = await screen.findByRole("heading", {
      name: "Test pain-point hooks next",
    });
    const summaryHeading = screen.getByRole("heading", {
      name: "Performance snapshot",
    });

    expect(
      recommendationHeading.compareDocumentPosition(summaryHeading) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.getByText("18.5%")).toBeInTheDocument();
    expect(screen.getByText("8.3%")).toBeInTheDocument();
    expect(screen.getByText("+10.3%")).toBeInTheDocument();
    expect(screen.getByText("2.2×")).toBeInTheDocument();
    expect(
      screen.getByText(
        "The 'pain point' hook type was associated with higher observed core engagement than the rest of eligible posts.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("engagement vs other eligible posts"),
    ).toBeInTheDocument();
    expect(screen.getByText(/not causation/i)).toBeInTheDocument();
  });

  it("shows a deliberate insufficient-evidence state", async () => {
    mockedGetRecommendation.mockResolvedValue(insufficientRecommendation);

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "More comparable posts needed" }),
    ).toBeInTheDocument();
    expect(screen.getByText(insufficientRecommendation.evidence.summary)).toBeVisible();
    expect(screen.getByText(/Current evidence: 1 eligible posts/)).toBeVisible();
  });

  it("keeps posts and analytics visible when recommendations fail", async () => {
    mockedGetRecommendation.mockRejectedValue(
      new ApiError("The backend returned HTTP 500.", 500),
    );

    render(<App />);

    expect(await screen.findByText("Pain point opening")).toBeInTheDocument();
    expect(screen.getByText("Performance snapshot")).toBeInTheDocument();
    expect(
      screen.getByText(/The recommendation could not be refreshed/),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("The product data is unavailable"),
    ).not.toBeInTheDocument();
  });

  it("keeps posts and recommendations visible when analytics fail", async () => {
    mockedGetAnalytics.mockRejectedValue(
      new ApiError("The backend returned HTTP 500.", 500),
    );

    render(<App />);

    expect(await screen.findByText("Pain point opening")).toBeInTheDocument();
    expect(screen.getByText("Test pain-point hooks next")).toBeInTheDocument();
    expect(screen.getByText(/Analytics could not be refreshed/)).toBeInTheDocument();
    expect(
      screen.queryByText("The product data is unavailable"),
    ).not.toBeInTheDocument();
  });

  it("shows the deliberate no-posts state", async () => {
    mockedGetPosts.mockResolvedValue([]);
    mockedGetAnalytics.mockResolvedValue({
      ...analytics,
      overall: {
        ...analytics.overall,
        post_count: 0,
        eligible_post_count: 0,
        total_views: 0,
        known_core_engagements: 0,
        known_shares: null,
        eligible_posts_with_share_data: 0,
        eligible_posts_without_share_data: 0,
        engagement_rate: null,
      },
      by_hook_type: [],
      by_format: [],
      by_creator: [],
    });
    mockedGetRecommendation.mockResolvedValue(insufficientRecommendation);

    render(<App />);

    expect(await screen.findByRole("heading", { name: "No content yet" })).toBeVisible();
    expect(screen.getByText(/Add the first performance record/)).toBeVisible();
  });

  it("uses natural copy for format recommendations", async () => {
    mockedGetRecommendation.mockResolvedValue({
      ...recommendation,
      dimension: "format",
      value: "short_form",
    });

    render(<App />);

    expect(
      await screen.findByRole("heading", {
        name: "Test short-form format next",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Short form")).toBeInTheDocument();
  });

  it("shows a global error only when all dashboard resources fail", async () => {
    const connectionError = new ApiError("Unable to connect to the backend.", 0);
    mockedGetPosts.mockRejectedValue(connectionError);
    mockedGetAnalytics.mockRejectedValue(connectionError);
    mockedGetRecommendation.mockRejectedValue(connectionError);

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "The product data is unavailable" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry connection" })).toBeEnabled();
  });

  it("posts a timezone-aware instant and refreshes every resource", async () => {
    const createdPost = {
      ...posts[0],
      id: 3,
      title: "Created content",
      views: 1000,
      likes: 120,
      comments: 15,
      published_at: localDateTimeToIso("2026-09-05T09:30"),
    };
    mockedCreatePost.mockResolvedValue(createdPost);
    mockedGetPosts
      .mockResolvedValueOnce(posts)
      .mockResolvedValue([...posts, createdPost]);

    render(<App />);
    await screen.findByText("Pain point opening");
    const user = await fillRequiredForm();
    await user.click(screen.getByRole("button", { name: "Save content" }));

    expect(await screen.findByText("Content saved successfully.")).toBeInTheDocument();
    expect(await screen.findByText("Created content")).toBeInTheDocument();
    expect(mockedCreatePost).toHaveBeenCalledWith({
      platform: "youtube",
      title: "Created content",
      hook_type: "pain_point",
      format: "short",
      creator: "Alex",
      views: 1000,
      likes: 120,
      comments: 15,
      shares: null,
      duration_seconds: null,
      published_at: localDateTimeToIso("2026-09-05T09:30"),
    });
    expect(mockedGetPosts).toHaveBeenCalledTimes(2);
    expect(mockedGetAnalytics).toHaveBeenCalledTimes(2);
    expect(mockedGetRecommendation).toHaveBeenCalledTimes(2);
  });

  it("associates backend validation errors with their fields", async () => {
    mockedCreatePost.mockRejectedValue(
      new ApiError("The backend returned HTTP 422.", 422, [
        {
          type: "greater_than_equal",
          loc: ["body", "views"],
          msg: "Input should be greater than or equal to 0",
        },
      ]),
    );

    render(<App />);
    await screen.findByText("Pain point opening");
    const user = await fillRequiredForm();
    await user.click(screen.getByRole("button", { name: "Save content" }));

    const viewsInput = screen.getByLabelText("Views");
    const message = await screen.findByText(
      "Input should be greater than or equal to 0",
    );
    expect(viewsInput).toHaveAttribute("aria-invalid", "true");
    expect(viewsInput).toHaveAttribute("aria-describedby", "views-error");
    expect(message).toHaveAttribute("id", "views-error");
    expect(screen.getByText("Review the highlighted fields.")).toBeInTheDocument();
  });

  it("communicates the submitting state without removing the control label", async () => {
    let resolveCreate: ((value: typeof posts[0]) => void) | undefined;
    mockedCreatePost.mockReturnValue(
      new Promise((resolve) => {
        resolveCreate = resolve;
      }),
    );

    render(<App />);
    await screen.findByText("Pain point opening");
    const user = await fillRequiredForm();
    await user.click(screen.getByRole("button", { name: "Save content" }));

    const savingButton = screen.getByRole("button", { name: "Saving content…" });
    expect(savingButton).toBeDisabled();
    expect(savingButton).toHaveAttribute("aria-busy", "true");

    resolveCreate?.(posts[0]);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Save content" })).toBeEnabled();
    });
  });
});
