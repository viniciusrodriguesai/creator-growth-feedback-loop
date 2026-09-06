import { useState, type FormEvent } from "react";

import { ApiError, createPost } from "../api/client";
import type { PostCreate } from "../api/types";
import { localDateTimeToIso } from "../lib/datetime";

type PostField = keyof PostCreate;
type FieldErrors = Partial<Record<PostField, string>>;

const postFields = new Set<PostField>([
  "platform",
  "title",
  "hook_type",
  "format",
  "creator",
  "views",
  "likes",
  "comments",
  "shares",
  "duration_seconds",
  "published_at",
]);

interface AddContentFormProps {
  onCreated: () => Promise<void>;
}

function optionalNumber(value: FormDataEntryValue | null): number | null {
  const text = String(value ?? "").trim();
  return text === "" ? null : Number(text);
}

function errorsByField(error: ApiError): FieldErrors {
  const fieldErrors: FieldErrors = {};

  for (const issue of error.validationIssues) {
    const field = issue.loc.at(-1);
    if (typeof field === "string" && postFields.has(field as PostField)) {
      fieldErrors[field as PostField] = issue.msg;
    }
  }

  return fieldErrors;
}

function FieldError({ field, errors }: { field: PostField; errors: FieldErrors }) {
  const message = errors[field];
  return message ? (
    <span className="field-error" id={`${field}-error`}>
      {message}
    </span>
  ) : null;
}

