import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import axios from "axios";
import {
  ArrowLeft,
  WifiHigh,
  Globe,
  Network,
  ChartBar,
  Speedometer,
  Robot,
  FloppyDisk,
  Play,
  ClockCountdown,
  Waveform,
} from "@phosphor-icons/react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const StatusBadge = ({ status }) => {
  const cfg = {
    online: { bg: "bg-[#D1FAE5]", text: "text-[#065F46]", border: "border-[#6EE7B7]", dot: "bg-[#00A153]" },
    offline: { bg: "bg-red-50", text: "text-red-800", border: "border-red-200", dot: "bg-[#E52B20]" },
    unknown: { bg: "bg-gray-100", text: "text-gray-700", border: "border-gray-300", dot: "bg-gray-400" },
    provisioning: { bg: "bg-yellow-50", text: "text-yellow-800", border: "border-yellow-200", dot: "bg-yellow-500" },
  };
  const c = cfg[status] || cfg.unknown;
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 border text-xs font-semibold uppercase tracking-wider ${c.bg} ${c.text} ${c.border}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot} ${status === "online" ? "pulse-dot" : ""}`}></span>
      {status}
    </span>
  );
};

const TABS = [
  { id: "overview", label: "Overview", icon: ChartBar },
  { id: "wan", label: "WAN Config", icon: Globe },
  { id: "wifi", label: "WiFi Config", icon: WifiHigh },
  { id: "diagnostics", label: "Diagnostics", icon: Network },
  { id: "ai", label: "AI Analysis", icon: Robot },
];

const inputCls = "w-full border border-[#E6E8EB] px-3 py-2 text-sm focus:outline-none focus:border-[#002FA7] focus:ring-1 focus:ring-[#002FA7] font-mono";
const labelCls = "block text-xs uppercase tracking-[0.12em] font-semibold text-gray-500 mb-1 font-body";

export default function DeviceDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [device, setDevice] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(true);
  const [settings, setSettings] = useState({});

  const [wanConfig, setWanConfig] = useState(null);
  const [wifi2g, setWifi2g] = useState(null);
  const [wifi5g, setWifi5g] = useState(null);
  const [savingWan, setSavingWan] = useState(false);
  const [savingWifi, setSavingWifi] = useState({ "2g": false, "5g": false });

  const [diagResult, setDiagResult] = useState(null);
  const [diagLoading, setDiagLoading] = useState({ ping: false, traceroute: false, speedtest: false });
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [diagHistory, setDiagHistory] = useState([]);

  useEffect(() => {
    const load = async () => {
      try {
        const [devRes, wanRes, wifiRes, settingsRes] = await Promise.all([
          axios.get(`${API}/devices/${id}`, { withCredentials: true }),
          axios.get(`${API}/devices/${id}/wan`, { withCredentials: true }),
          axios.get(`${API}/devices/${id}/wifi`, { withCredentials: true }),
          axios.get(`${API}/settings/public`, { withCredentials: true }),
        ]);
        setDevice(devRes.data);
        setWanConfig(wanRes.data);
        setWifi2g(wifiRes.data.wifi_2g);
        setWifi5g(wifiRes.data.wifi_5g);
        setSettings(settingsRes.data);

        const histRes = await axios.get(`${API}/diagnostics/${id}/history`, { withCredentials: true });
        setDiagHistory(histRes.data);
      } catch (e) { console.error(e); }
      setLoading(false);
    };
    load();
  }, [id]);

  const saveWan = async () => {
    setSavingWan(true);
    try {
      await axios.put(`${API}/devices/${id}/wan`, wanConfig, { withCredentials: true });
      alert("WAN config saved successfully");
    } catch (e) { alert(e.response?.data?.detail || "Save failed"); }
    setSavingWan(false);
  };

  const saveWifi = async (band) => {
    setSavingWifi((s) => ({ ...s, [band]: true }));
    try {
      const cfg = band === "2g" ? wifi2g : wifi5g;
      await axios.put(`${API}/devices/${id}/wifi?band=${band === "2g" ? "2.4GHz" : "5GHz"}`, cfg, { withCredentials: true });
      alert(`WiFi ${band === "2g" ? "2.4GHz" : "5GHz"} config saved`);
    } catch (e) { alert(e.response?.data?.detail || "Save failed"); }
    setSavingWifi((s) => ({ ...s, [band]: false }));
  };

  const runDiag = async (type) => {
    setDiagLoading((d) => ({ ...d, [type]: true }));
    setDiagResult(null);
    try {
      const { data } = await axios.post(`${API}/diagnostics/${id}/${type}`, {}, { withCredentials: true });
      setDiagResult({ type, data });
      const histRes = await axios.get(`${API}/diagnostics/${id}/history`, { withCredentials: true });
      setDiagHistory(histRes.data);
      await axios.get(`${API}/devices/${id}`, { withCredentials: true }).then((r) => setDevice(r.data));
    } catch (e) { setDiagResult({ type, error: e.response?.data?.detail || "Failed" }); }
    setDiagLoading((d) => ({ ...d, [type]: false }));
  };

  const runAI = async () => {
    setAiLoading(true);
    setAiAnalysis(null);
    try {
      const { data } = await axios.post(`${API}/diagnostics/${id}/ai-analyze`, {}, { withCredentials: true });
      setAiAnalysis(data.result?.analysis || "No analysis returned");
    } catch (e) { setAiAnalysis(`Error: ${e.response?.data?.detail || "AI analysis failed"}`); }
    setAiLoading(false);
  };

  if (loading) {
    return <div className="p-12 flex justify-center"><div className="w-8 h-8 border-2 border-[#002FA7] border-t-transparent rounded-full animate-spin"></div></div>;
  }
  if (!device) return <div className="p-8 text-center text-gray-500">Device not found</div>;

  return (
    <div className="fade-in">
      {/* Header */}
      <div className="px-6 md:px-8 py-5 border-b border-[#E6E8EB]">
        <Link to="/devices" className="flex items-center gap-1 text-xs text-gray-400 hover:text-[#002FA7] mb-3 font-body transition-colors w-fit">
          <ArrowLeft size={12} /> Back to Devices
        </Link>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-[#0A0B0D] font-heading">{device.name}</h1>
            <p className="text-sm text-gray-500 font-body mt-0.5">{device.manufacturer} {device.model} &bull; <span className="font-mono text-xs">{device.serial_number}</span></p>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={device.status} />
            <span className="text-xs font-mono bg-blue-50 text-blue-700 border border-blue-200 px-2 py-1">
              {device.protocol?.toUpperCase()}
            </span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-[#E6E8EB] px-6 md:px-8 flex gap-0 overflow-x-auto">
        {TABS.map(({ id: tabId, label, icon: Icon }) => {
          if (tabId === "ai" && !settings.ai_enabled) return null;
          return (
            <button
              key={tabId}
              className={`flex items-center gap-1.5 px-4 py-3 text-xs font-semibold uppercase tracking-wider border-b-2 transition-colors whitespace-nowrap font-body ${
                activeTab === tabId
                  ? "border-[#002FA7] text-[#002FA7]"
                  : "border-transparent text-gray-500 hover:text-gray-800"
              }`}
              onClick={() => setActiveTab(tabId)}
              data-testid={`tab-${tabId}`}
            >
              <Icon size={14} />
              {label}
            </button>
          );
        })}
      </div>

      <div className="p-6 md:p-8">
        {/* OVERVIEW TAB */}
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="overview-tab">
            {[
              { label: "IP Address", value: device.ip_address || "Not configured", mono: true },
              { label: "MAC Address", value: device.mac_address || "—", mono: true },
              { label: "Firmware", value: device.firmware_version || "Unknown", mono: true },
              { label: "Protocol", value: (device.protocol || "tr069").toUpperCase(), mono: true },
              { label: "Location", value: device.location || "—" },
              { label: "Provision Code", value: device.provision_code || "—", mono: true },
              { label: "Last Seen", value: device.last_seen ? new Date(device.last_seen).toLocaleString() : "Never" },
              { label: "Connected Clients", value: device.connected_clients ?? 0, mono: true },
              { label: "Uptime", value: device.uptime ? `${Math.floor(device.uptime / 3600)}h ${Math.floor((device.uptime % 3600) / 60)}m` : "Unknown" },
            ].map(({ label, value, mono }) => (
              <div key={label} className="border border-[#E6E8EB] p-4">
                <p className="text-[10px] uppercase tracking-[0.15em] font-semibold text-gray-400 mb-1 font-body">{label}</p>
                <p className={`text-sm font-semibold text-[#0A0B0D] ${mono ? "font-mono" : "font-body"}`}>{String(value)}</p>
              </div>
            ))}
            {device.notes && (
              <div className="border border-[#E6E8EB] p-4 md:col-span-2 lg:col-span-3">
                <p className="text-[10px] uppercase tracking-[0.15em] font-semibold text-gray-400 mb-1 font-body">Notes</p>
                <p className="text-sm text-gray-700 font-body">{device.notes}</p>
              </div>
            )}
            {/* ACS Info */}
            <div className="border border-[#002FA7]/20 bg-blue-50/50 p-4 md:col-span-2 lg:col-span-3">
              <p className="text-[10px] uppercase tracking-[0.15em] font-semibold text-[#002FA7] mb-2 font-body">ACS Configuration</p>
              <p className="text-xs text-gray-600 font-body mb-1">
                <span className="font-semibold">CWMP ACS URL:</span>{" "}
                <span className="font-mono">{settings.acs_url || `${process.env.REACT_APP_BACKEND_URL}/api/acs/cwmp`}</span>
              </p>
              <p className="text-xs text-gray-600 font-body mb-1">
                <span className="font-semibold">USP Endpoint:</span>{" "}
                <span className="font-mono">{process.env.REACT_APP_BACKEND_URL}/api/acs/usp/register</span>
              </p>
              <p className="text-xs text-gray-600 font-body">
                <span className="font-semibold">Inform Interval:</span>{" "}
                <span className="font-mono">{settings.inform_interval || 300}s</span>
              </p>
            </div>
          </div>
        )}

        {/* WAN CONFIG TAB */}
        {activeTab === "wan" && wanConfig && (
          <div data-testid="wan-tab">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold font-heading">WAN Configuration</h2>
              {user?.role !== "staff" && (
                <button
                  onClick={saveWan}
                  disabled={savingWan}
                  className="flex items-center gap-2 bg-[#002FA7] text-white px-4 py-2 text-sm font-semibold hover:bg-[#0035C4] disabled:opacity-60"
                  data-testid="save-wan-button"
                >
                  <FloppyDisk size={14} />
                  {savingWan ? "Saving..." : "Save WAN Config"}
                </button>
              )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div>
                <label className={labelCls}>Connection Mode</label>
                <select className={inputCls} value={wanConfig.mode} onChange={(e) => setWanConfig({ ...wanConfig, mode: e.target.value })} data-testid="wan-mode-select" disabled={user?.role === "staff"}>
                  <option value="dhcp">DHCP</option>
                  <option value="pppoe">PPPoE</option>
                  <option value="static">Static IP</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Connection Type</label>
                <select className={inputCls} value={wanConfig.connection_type} onChange={(e) => setWanConfig({ ...wanConfig, connection_type: e.target.value })} disabled={user?.role === "staff"}>
                  <option value="ethernet">Ethernet / Fiber</option>
                  <option value="adsl">ADSL</option>
                  <option value="vdsl">VDSL</option>
                  <option value="gpon">GPON</option>
                  <option value="4g">4G LTE</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>MTU</label>
                <input className={inputCls} type="number" value={wanConfig.mtu} onChange={(e) => setWanConfig({ ...wanConfig, mtu: parseInt(e.target.value) })} disabled={user?.role === "staff"} data-testid="wan-mtu-input" />
              </div>
              <div>
                <label className={labelCls}>VLAN ID (optional)</label>
                <input className={inputCls} type="number" placeholder="e.g. 100" value={wanConfig.vlan_id || ""} onChange={(e) => setWanConfig({ ...wanConfig, vlan_id: e.target.value ? parseInt(e.target.value) : null })} disabled={user?.role === "staff"} />
              </div>

              {wanConfig.mode === "pppoe" && (
                <>
                  <div>
                    <label className={labelCls}>PPPoE Username</label>
                    <input className={inputCls} value={wanConfig.pppoe_username} onChange={(e) => setWanConfig({ ...wanConfig, pppoe_username: e.target.value })} disabled={user?.role === "staff"} data-testid="wan-pppoe-user" />
                  </div>
                  <div>
                    <label className={labelCls}>PPPoE Password</label>
                    <input className={inputCls} type="password" value={wanConfig.pppoe_password} onChange={(e) => setWanConfig({ ...wanConfig, pppoe_password: e.target.value })} disabled={user?.role === "staff"} />
                  </div>
                </>
              )}

              {wanConfig.mode === "static" && (
                <>
                  <div>
                    <label className={labelCls}>IP Address</label>
                    <input className={inputCls} value={wanConfig.ip_address} onChange={(e) => setWanConfig({ ...wanConfig, ip_address: e.target.value })} disabled={user?.role === "staff"} />
                  </div>
                  <div>
                    <label className={labelCls}>Subnet Mask</label>
                    <input className={inputCls} value={wanConfig.subnet_mask} onChange={(e) => setWanConfig({ ...wanConfig, subnet_mask: e.target.value })} disabled={user?.role === "staff"} />
                  </div>
                  <div>
                    <label className={labelCls}>Gateway</label>
                    <input className={inputCls} value={wanConfig.gateway} onChange={(e) => setWanConfig({ ...wanConfig, gateway: e.target.value })} disabled={user?.role === "staff"} />
                  </div>
                </>
              )}

              <div>
                <label className={labelCls}>Primary DNS</label>
                <input className={inputCls} value={wanConfig.dns_primary} onChange={(e) => setWanConfig({ ...wanConfig, dns_primary: e.target.value })} disabled={user?.role === "staff"} />
              </div>
              <div>
                <label className={labelCls}>Secondary DNS</label>
                <input className={inputCls} value={wanConfig.dns_secondary} onChange={(e) => setWanConfig({ ...wanConfig, dns_secondary: e.target.value })} disabled={user?.role === "staff"} />
              </div>
            </div>
          </div>
        )}

        {/* WIFI CONFIG TAB */}
        {activeTab === "wifi" && wifi2g && wifi5g && (
          <div data-testid="wifi-tab">
            <h2 className="text-lg font-bold font-heading mb-5">WiFi Configuration</h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {[
                { band: "2g", label: "2.4 GHz Band", cfg: wifi2g, setCfg: setWifi2g },
                { band: "5g", label: "5 GHz Band", cfg: wifi5g, setCfg: setWifi5g },
              ].map(({ band, label, cfg, setCfg }) => (
                <div key={band} className="border border-[#E6E8EB]" data-testid={`wifi-${band}-panel`}>
                  <div className="flex items-center justify-between px-4 py-3 border-b border-[#E6E8EB] bg-[#FAFBFC]">
                    <div className="flex items-center gap-2">
                      <WifiHigh size={16} color="#002FA7" />
                      <h3 className="text-sm font-bold font-heading">{label}</h3>
                    </div>
                    <div className="flex items-center gap-3">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <span className="text-xs font-body text-gray-500">Enabled</span>
                        <input type="checkbox" checked={cfg.enabled} onChange={(e) => setCfg({ ...cfg, enabled: e.target.checked })} disabled={user?.role === "staff"} className="w-4 h-4" data-testid={`wifi-${band}-toggle`} />
                      </label>
                      {user?.role !== "staff" && (
                        <button onClick={() => saveWifi(band)} disabled={savingWifi[band]} className="flex items-center gap-1 bg-[#002FA7] text-white px-3 py-1.5 text-xs font-semibold hover:bg-[#0035C4] disabled:opacity-60" data-testid={`save-wifi-${band}`}>
                          <FloppyDisk size={12} />
                          {savingWifi[band] ? "Saving..." : "Save"}
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="p-4 space-y-3">
                    <div>
                      <label className={labelCls}>SSID (Network Name)</label>
                      <input className={inputCls} value={cfg.ssid} onChange={(e) => setCfg({ ...cfg, ssid: e.target.value })} disabled={user?.role === "staff"} data-testid={`wifi-${band}-ssid`} />
                    </div>
                    <div>
                      <label className={labelCls}>Password</label>
                      <input className={inputCls} type="password" value={cfg.password} onChange={(e) => setCfg({ ...cfg, password: e.target.value })} disabled={user?.role === "staff"} />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className={labelCls}>Security</label>
                        <select className={inputCls} value={cfg.security} onChange={(e) => setCfg({ ...cfg, security: e.target.value })} disabled={user?.role === "staff"}>
                          <option value="WPA2">WPA2</option>
                          <option value="WPA3">WPA3</option>
                          <option value="WPA2/WPA3">WPA2/WPA3</option>
                          <option value="WEP">WEP</option>
                          <option value="open">Open</option>
                        </select>
                      </div>
                      <div>
                        <label className={labelCls}>Channel</label>
                        <select className={inputCls} value={cfg.channel} onChange={(e) => setCfg({ ...cfg, channel: e.target.value })} disabled={user?.role === "staff"}>
                          <option value="auto">Auto</option>
                          {band === "2g"
                            ? [1,2,3,4,5,6,7,8,9,10,11,12,13].map((c) => <option key={c} value={String(c)}>{c}</option>)
                            : [36,40,44,48,52,56,60,64,100,104,108,112,116,120,124,128,132,136,140,149,153,157,161].map((c) => <option key={c} value={String(c)}>{c}</option>)
                          }
                        </select>
                      </div>
                      <div>
                        <label className={labelCls}>Bandwidth</label>
                        <select className={inputCls} value={cfg.bandwidth} onChange={(e) => setCfg({ ...cfg, bandwidth: e.target.value })} disabled={user?.role === "staff"}>
                          {band === "2g"
                            ? ["20MHz", "40MHz"].map((b) => <option key={b}>{b}</option>)
                            : ["20MHz", "40MHz", "80MHz", "160MHz"].map((b) => <option key={b}>{b}</option>)
                          }
                        </select>
                      </div>
                      <div>
                        <label className={labelCls}>TX Power</label>
                        <select className={inputCls} value={cfg.tx_power} onChange={(e) => setCfg({ ...cfg, tx_power: e.target.value })} disabled={user?.role === "staff"}>
                          <option value="auto">Auto</option>
                          <option value="high">High</option>
                          <option value="medium">Medium</option>
                          <option value="low">Low</option>
                        </select>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* DIAGNOSTICS TAB */}
        {activeTab === "diagnostics" && (
          <div data-testid="diagnostics-tab">
            <h2 className="text-lg font-bold font-heading mb-5">Diagnostics</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              {[
                { type: "ping", label: "Ping Test", icon: ChartBar, desc: "Test connectivity to device IP", enabled: settings.diagnostics_enabled !== false },
                { type: "traceroute", label: "Traceroute", icon: ClockCountdown, desc: "Trace network path to device", enabled: settings.diagnostics_enabled !== false },
                { type: "speedtest", label: "Speed Test", icon: Speedometer, desc: "Measure link throughput", enabled: settings.speed_test_enabled !== false },
              ].map(({ type, label, icon: Icon, desc, enabled }) => (
                <div key={type} className={`border border-[#E6E8EB] p-4 ${!enabled ? "opacity-50" : ""}`} data-testid={`diag-${type}-panel`}>
                  <div className="flex items-center gap-2 mb-2">
                    <Icon size={18} color="#002FA7" />
                    <h3 className="text-sm font-bold font-heading">{label}</h3>
                  </div>
                  <p className="text-xs text-gray-500 mb-4 font-body">{desc}</p>
                  <button
                    onClick={() => runDiag(type)}
                    disabled={diagLoading[type] || !enabled}
                    className="flex items-center gap-2 bg-[#002FA7] text-white px-3 py-2 text-xs font-semibold hover:bg-[#0035C4] disabled:opacity-60 w-full justify-center"
                    data-testid={`run-${type}-button`}
                  >
                    {diagLoading[type] ? (
                      <><div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin"></div> Running...</>
                    ) : (
                      <><Play size={12} /> Run {label}</>
                    )}
                  </button>
                </div>
              ))}
            </div>

            {diagResult && (
              <div className="border border-[#E6E8EB] mb-6" data-testid="diag-result">
                <div className="px-4 py-2 border-b border-[#E6E8EB] bg-[#FAFBFC] flex items-center gap-2">
                  <Waveform size={14} color="#002FA7" />
                  <span className="text-xs uppercase tracking-wider font-semibold text-gray-600 font-body">
                    {diagResult.type} Result
                  </span>
                </div>
                {diagResult.error ? (
                  <div className="p-4 text-sm text-[#E52B20] font-body">{diagResult.error}</div>
                ) : diagResult.type === "speedtest" ? (
                  <div className="grid grid-cols-4 gap-0 divide-x divide-[#E6E8EB]">
                    {[
                      { label: "Download", value: `${diagResult.data.result.download_mbps}`, unit: "Mbps", color: "#00A153" },
                      { label: "Upload", value: `${diagResult.data.result.upload_mbps}`, unit: "Mbps", color: "#002FA7" },
                      { label: "Ping", value: `${diagResult.data.result.ping_ms}`, unit: "ms", color: "#FFC800" },
                      { label: "Jitter", value: `${diagResult.data.result.jitter_ms}`, unit: "ms", color: "#E52B20" },
                    ].map(({ label, value, unit, color }) => (
                      <div key={label} className="p-4 text-center">
                        <p className="text-xs uppercase tracking-wider text-gray-400 mb-1 font-body">{label}</p>
                        <p className="text-2xl font-black font-mono" style={{ color }}>{value}</p>
                        <p className="text-xs text-gray-400 font-body">{unit}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="terminal-output">
                    {diagResult.data.result.raw_output || JSON.stringify(diagResult.data.result, null, 2)}
                  </div>
                )}
              </div>
            )}

            {/* Diagnostic History */}
            {diagHistory.length > 0 && (
              <div className="border border-[#E6E8EB]">
                <div className="px-4 py-2 border-b border-[#E6E8EB] bg-[#FAFBFC]">
                  <span className="text-xs uppercase tracking-wider font-semibold text-gray-600 font-body">Recent History</span>
                </div>
                <table className="data-table w-full">
                  <thead>
                    <tr>
                      <th className="text-left">Type</th>
                      <th className="text-left">Result</th>
                      <th className="text-left">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {diagHistory.slice(0, 10).map((h) => (
                      <tr key={h.id}>
                        <td><span className="text-xs font-mono font-semibold uppercase text-[#002FA7]">{h.type}</span></td>
                        <td>
                          <span className={`text-xs font-body ${h.result?.success ? "text-[#00A153]" : "text-[#E52B20]"}`}>
                            {h.type === "speedtest" ? `↓${h.result?.download_mbps}Mbps ↑${h.result?.upload_mbps}Mbps`
                              : h.type === "ai_diagnostic" ? "Analysis complete"
                              : h.result?.success ? `${h.result?.packets_received}/${h.result?.packets_sent} packets` : "Failed"}
                          </span>
                        </td>
                        <td><span className="text-xs text-gray-400 font-mono">{new Date(h.created_at).toLocaleString()}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* AI ANALYSIS TAB */}
        {activeTab === "ai" && settings.ai_enabled && (
          <div data-testid="ai-tab">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h2 className="text-lg font-bold font-heading">AI Diagnostics</h2>
                <p className="text-xs text-gray-500 font-body mt-0.5">Powered by Gemini 3 Flash — analyses device status and recent diagnostics</p>
              </div>
              <button
                onClick={runAI}
                disabled={aiLoading}
                className="flex items-center gap-2 bg-[#002FA7] text-white px-4 py-2 text-sm font-semibold hover:bg-[#0035C4] disabled:opacity-60"
                data-testid="run-ai-analysis-button"
              >
                {aiLoading ? (
                  <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div> Analyzing...</>
                ) : (
                  <><Robot size={16} /> Run AI Analysis</>
                )}
              </button>
            </div>

            {aiLoading && (
              <div className="border border-[#E6E8EB] p-8 text-center">
                <div className="w-8 h-8 border-2 border-[#002FA7] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                <p className="text-sm text-gray-500 font-body">Gemini is analyzing device data...</p>
              </div>
            )}

            {aiAnalysis && !aiLoading && (
              <div className="border border-[#002FA7]/20" data-testid="ai-analysis-result">
                <div className="flex items-center gap-2 px-4 py-2 border-b border-[#002FA7]/20 bg-blue-50/50">
                  <Robot size={14} color="#002FA7" />
                  <span className="text-xs uppercase tracking-wider font-semibold text-[#002FA7] font-body">AI Analysis Report</span>
                  <span className="ml-auto text-[10px] text-gray-400 font-mono">gemini-3-flash-preview</span>
                </div>
                <div className="terminal-output whitespace-pre-wrap" style={{ background: "#1A1B1E", color: "#E5E7EB" }}>
                  {aiAnalysis.replace(/\*\*(.+?)\*\*/g, "** $1 **")}
                </div>
              </div>
            )}

            {!aiAnalysis && !aiLoading && (
              <div className="border border-dashed border-[#E6E8EB] p-12 text-center"
                style={{ backgroundImage: `url('https://images.pexels.com/photos/6466141/pexels-photo-6466141.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940')`, backgroundSize: "cover", backgroundPosition: "center", position: "relative" }}>
                <div className="absolute inset-0 bg-white/90"></div>
                <div className="relative z-10">
                  <Robot size={40} className="text-gray-300 mx-auto mb-4" />
                  <p className="text-sm font-semibold text-gray-600 font-heading">Run AI analysis to get insights</p>
                  <p className="text-xs text-gray-400 mt-1 font-body">Gemini will analyze device configuration, status, and recent diagnostic history.</p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
