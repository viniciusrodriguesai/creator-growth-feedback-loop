export function localDateTimeToIso(localDateTime: string): string {
  const instant = new Date(localDateTime);

  if (!localDateTime || Number.isNaN(instant.getTime())) {
    throw new Error("Published date and time must be valid.");
  }

  return instant.toISOString();
}
