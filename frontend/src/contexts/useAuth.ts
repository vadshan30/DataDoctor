import { useContext } from "react";
import { AuthContext } from "./AuthProvider";

/**
 * Hook to access the authentication context.
 * Must be used inside an <AuthProvider> tree.
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { session, signOut } = useAuth();
 *   // ...
 * }
 * ```
 */
export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
