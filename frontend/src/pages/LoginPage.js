import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import {
  WifiHigh,
  Eye,
  EyeSlash,
} from "@phosphor-icons/react";

function formatError(detail) {
  if (!detail) return "Login failed. Try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((e) => e?.msg || JSON.stringify(e)).join(" ");
  return String(detail);
}

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(formatError(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left: Form */}
      <div className="w-full lg:w-1/2 flex flex-col justify-center px-8 md:px-16 lg:px-20 py-12 bg-white">
        <div className="max-w-sm w-full mx-auto">
          {/* Logo */}
          <div className="flex items-center gap-3 mb-10">
            <div className="w-10 h-10 bg-[#002FA7] flex items-center justify-center">
              <WifiHigh size={22} color="white" weight="bold" />
            </div>
            <div>
              <p className="text-lg font-black text-[#0A0B0D] font-heading leading-none">ACS Server</p>
              <p className="text-[10px] text-gray-400 uppercase tracking-[0.2em] font-semibold">India Platform</p>
            </div>
          </div>

          <h1 className="text-4xl font-black text-[#0A0B0D] font-heading mb-2 leading-tight tracking-tight">
            Sign In
          </h1>
          <p className="text-sm text-gray-500 mb-8 font-body">
            Access your ACS management console
          </p>

          {error && (
            <div
              className="mb-5 p-3 border border-[#E52B20] bg-red-50 text-[#E52B20] text-sm font-medium"
              data-testid="login-error"
            >
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs uppercase tracking-[0.15em] font-semibold text-gray-500 mb-1.5 font-body">
                Email Address
              </label>
              <input
                type="email"
                className="w-full border border-[#E6E8EB] px-3 py-2.5 text-sm focus:outline-none focus:border-[#002FA7] focus:ring-1 focus:ring-[#002FA7] transition-colors font-body"
                placeholder="admin@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                data-testid="login-email-input"
              />
            </div>

            <div>
              <label className="block text-xs uppercase tracking-[0.15em] font-semibold text-gray-500 mb-1.5 font-body">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  className="w-full border border-[#E6E8EB] px-3 py-2.5 text-sm pr-10 focus:outline-none focus:border-[#002FA7] focus:ring-1 focus:ring-[#002FA7] transition-colors font-body"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  data-testid="login-password-input"
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeSlash size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#002FA7] text-white py-2.5 text-sm font-semibold uppercase tracking-widest hover:bg-[#0035C4] disabled:opacity-60 transition-colors duration-150 mt-2 font-body"
              data-testid="login-submit-button"
            >
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>

          <p className="text-xs text-gray-400 mt-8 font-body">
            ACS Management Platform supporting TR-069 & TR-369 protocols.
            <br />
            Authorized access only.
          </p>
        </div>
      </div>

      {/* Right: Hero Image */}
      <div
        className="hidden lg:flex lg:w-1/2 relative overflow-hidden"
        style={{
          backgroundImage: `url('https://images.pexels.com/photos/32698507/pexels-photo-32698507.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940')`,
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      >
        <div className="absolute inset-0 bg-[#002FA7] opacity-80"></div>
        <div className="relative z-10 flex flex-col justify-end p-12 text-white">
          <h2 className="text-4xl font-black font-heading leading-tight mb-4">
            Manage All Indian<br />Router Networks
          </h2>
          <p className="text-sm opacity-80 font-body max-w-xs leading-relaxed">
            Centralized ACS platform supporting BSNL, Airtel, Jio, ACT and all generic TR-069/TR-369 compatible CPE devices.
          </p>
          <div className="flex gap-4 mt-8">
            <div className="border border-white/30 px-4 py-2">
              <p className="text-xs opacity-70 uppercase tracking-wider">Protocol</p>
              <p className="text-sm font-bold font-mono">TR-069 + TR-369</p>
            </div>
            <div className="border border-white/30 px-4 py-2">
              <p className="text-xs opacity-70 uppercase tracking-wider">Roles</p>
              <p className="text-sm font-bold font-mono">Admin / Op / Staff</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
