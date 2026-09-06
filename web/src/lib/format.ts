export function formatInteger(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

export function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatPercentage(value: number | null): string {
  return value === null
    ? "Not available"
    : new Intl.NumberFormat("en-US", {
        style: "percent",
        maximumFractionDigits: 1,
      }).format(value);
}

export function formatLift(value: number | null): string {
  return value === null ? "Not available" : `${value.toFixed(1)}×`;
}

export function formatDisplayValue(value: string): string {
  const label = value.replaceAll("_", " ");
  return label.charAt(0).toUpperCase() + label.slice(1);
}

export function formatDisplayText(value: string): string {
  return value.replaceAll(
    /\b[a-z0-9]+(?:_[a-z0-9]+)+\b/g,
    (token) => token.replaceAll("_", " "),
  );
}
