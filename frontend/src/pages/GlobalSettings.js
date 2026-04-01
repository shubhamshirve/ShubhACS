import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  GearSix,
  Robot,
  WifiHigh,
  ShieldCheck,
  FloppyDisk,
  Eye,
  EyeSlash,
  Info,
} from "@phosphor-icons/react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TABS = [
  { id: "ai", label: "AI Settings", icon: Robot },
  { id: "acs", label: "ACS / Protocol", icon: WifiHigh },
  { id: "features", label: "Feature Toggles", icon: ShieldCheck },
];

export default function GlobalSettings() {
  const [settings, setSettings] = useState(null);
  const [activeTab, setActiveTab] = useState("ai");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [showKey, setShowKey] = useState(false);

  useEffect(() => {
    axios.get(`${API}/settings`, { withCredentials: true })
      .then((r) => setSettings({ ...r.data, gemini_api_key: r.data.gemini_api_key || "" }))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      const payload = { ...settings };
      delete payload.gemini_api_key_masked;
      delete payload.updated_at;
      delete payload.updated_by;
      await axios.put(`${API}/settings`, payload, { withCredentials: true });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) { alert(e.response?.data?.detail || "Save failed"); }
    setSaving(false);
  };

  const set = (k, v) => setSettings((s) => ({ ...s, [k]: v }));

  const inp = "w-full border border-[#E6E8EB] px-3 py-2 text-sm focus:outline-none focus:border-[#002FA7] focus:ring-1 focus:ring-[#002FA7] font-mono";
  const lbl = "block text-xs uppercase tracking-[0.12em] font-semibold text-gray-500 mb-1.5 font-body";

  const Toggle = ({ field, label, desc }) => (
    <div className="flex items-center justify-between py-4 border-b border-[#E6E8EB]" data-testid={`toggle-${field}`}>
      <div className="flex-1">
        <p className="text-sm font-semibold text-[#0A0B0D] font-heading">{label}</p>
        <p className="text-xs text-gray-500 font-body mt-0.5">{desc}</p>
      </div>
      <button
        className={`w-12 h-6 border-2 flex items-center transition-colors duration-200 ${settings?.[field] ? "bg-[#002FA7] border-[#002FA7] justify-end" : "bg-gray-100 border-gray-300 justify-start"}`}
        onClick={() => set(field, !settings?.[field])}
        data-testid={`toggle-btn-${field}`}
      >
        <div className="w-4 h-4 bg-white m-0.5 shadow-sm"></div>
      </button>
    </div>
  );

  if (loading) return <div className="p-12 flex justify-center"><div className="w-8 h-8 border-2 border-[#002FA7] border-t-transparent rounded-full animate-spin"></div></div>;

  return (
    <div className="fade-in">
      <div className="px-6 md:px-8 py-6 border-b border-[#E6E8EB] flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] font-semibold text-gray-400 mb-0.5 font-body">Platform Configuration</p>
          <h1 className="text-2xl font-black text-[#0A0B0D] font-heading">Global Settings</h1>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className={`flex items-center gap-2 px-5 py-2.5 text-sm font-semibold transition-colors font-body ${saved ? "bg-[#00A153] text-white" : "bg-[#002FA7] text-white hover:bg-[#0035C4]"} disabled:opacity-60`}
          data-testid="save-settings-button"
        >
          <FloppyDisk size={15} />
          {saving ? "Saving..." : saved ? "Saved!" : "Save Changes"}
        </button>
      </div>

      <div className="border-b border-[#E6E8EB] px-6 md:px-8 flex">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button key={id} className={`flex items-center gap-1.5 px-4 py-3 text-xs font-semibold uppercase tracking-wider border-b-2 transition-colors font-body ${activeTab === id ? "border-[#002FA7] text-[#002FA7]" : "border-transparent text-gray-500 hover:text-gray-800"}`}
            onClick={() => setActiveTab(id)} data-testid={`settings-tab-${id}`}>
            <Icon size={14} />{label}
          </button>
        ))}
      </div>

      <div className="p-6 md:p-8 max-w-2xl">
        {/* AI SETTINGS */}
        {activeTab === "ai" && (
          <div data-testid="ai-settings-panel">
            <Toggle field="ai_enabled" label="AI Diagnostics" desc="Enable AI-powered diagnostics and fault analysis using Gemini 3 Flash" />
            <div className="pt-5">
              <div className="p-4 bg-blue-50 border border-blue-200 flex gap-3 mb-5">
                <Info size={16} className="text-[#002FA7] flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-semibold text-[#002FA7] font-body">Gemini API Key Configuration</p>
                  <p className="text-xs text-gray-600 font-body mt-1">Leave empty to use the platform's shared Emergent Universal Key (recommended). Enter your own Gemini API key for dedicated usage.</p>
                </div>
              </div>
              <label className={lbl}>Gemini API Key (Optional)</label>
              <div className="relative">
                <input
                  className={inp}
                  type={showKey ? "text" : "password"}
                  placeholder="Leave empty to use Universal Key (AIzaSy...)"
                  value={settings?.gemini_api_key || ""}
                  onChange={(e) => set("gemini_api_key", e.target.value)}
                  data-testid="gemini-api-key-input"
                />
                <button type="button" className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  onClick={() => setShowKey(!showKey)}>
                  {showKey ? <EyeSlash size={15} /> : <Eye size={15} />}
                </button>
              </div>
              {settings?.gemini_api_key_masked && (
                <p className="text-xs text-gray-400 mt-1 font-mono">Current key: {settings.gemini_api_key_masked}</p>
              )}
            </div>
          </div>
        )}

        {/* ACS/PROTOCOL */}
        {activeTab === "acs" && (
          <div data-testid="acs-settings-panel" className="space-y-4">
            <Toggle field="tr069_enabled" label="TR-069 (CWMP)" desc="Accept TR-069 Inform messages from CPE devices at /api/acs/cwmp" />
            <Toggle field="tr369_enabled" label="TR-369 (USP)" desc="Accept TR-369 USP device registrations at /api/acs/usp/register" />
            <div className="pt-2">
              <label className={lbl}>ACS Server URL (for CPE provisioning)</label>
              <input className={inp} value={settings?.acs_url || ""} onChange={(e) => set("acs_url", e.target.value)} data-testid="acs-url-input" />
              <p className="text-xs text-gray-400 mt-1 font-body">Configure this URL in your CPE devices as the ACS server address</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={lbl}>CWMP Username</label>
                <input className={inp} value={settings?.cwmp_username || ""} onChange={(e) => set("cwmp_username", e.target.value)} data-testid="cwmp-username-input" />
              </div>
              <div>
                <label className={lbl}>CWMP Password</label>
                <input className={inp} type="password" value={settings?.cwmp_password || ""} onChange={(e) => set("cwmp_password", e.target.value)} />
              </div>
            </div>
            <div>
              <label className={lbl}>Inform Interval (seconds)</label>
              <input className={inp} type="number" min={60} max={3600} value={settings?.inform_interval || 300} onChange={(e) => set("inform_interval", parseInt(e.target.value))} data-testid="inform-interval-input" />
              <p className="text-xs text-gray-400 mt-1 font-body">How often CPE devices should send periodic Inform messages (default: 300s)</p>
            </div>
            <div className="mt-4 p-4 border border-[#E6E8EB] bg-[#FAFBFC]">
              <p className="text-xs font-semibold text-gray-600 mb-2 font-body">TR-069 CPE Configuration Template:</p>
              <div className="terminal-output text-[11px]">{`[TR-069 ACS Settings]
ACS URL: ${settings?.acs_url || "<YOUR_SERVER>/api/acs/cwmp"}
Username: ${settings?.cwmp_username || "acs"}
Password: ${settings?.cwmp_password ? "****" : "acs123"}
Periodic Inform: Enable
Inform Interval: ${settings?.inform_interval || 300}s`}</div>
            </div>
          </div>
        )}

        {/* FEATURE TOGGLES */}
        {activeTab === "features" && (
          <div data-testid="feature-settings-panel">
            <Toggle field="diagnostics_enabled" label="Diagnostics (Ping & Traceroute)" desc="Allow ping and traceroute tests from the device detail page" />
            <Toggle field="speed_test_enabled" label="Speed Test" desc="Allow speed test measurements from device detail page" />
          </div>
        )}
      </div>
    </div>
  );
}
