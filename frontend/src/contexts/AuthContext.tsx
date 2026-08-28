/**
 * Backwards-compatible re-exports.
 *
 * The original AuthContext.tsx exported both a component (`AuthProvider`) and
 * a hook (`useAuth`). That combination triggers Vite's Fast Refresh warning
 * because hot-reload can't safely refresh a module that mixes the two. The
 * component now lives in `./AuthProvider` and the hook in `./useAuth`.
 *
 * Existing imports from "../contexts/AuthContext" keep working unchanged.
 */
export { AuthProvider } from "./AuthProvider";
export { AuthContext } from "./AuthProvider";
export { useAuth } from "./useAuth";
export type { AuthContextValue } from "./AuthProvider";
