// USE_STUBS renders pages against hardcoded sample data so the shell works without a live backend.
// Set to false (or via VITE_USE_STUBS=0) once the control plane is running and migrated.
export const USE_STUBS = (import.meta.env.VITE_USE_STUBS ?? "1") !== "0";

export const POLL_INTERVAL_MS = 5000; // dashboard/incident polling (ITER_01); SSE-driven in ITER_03.
