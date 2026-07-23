import type { ReactNode } from "react";

// Shared loading/error/empty wrapper for TanStack Query results.
export default function QueryBoundary({
  isLoading,
  isError,
  error,
  isEmpty,
  emptyLabel = "Nothing here yet.",
  children,
}: {
  isLoading: boolean;
  isError: boolean;
  error?: unknown;
  isEmpty?: boolean;
  emptyLabel?: string;
  children: ReactNode;
}) {
  if (isLoading) return <div className="state">Loading…</div>;
  if (isError) {
    const message = error instanceof Error ? error.message : "Request failed";
    return <div className="state">Error: {message}</div>;
  }
  if (isEmpty) return <div className="state">{emptyLabel}</div>;
  return <>{children}</>;
}
