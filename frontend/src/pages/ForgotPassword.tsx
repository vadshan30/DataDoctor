import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { AuthPage } from "./Login";
import { requestPasswordReset } from "../api/auth";

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setSuccess(false);
    setLoading(true);
    try {
      await requestPasswordReset(email);
      setSuccess(true);
    } catch (err) {
      // Keep the original error available in DevTools when fetch fails before receiving a response.
      console.error("[DataDoctor] Password reset request failed", err);
      setError(err instanceof Error ? err.message : "Unable to process request. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthPage
      eyebrow="Reset password"
      title="Forgot your password?"
      subtitle="Enter your email and we'll send you a link to reset your password."
    >
      {success ? (
        <div className="flex flex-col gap-4">
          <div className="bg-teal-50 border border-teal-200 text-teal-800 rounded-lg p-4 text-sm">
            <p className="font-semibold mb-1">Check your inbox</p>
            <p>Password reset link sent to your email. Follow the instructions in the email to choose a new password.</p>
          </div>
          <Link
            to="/login"
            className="w-full text-center bg-teal-600 hover:bg-teal-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors duration-200"
          >
            Back to sign in
          </Link>
        </div>
      ) : (
        <form onSubmit={submit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="reset-email" className="text-sm font-medium text-gray-700">
              Email
            </label>
            <input
              id="reset-email"
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full px-3 py-3 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition"
              placeholder="you@example.com"
            />
          </div>

          {error && <p className="text-red-600 text-sm mt-1">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-teal-600 hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 px-4 rounded-lg transition-colors duration-200 mt-2"
          >
            {loading ? "Sending…" : "Send Reset Link"}
          </button>

          <p className="text-center text-sm text-gray-500 mt-2">
            Remembered your password?{" "}
            <Link to="/login" className="text-teal-600 hover:text-teal-700 hover:underline font-medium">
              Back to sign in
            </Link>
          </p>
        </form>
      )}
    </AuthPage>
  );
}
