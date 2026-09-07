import { useEffect, useRef, useState, type FormEvent } from "react";

import { ApiError, importYouTubeVideo } from "../api/client";
import type { YouTubeImportRequest } from "../api/types";

const hookTypeOptions = [
  { value: "pain_point", label: "Pain point" },
  { value: "product_led", label: "Product-led" },
  { value: "question", label: "Question" },
  { value: "story", label: "Story" },
] as const;

const formatOptions = [
  { value: "short", label: "Short" },
  { value: "long", label: "Long" },
] as const;

const errorMessages: Record<string, string> = {
  youtube_video_already_imported:
    "This YouTube video is already in your content library.",
  youtube_not_configured:
    "YouTube importing is not available right now. Please try again later.",
  youtube_video_not_found:
    "We couldn't find a public YouTube video at that URL.",
  youtube_metrics_unavailable:
    "This video's public performance metrics are unavailable, so it can't be imported.",
  youtube_quota_exceeded:
    "YouTube importing is temporarily unavailable. Please try again later.",
  youtube_timeout: "YouTube took too long to respond. Please try again.",
  youtube_access_denied:
    "YouTube wouldn't allow access to this video's public details.",
  youtube_invalid_response:
    "YouTube returned an unexpected response. Please try again later.",
  youtube_upstream_unavailable:
    "YouTube is temporarily unavailable. Please try again later.",
  invalid_youtube_url: "Paste a supported public YouTube video URL.",
};

const genericErrorMessage = "We couldn't import this video. Please try again.";

function importErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.code) {
    return errorMessages[error.code] ?? genericErrorMessage;
  }

  return genericErrorMessage;
}

export function YouTubeImportForm() {
  const [url, setUrl] = useState("");
  const [hookType, setHookType] = useState("pain_point");
  const [format, setFormat] = useState("short");
  const [submitting, setSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const submittingRef = useRef(false);
  const urlInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (successMessage && !submitting) {
      urlInputRef.current?.focus();
    }
  }, [submitting, successMessage]);

  function clearFeedback() {
    setSuccessMessage(null);
    setErrorMessage(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submittingRef.current) {
      return;
    }

    submittingRef.current = true;
    setSubmitting(true);
    clearFeedback();

    const payload: YouTubeImportRequest = {
      url: url.trim(),
      hook_type: hookType,
      format,
    };

    try {
      const importedPost = await importYouTubeVideo(payload);
      setUrl("");
      setSuccessMessage(`Imported "${importedPost.title}" from YouTube.`);
    } catch (error) {
      setErrorMessage(importErrorMessage(error));
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  }

  return (
    <section
      className="panel youtube-import-panel"
      aria-labelledby="youtube-import-title"
    >
      <div className="section-heading youtube-import-heading">
        <div>
          <p className="eyebrow">YouTube import</p>
          <h2 id="youtube-import-title">Import a video</h2>
        </div>
        <p>Paste a YouTube video, classify it, and import its public metrics.</p>
      </div>

      <form
        className="youtube-import-form"
        onSubmit={handleSubmit}
        aria-labelledby="youtube-import-title"
        aria-busy={submitting}
      >
        <div className="form-field youtube-url-field">
          <label htmlFor="youtube-url">YouTube URL</label>
          <input
            ref={urlInputRef}
            id="youtube-url"
            name="url"
            type="url"
            value={url}
            onChange={(event) => {
              setUrl(event.target.value);
              clearFeedback();
            }}
            placeholder="https://www.youtube.com/watch?v=..."
            autoComplete="off"
            required
            disabled={submitting}
          />
        </div>

        <div className="form-field">
          <label htmlFor="youtube-hook-type">Hook type</label>
          <select
            id="youtube-hook-type"
            name="hook_type"
            value={hookType}
            onChange={(event) => {
              setHookType(event.target.value);
              clearFeedback();
            }}
            required
            disabled={submitting}
          >
            {hookTypeOptions.map((option) => (
              <option value={option.value} key={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="form-field">
          <label htmlFor="youtube-format">Format</label>
          <select
            id="youtube-format"
            name="format"
            value={format}
            onChange={(event) => {
              setFormat(event.target.value);
              clearFeedback();
            }}
            required
            disabled={submitting}
          >
            {formatOptions.map((option) => (
              <option value={option.value} key={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="youtube-import-action">
          <button type="submit" disabled={submitting} aria-busy={submitting}>
            {submitting ? "Importing..." : "Import video"}
          </button>
        </div>

        <div className="import-feedback" aria-live="polite" aria-atomic="true">
          {successMessage ? (
            <p className="success-message">{successMessage}</p>
          ) : null}
          {errorMessage ? (
            <p className="error-message" role="alert">
              {errorMessage}
            </p>
          ) : null}
        </div>
      </form>
    </section>
  );
}
