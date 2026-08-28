import { FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AuthPage } from "./Login";
import { confirmPasswordReset } from "../api/auth";

export function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      await confirmPasswordReset(token, password);
      setSuccess(true);
      // Redirect after a brief delay so the user can read the success message
      setTimeout(() => navigate("/login"), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reset password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthPage
      eyebrow="Set new password"
      title="Choose a new password"
      subtitle="Enter your new password below to finish resetting your account."
    >
      {success ? (
        <div className="flex flex-col gap-4">
          <div className="bg-teal-50 border border-teal-200 text-teal-800 rounded-lg p-4 text-sm">
            <p className="font-semibold mb-1">Password updated</p>
            <p>Your password has been reset successfully. Redirecting you to sign in…</p>
          </div>
          <Link
            to="/login"
            className="w-full text-center bg-teal-600 hover:bg-teal-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors duration-200"
          >
            Back to sign in
          </Link>
        </div>
      ) : !token ? (
        <div className="flex flex-col gap-4">
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 text-sm">
            <p className="font-semibold mb-1">Invalid or missing reset token</p>
            <p>The link you followed is invalid or has expired. Please request a new password reset link.</p>
          </div>
          <Link
            to="/forgot-password"
            className="w-full text-center bg-teal-600 hover:bg-teal-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors duration-200"
          >
            Request a new link
          </Link>
        </div>
      ) : (
        <form onSubmit={submit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="new-password" className="text-sm font-medium text-gray-700">
              New password
            </label>
            <input
              id="new-password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full px-3 py-3 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition"
              placeholder="••••••••"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="confirm-password" className="text-sm font-medium text-gray-700">
              Confirm new password
            </label>
            <input
              id="confirm-password"
              type="password"
              required
              minLength={8}
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
              className="w-full px-3 py-3 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition"
              placeholder="••••••••"
            />
          </div>

          {error && <p className="text-red-600 text-sm mt-1">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-teal-600 hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 px-4 rounded-lg transition-colors duration-200 mt-2"
          >
            {loading ? "Updating…" : "Update password"}
          </button>

          <p className="text-center text-sm text-gray-500 mt-2">
            Changed your mind?{" "}
            <Link to="/login" className="text-teal-600 hover:text-teal-700 hover:underline font-medium">
              Back to sign in
            </Link>
          </p>
        </form>
      )}
    </AuthPage>
  );
}
