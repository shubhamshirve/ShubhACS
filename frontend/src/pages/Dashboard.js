import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import axios from "axios";
import {
  HardDrives,
  WifiHigh,
  Buildings,
  Users,
  CheckCircle,
  XCircle,
  Question,
  ArrowRight,
  ChartBar,
} from "@phosphor-icons/react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/stats`, { withCredentials: true })
      .then((r) => setStats(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  // Auto-refresh stats every 60 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      axios.get(`${API}/stats`, { withCredentials: true })
        .then((r) => setStats(r.data))
        .catch(console.error);
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="w-8 h-8 border-2 border-[#002FA7] border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  const kpiCards = [
    ...(user?.role === "super_admin"
      ? [
          {
            label: "Total Operators",
            value: stats?.total_operators ?? 0,
            icon: Buildings,
            color: "#002FA7",
            link: "/operators",
          },
        ]
      : []),
    {
      label: "Total Devices",
      value: stats?.total_devices ?? 0,
      icon: HardDrives,
      color: "#002FA7",
      link: "/devices",
    },
    {
      label: "Online",
      value: stats?.online_devices ?? 0,
      icon: CheckCircle,
      color: "#00A153",
      link: "/devices?status=online",
    },
    {
      label: "Offline",
      value: stats?.offline_devices ?? 0,
      icon: XCircle,
      color: "#E52B20",
      link: "/devices?status=offline",
    },
    {
      label: "Unknown",
      value: stats?.unknown_devices ?? 0,
      icon: Question,
      color: "#FFC800",
      link: "/devices?status=unknown",
    },
    ...(user?.role === "super_admin"
      ? [{ label: "Total Users", value: stats?.total_users ?? 0, icon: Users, color: "#374151", link: "/users" }]
      : []),
    ...(user?.role === "operator"
      ? [{ label: "Staff Members", value: stats?.staff_count ?? 0, icon: Users, color: "#374151", link: "/users" }]
      : []),
  ];

  const protocols = stats?.protocol_distribution || {};

  return (
    <div className="p-6 md:p-8 fade-in">
      {/* Header */}
      <div className="mb-6 border-b border-[#E6E8EB] pb-5 flex items-end justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] font-semibold text-gray-400 mb-1 font-body">
            {user?.role === "super_admin" ? "Platform Overview" : "Operations Dashboard"}
          </p>
          <h1 className="text-3xl font-black text-[#0A0B0D] font-heading">Dashboard</h1>
          {user?.operator_id && (
            <p className="text-sm text-gray-500 mt-1 font-body">Operator: {user?.operator_name || user?.operator_id}</p>
          )}
        </div>
        <span className="flex items-center gap-1.5 text-[10px] text-green-600 font-mono mb-1">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse inline-block"></span>
          Auto-refresh
        </span>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-8" data-testid="kpi-grid">
        {kpiCards.map(({ label, value, icon: Icon, color, link }) => (
          <Link
            key={label}
            to={link}
            className="kpi-card group no-underline"
            data-testid={`kpi-${label.toLowerCase().replace(/\s+/g, "-")}`}
          >
            <div className="flex items-start justify-between mb-3">
              <div style={{ color }} className="opacity-80">
                <Icon size={22} weight="regular" />
              </div>
              <ArrowRight size={14} className="text-gray-300 group-hover:text-[#002FA7] transition-colors" />
            </div>
            <p className="text-3xl font-black font-mono" style={{ color }}>{value}</p>
            <p className="text-xs uppercase tracking-[0.15em] font-semibold text-gray-400 mt-1 font-body">{label}</p>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Protocol Distribution */}
        <div className="border border-[#E6E8EB] p-5">
          <div className="flex items-center gap-2 mb-4 border-b border-[#E6E8EB] pb-3">
            <ChartBar size={16} color="#002FA7" />
            <h3 className="text-xs uppercase tracking-[0.15em] font-semibold text-gray-500 font-body">Protocol Distribution</h3>
          </div>
          <div className="space-y-3">
            {[
              { label: "TR-069 (CWMP)", key: "tr069", color: "#002FA7" },
              { label: "TR-369 (USP)", key: "tr369", color: "#00A153" },
              { label: "Dual (Both)", key: "both", color: "#FFC800" },
            ].map(({ label, key, color }) => {
              const count = protocols[key] || 0;
              const total = stats?.total_devices || 1;
              const pct = total > 0 ? Math.round((count / total) * 100) : 0;
              return (
                <div key={key}>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs font-medium text-gray-600 font-body">{label}</span>
                    <span className="text-xs font-mono font-bold" style={{ color }}>{count}</span>
                  </div>
                  <div className="h-1.5 bg-gray-100 w-full">
                    <div className="h-1.5 transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: color }}></div>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-4 pt-3 border-t border-[#E6E8EB]">
            <p className="text-[10px] uppercase tracking-wider text-gray-400 font-body">Diagnostics This Week</p>
            <p className="text-2xl font-black font-mono text-[#002FA7] mt-1">{stats?.diagnostics_this_week ?? 0}</p>
          </div>
        </div>

        {/* Recent Devices */}
        <div className="lg:col-span-2 border border-[#E6E8EB]">
          <div className="flex items-center justify-between px-5 py-3 border-b border-[#E6E8EB]">
            <div className="flex items-center gap-2">
              <HardDrives size={16} color="#002FA7" />
              <h3 className="text-xs uppercase tracking-[0.15em] font-semibold text-gray-500 font-body">Recent Devices</h3>
            </div>
            <Link to="/devices" className="text-xs text-[#002FA7] font-semibold hover:underline font-body">
              View All →
            </Link>
          </div>
          <div data-testid="recent-devices-list">
            {(stats?.recent_devices || []).length === 0 ? (
              <div className="p-8 text-center text-sm text-gray-400 font-body">No devices yet. Add your first device.</div>
            ) : (
              (stats?.recent_devices || []).map((device) => (
                <Link
                  key={device.id}
                  to={`/devices/${device.id}`}
                  className="flex items-center gap-3 px-5 py-3 border-b border-[#F0F2F4] hover:bg-[#F8F9FF] transition-colors no-underline"
                  data-testid={`device-row-${device.id}`}
                >
                  <div className={`w-2 h-2 flex-shrink-0 ${
                    device.status === "online" ? "bg-[#00A153]" :
                    device.status === "offline" ? "bg-[#E52B20]" : "bg-gray-300"
                  }`}></div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-[#0A0B0D] truncate font-heading">{device.name}</p>
                    <p className="text-xs text-gray-400 font-mono">{device.ip_address || "No IP"}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-xs text-gray-500 font-body">{device.manufacturer}</p>
                    <p className="text-xs text-gray-400 font-body">{device.model}</p>
                  </div>
                  <ArrowRight size={12} className="text-gray-300 flex-shrink-0" />
                </Link>
              ))
            )}
          </div>
          {(stats?.recent_devices || []).length > 0 && (
            <div className="px-5 py-3 bg-[#FAFBFC]">
              <Link to="/devices" className="text-xs text-[#002FA7] font-semibold font-body">
                View all {stats?.total_devices} devices →
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
