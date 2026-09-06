import { describe, expect, it } from "vitest";

import { localDateTimeToIso } from "../lib/datetime";

describe("localDateTimeToIso", () => {
  it("converts a local wall-clock value to an unambiguous UTC instant", () => {
    const result = localDateTimeToIso("2026-09-05T09:30");
    const expectedLocalInstant = new Date(2026, 8, 5, 9, 30).toISOString();

    expect(result).toBe(expectedLocalInstant);
    expect(result).toMatch(/Z$/);
    expect(Number.isNaN(Date.parse(result))).toBe(false);
  });

  it("rejects an invalid local date and time", () => {
    expect(() => localDateTimeToIso("")).toThrow(
      "Published date and time must be valid.",
    );
  });
});
