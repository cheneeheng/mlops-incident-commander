// USE_STUBS renders pages against hardcoded sample data so the shell works without a live backend.
// Defaults to false at MVP (real control plane); opt back into sample data with VITE_USE_STUBS=1.
export const USE_STUBS = (import.meta.env.VITE_USE_STUBS ?? "0") !== "0";

export const POLL_INTERVAL_MS = 5000; // dashboard/incident polling (ITER_01); SSE-driven in ITER_03.