export function AddContentForm({ onCreated }: AddContentFormProps) {
  const [submitting, setSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  function clearFieldError(field: string) {
    if (!postFields.has(field as PostField)) {
      return;
    }
    setFieldErrors((current) => {
      const next = { ...current };
      delete next[field as PostField];
      return next;
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setFieldErrors({});
    setFormError(null);
    setSuccessMessage(null);

    const form = event.currentTarget;
    const formData = new FormData(form);

    try {
      const payload: PostCreate = {
        platform: formData.get("platform") as PostCreate["platform"],
        title: String(formData.get("title") ?? ""),
        hook_type: String(formData.get("hook_type") ?? ""),
        format: String(formData.get("format") ?? ""),
        creator: String(formData.get("creator") ?? ""),
        views: Number(formData.get("views")),
        likes: Number(formData.get("likes")),
        comments: Number(formData.get("comments")),
        shares: optionalNumber(formData.get("shares")),
        duration_seconds: optionalNumber(formData.get("duration_seconds")),
        published_at: localDateTimeToIso(
          String(formData.get("published_at") ?? ""),
        ),
      };

      await createPost(payload);
      form.reset();
      setSuccessMessage("Content saved successfully.");
      await onCreated();
    } catch (error) {
      if (error instanceof ApiError) {
        const nextFieldErrors = errorsByField(error);
        setFieldErrors(nextFieldErrors);
        if (Object.keys(nextFieldErrors).length === 0) {
          setFormError(error.message);
        }
      } else if (error instanceof Error) {
        setFieldErrors({ published_at: error.message });
      } else {
        setFormError("Unable to save this content record.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="panel content-form-panel" aria-labelledby="add-content-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">New evidence</p>
          <h2 id="add-content-title">Add content</h2>
        </div>
        <p>Record one published piece and its observed performance.</p>
      </div>

      <form
        className="content-form"
        onSubmit={handleSubmit}
        onInput={(event) => clearFieldError((event.target as HTMLInputElement).name)}
      >
        <div className="form-field">
          <label htmlFor="platform">Platform</label>
          <select
            id="platform"
            name="platform"
            defaultValue="youtube"
            aria-invalid={Boolean(fieldErrors.platform)}
            aria-describedby={fieldErrors.platform ? "platform-error" : undefined}
          >
            <option value="youtube">YouTube</option>
            <option value="instagram">Instagram</option>
            <option value="tiktok">TikTok</option>
          </select>
          <FieldError field="platform" errors={fieldErrors} />
        </div>

        <div className="form-field form-field-wide">
          <label htmlFor="title">Title</label>
          <input
            id="title"
            name="title"
            required
            aria-invalid={Boolean(fieldErrors.title)}
            aria-describedby={fieldErrors.title ? "title-error" : undefined}
          />
          <FieldError field="title" errors={fieldErrors} />
        </div>

        <div className="form-field">
          <label htmlFor="hook_type">Hook type</label>
          <input
            id="hook_type"
            name="hook_type"
            required
            aria-invalid={Boolean(fieldErrors.hook_type)}
            aria-describedby={fieldErrors.hook_type ? "hook_type-error" : undefined}
          />
          <FieldError field="hook_type" errors={fieldErrors} />
        </div>

        <div className="form-field">
          <label htmlFor="format">Format</label>
          <input
            id="format"
            name="format"
            required
            aria-invalid={Boolean(fieldErrors.format)}
            aria-describedby={fieldErrors.format ? "format-error" : undefined}
          />
          <FieldError field="format" errors={fieldErrors} />
        </div>

        <div className="form-field">
          <label htmlFor="creator">Creator</label>
          <input
            id="creator"
            name="creator"
            required
            aria-invalid={Boolean(fieldErrors.creator)}
            aria-describedby={fieldErrors.creator ? "creator-error" : undefined}
          />
          <FieldError field="creator" errors={fieldErrors} />
        </div>

        {(["views", "likes", "comments"] as const).map((field) => (
          <div className="form-field" key={field}>
            <label htmlFor={field}>{field[0].toUpperCase() + field.slice(1)}</label>
            <input
              id={field}
              name={field}
              type="number"
              min="0"
              step="1"
              required
              inputMode="numeric"
              aria-invalid={Boolean(fieldErrors[field])}
              aria-describedby={fieldErrors[field] ? `${field}-error` : undefined}
            />
            <FieldError field={field} errors={fieldErrors} />
          </div>
        ))}

        <div className="form-field">
          <label htmlFor="shares">Shares <span>(optional)</span></label>
          <input
            id="shares"
            name="shares"
            type="number"
            min="0"
            step="1"
            inputMode="numeric"
            aria-invalid={Boolean(fieldErrors.shares)}
            aria-describedby={fieldErrors.shares ? "shares-error" : undefined}
          />
          <FieldError field="shares" errors={fieldErrors} />
        </div>

        <div className="form-field">
          <label htmlFor="duration_seconds">Duration in seconds <span>(optional)</span></label>
          <input
            id="duration_seconds"
            name="duration_seconds"
            type="number"
            min="0"
            step="1"
            inputMode="numeric"
            aria-invalid={Boolean(fieldErrors.duration_seconds)}
            aria-describedby={
              fieldErrors.duration_seconds ? "duration_seconds-error" : undefined
            }
          />
          <FieldError field="duration_seconds" errors={fieldErrors} />
        </div>

        <div className="form-field">
          <label htmlFor="published_at">Published date and time</label>
          <input
            id="published_at"
            name="published_at"
            type="datetime-local"
            required
            aria-invalid={Boolean(fieldErrors.published_at)}
            aria-describedby={
              fieldErrors.published_at ? "published_at-error" : "published-at-help"
            }
          />
          <span className="field-help" id="published-at-help">
            Uses your current local timezone.
          </span>
          <FieldError field="published_at" errors={fieldErrors} />
        </div>

        <div className="form-actions form-field-wide">
          <button type="submit" disabled={submitting} aria-busy={submitting}>
            {submitting ? "Saving content…" : "Save content"}
          </button>
          <div className="form-feedback" aria-live="polite" aria-atomic="true">
            {successMessage ? <p className="success-message">{successMessage}</p> : null}
            {Object.keys(fieldErrors).length > 0 ? (
              <p className="error-message">Review the highlighted fields.</p>
            ) : null}
            {formError ? <p className="error-message">{formError}</p> : null}
          </div>
        </div>
      </form>
    </section>
  );
}
