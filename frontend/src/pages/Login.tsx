import { FormEvent, useState, type ReactNode } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export function Login() {
  const { session, signIn, signInAsGuest, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  if (session) return <Navigate to="/dashboard" replace />;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    try {
      await signIn(email, password);
      navigate((location.state as { from?: string })?.from || "/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in.");
    }
  };

  return (
    <AuthPage
      eyebrow="Welcome back"
      title="Your data, in focus."
      subtitle="Sign in to continue working with your datasets."
    >
      <form onSubmit={submit} className="flex flex-col gap-4">
        <Field label="Email" type="email" value={email} onChange={setEmail} required />
        <Field label="Password" type="password" value={password} onChange={setPassword} required />

        <div className="flex justify-end -mt-2">
          <Link
            to="/forgot-password"
            className="text-sm text-gray-500 hover:text-teal-700 hover:underline transition-colors"
          >
            Forgot password?
          </Link>
        </div>

        {error && (
          <p className="text-red-600 text-sm mt-1">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-teal-600 hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 px-4 rounded-lg transition-colors duration-200 mt-2"
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>

        <button
          type="button"
          onClick={async () => {
            setError("");
            try {
              await signInAsGuest();
              navigate((location.state as { from?: string })?.from || "/dashboard");
            } catch (err) {
              setError(err instanceof Error ? err.message : "Unable to sign in as guest.");
            }
          }}
          disabled={loading}
          className="w-full border border-gray-300 hover:border-gray-400 disabled:opacity-50 disabled:cursor-not-allowed text-gray-700 font-medium py-3 px-4 rounded-lg transition-colors duration-200 mt-2 flex items-center justify-center gap-2"
        >
          {loading ? "Logging in as guest…" : "Try as Guest"}
        </button>

        <p className="text-center text-sm text-gray-500 mt-2">
          New to DataDoctor?{" "}
          <Link to="/register" className="text-teal-600 hover:text-teal-700 hover:underline font-medium">
            Create an account
          </Link>
        </p>
      </form>
    </AuthPage>
  );
}

function Field({
  label,
  type,
  value,
  onChange,
  required,
}: {
  label: string;
  type: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-gray-700">{label}</label>
      <input
        type={type}
        value={value}
        required={required}
        onChange={(event) => onChange(event.target.value)}
        className="w-full px-3 py-3 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition"
        placeholder={type === "email" ? "you@example.com" : "••••••••"}
      />
    </div>
  );
}

export function AuthPage({
  eyebrow,
  title,
  subtitle,
  children,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen flex">
      {/* Left panel — branding */}
      <div className="hidden lg:flex flex-col justify-between w-1/2 bg-gradient-to-br from-teal-700 to-teal-900 p-12 text-white">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center font-bold text-xl">
            D
          </div>
          <span className="font-bold text-xl tracking-tight">DataDoctor</span>
        </div>

        <div>
          <p className="text-teal-300 font-semibold uppercase tracking-widest text-xs mb-4">
            DataDoctor platform
          </p>
          <h1 className="text-4xl font-bold leading-tight mb-4">
            Turn raw data into a clear next step.
          </h1>
          <p className="text-teal-200 text-lg leading-relaxed">
            Profile, clean, engineer, and prepare your data for decisions.
          </p>
        </div>

        <p className="text-teal-400 text-sm">© 2024 DataDoctor. All rights reserved.</p>
      </div>

      {/* Right panel — form */}
      <div className="flex flex-1 items-center justify-center bg-gray-50 p-6">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="flex items-center gap-2 mb-8 lg:hidden">
            <div className="w-9 h-9 rounded-xl bg-teal-600 flex items-center justify-center font-bold text-white text-lg">
              D
            </div>
            <span className="font-bold text-xl text-gray-900">DataDoctor</span>
          </div>

          <div className="bg-white rounded-2xl shadow-lg p-8">
            <p className="text-teal-600 font-semibold text-sm uppercase tracking-widest mb-2">
              {eyebrow}
            </p>
            <h2 className="text-2xl font-bold text-gray-900 mb-1">{title}</h2>
            <p className="text-gray-500 text-sm mb-8">{subtitle}</p>

            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
