import React, { useState, useEffect, useCallback } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import axios from "axios";
import {
  Plus,
  MagnifyingGlass,
  Funnel,
  ArrowRight,
  Trash,
  PencilSimple,
  CheckCircle,
  XCircle,
  Question,
  WifiHigh,
  X,
} from "@phosphor-icons/react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const StatusBadge = ({ status }) => {
  const cfg = {
    online: { cls: "status-online", label: "Online" },
    offline: { cls: "status-offline", label: "Offline" },
    unknown: { cls: "status-unknown", label: "Unknown" },
    provisioning: { cls: "status-provisioning", label: "Provisioning" },
  };
  const { cls, label } = cfg[status] || cfg.unknown;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${cls}`}>
      {label}
    </span>
  );
};

const ProtocolBadge = ({ protocol }) => {
  const colors = {
    tr069: "bg-blue-50 text-blue-700 border border-blue-200",
    tr369: "bg-green-50 text-green-700 border border-green-200",
    both: "bg-purple-50 text-purple-700 border border-purple-200",
  };
  return (
    <span className={`inline-flex px-2 py-0.5 text-[10px] font-mono font-semibold uppercase ${colors[protocol] || colors.tr069}`}>
      {protocol?.toUpperCase() || "TR-069"}
    </span>
  );
};

function AddDeviceModal({ operators, onClose, onSuccess }) {
  const { user } = useAuth();
  const [form, setForm] = useState({
    name: "", serial_number: "", mac_address: "", ip_address: "",
    manufacturer: "", model: "", firmware_version: "", protocol: "tr069",
    operator_id: user?.operator_id || "", location: "", notes: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await axios.post(`${API}/devices`, form, { withCredentials: true });
      onSuccess();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to add device");
    } finally {
      setLoading(false);
    }
  };

  const inputCls = "w-full border border-[#E6E8EB] px-3 py-2 text-sm focus:outline-none focus:border-[#002FA7] focus:ring-1 focus:ring-[#002FA7] font-body";
  const labelCls = "block text-xs uppercase tracking-[0.12em] font-semibold text-gray-500 mb-1 font-body";

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" data-testid="add-device-modal">
      <div className="bg-white w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E6E8EB]">
          <h2 className="text-lg font-bold font-heading">Add New Device</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100"><X size={18} /></button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && <div className="p-3 border border-[#E52B20] bg-red-50 text-sm text-[#E52B20]" data-testid="add-device-error">{error}</div>}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Device Name *</label>
              <input className={inputCls} value={form.name} onChange={(e) => set("name", e.target.value)} required data-testid="device-name-input" />
            </div>
            <div>
              <label className={labelCls}>Serial Number *</label>
              <input className={inputCls} value={form.serial_number} onChange={(e) => set("serial_number", e.target.value)} required data-testid="device-serial-input" />
            </div>
            <div>
              <label className={labelCls}>MAC Address</label>
              <input className={inputCls} placeholder="AA:BB:CC:DD:EE:FF" value={form.mac_address} onChange={(e) => set("mac_address", e.target.value)} data-testid="device-mac-input" />
            </div>
            <div>
              <label className={labelCls}>IP Address</label>
              <input className={inputCls} placeholder="192.168.1.1" value={form.ip_address} onChange={(e) => set("ip_address", e.target.value)} data-testid="device-ip-input" />
            </div>
            <div>
              <label className={labelCls}>Manufacturer</label>
              <input className={inputCls} placeholder="Huawei, ZTE, Nokia..." value={form.manufacturer} onChange={(e) => set("manufacturer", e.target.value)} data-testid="device-manufacturer-input" />
            </div>
            <div>
              <label className={labelCls}>Model</label>
              <input className={inputCls} placeholder="HG8245H, F660..." value={form.model} onChange={(e) => set("model", e.target.value)} data-testid="device-model-input" />
            </div>
            <div>
              <label className={labelCls}>Firmware Version</label>
              <input className={inputCls} value={form.firmware_version} onChange={(e) => set("firmware_version", e.target.value)} />
            </div>
            <div>
              <label className={labelCls}>Protocol</label>
              <select className={inputCls} value={form.protocol} onChange={(e) => set("protocol", e.target.value)} data-testid="device-protocol-select">
                <option value="tr069">TR-069 (CWMP)</option>
                <option value="tr369">TR-369 (USP)</option>
                <option value="both">Both</option>
              </select>
            </div>
            {user?.role === "super_admin" && (
              <div className="col-span-2">
                <label className={labelCls}>Operator *</label>
                <select className={inputCls} value={form.operator_id} onChange={(e) => set("operator_id", e.target.value)} required data-testid="device-operator-select">
                  <option value="">Select Operator</option>
                  {operators.map((op) => (
                    <option key={op.id} value={op.id}>{op.name} ({op.code})</option>
                  ))}
                </select>
              </div>
            )}
            <div>
              <label className={labelCls}>Location</label>
              <input className={inputCls} placeholder="City, Area..." value={form.location} onChange={(e) => set("location", e.target.value)} />
            </div>
            <div>
              <label className={labelCls}>Notes</label>
              <input className={inputCls} value={form.notes} onChange={(e) => set("notes", e.target.value)} />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm border border-[#E6E8EB] hover:bg-gray-50 font-body">Cancel</button>
            <button type="submit" disabled={loading} className="px-6 py-2 text-sm bg-[#002FA7] text-white font-semibold hover:bg-[#0035C4] disabled:opacity-60 font-body" data-testid="add-device-submit">
              {loading ? "Adding..." : "Add Device"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function DeviceList() {
  const { user } = useAuth();
  const [devices, setDevices] = useState([]);
  const [operators, setOperators] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterProtocol, setFilterProtocol] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [searchParams] = useSearchParams();

  useEffect(() => {
    const s = searchParams.get("status");
    if (s) setFilterStatus(s);
  }, [searchParams]);

  const fetchDevices = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (search) params.search = search;
      if (filterStatus) params.status = filterStatus;
      if (filterProtocol) params.protocol = filterProtocol;
      const { data } = await axios.get(`${API}/devices`, { params, withCredentials: true });
      setDevices(data);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [search, filterStatus, filterProtocol]);

  useEffect(() => {
    fetchDevices();
  }, [fetchDevices]);

  // Real-time status polling every 30 seconds (fires immediately on mount)
  useEffect(() => {
    const pollStatus = async () => {
      try {
        const { data } = await axios.get(`${API}/devices/status-updates`, { withCredentials: true });
        const statusById = {};
        data.forEach((d) => { statusById[d.id] = d; });
        setDevices((prev) =>
          prev.map((device) =>
            statusById[device.id]
              ? { ...device, status: statusById[device.id].status, last_seen: statusById[device.id].last_seen, ip_address: statusById[device.id].ip_address }
              : device
          )
        );
        setLastUpdated(new Date());
      } catch (e) {}
    };
    // Fire immediately on mount, then every 30s
    pollStatus();
    const interval = setInterval(pollStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (user?.role === "super_admin") {
      axios.get(`${API}/operators`, { withCredentials: true })
        .then((r) => setOperators(r.data)).catch(console.error);
    }
  }, [user]);

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Delete device "${name}"? This will also delete all diagnostic history.`)) return;
    try {
      await axios.delete(`${API}/devices/${id}`, { withCredentials: true });
      setDevices((d) => d.filter((x) => x.id !== id));
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to delete");
    }
  };

  return (
    <div className="fade-in">
      {/* Header */}
      <div className="px-6 md:px-8 py-6 border-b border-[#E6E8EB] flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] font-semibold text-gray-400 mb-0.5 font-body">CPE Management</p>
          <h1 className="text-2xl font-black text-[#0A0B0D] font-heading">Devices</h1>
        </div>
        {user?.role !== "staff" && (
          <button
            className="flex items-center gap-2 bg-[#002FA7] text-white px-4 py-2 text-sm font-semibold hover:bg-[#0035C4] transition-colors"
            onClick={() => setShowAdd(true)}
            data-testid="add-device-button"
          >
            <Plus size={16} />
            Add Device
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="px-6 md:px-8 py-4 border-b border-[#E6E8EB] flex flex-wrap gap-3 items-center bg-[#FAFBFC]">
        <div className="flex items-center gap-2 border border-[#E6E8EB] bg-white px-3 py-2 flex-1 min-w-[200px] max-w-sm">
          <MagnifyingGlass size={14} className="text-gray-400" />
          <input
            className="flex-1 text-sm outline-none font-body"
            placeholder="Search by name, serial, IP..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            data-testid="device-search-input"
          />
          {search && <button onClick={() => setSearch("")}><X size={12} className="text-gray-400" /></button>}
        </div>

        <div className="flex items-center gap-2">
          <Funnel size={14} className="text-gray-400" />
          <select
            className="border border-[#E6E8EB] px-3 py-2 text-sm focus:outline-none focus:border-[#002FA7] font-body bg-white"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            data-testid="status-filter"
          >
            <option value="">All Status</option>
            <option value="online">Online</option>
            <option value="offline">Offline</option>
            <option value="unknown">Unknown</option>
            <option value="provisioning">Provisioning</option>
          </select>
          <select
            className="border border-[#E6E8EB] px-3 py-2 text-sm focus:outline-none focus:border-[#002FA7] font-body bg-white"
            value={filterProtocol}
            onChange={(e) => setFilterProtocol(e.target.value)}
            data-testid="protocol-filter"
          >
            <option value="">All Protocols</option>
            <option value="tr069">TR-069</option>
            <option value="tr369">TR-369</option>
            <option value="both">Both</option>
          </select>
          {(filterStatus || filterProtocol) && (
            <button
              className="text-xs text-[#E52B20] font-semibold"
              onClick={() => { setFilterStatus(""); setFilterProtocol(""); }}
            >Clear</button>
          )}
        </div>

        <div className="ml-auto flex items-center gap-3 text-xs text-gray-400 font-mono">
          {lastUpdated && (
            <span className="flex items-center gap-1.5 text-green-600">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse inline-block"></span>
              Live
            </span>
          )}
          {devices.length} device{devices.length !== 1 ? "s" : ""}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        {loading ? (
          <div className="p-12 flex justify-center">
            <div className="w-8 h-8 border-2 border-[#002FA7] border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : devices.length === 0 ? (
          <div className="p-16 text-center" data-testid="no-devices-message">
            <WifiHigh size={40} className="text-gray-200 mx-auto mb-4" />
            <p className="text-sm font-semibold text-gray-500 font-heading">No devices found</p>
            <p className="text-xs text-gray-400 mt-1 font-body">
              {search || filterStatus || filterProtocol ? "Try adjusting your filters." : "Add your first device to get started."}
            </p>
          </div>
        ) : (
          <table className="data-table w-full">
            <thead>
              <tr>
                <th className="text-left">Status</th>
                <th className="text-left">Device</th>
                <th className="text-left">Serial / MAC</th>
                <th className="text-left">IP Address</th>
                <th className="text-left">Protocol</th>
                {user?.role === "super_admin" && <th className="text-left">Operator</th>}
                <th className="text-left">Firmware</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody data-testid="device-table-body">
              {devices.map((device) => (
                <tr key={device.id} data-testid={`device-row-${device.id}`}>
                  <td><StatusBadge status={device.status} /></td>
                  <td>
                    <Link to={`/devices/${device.id}`} className="group" data-testid={`device-link-${device.id}`}>
                      <p className="text-sm font-semibold text-[#0A0B0D] group-hover:text-[#002FA7] transition-colors font-heading">{device.name}</p>
                      <p className="text-xs text-gray-400 font-body">{device.manufacturer} {device.model}</p>
                    </Link>
                  </td>
                  <td>
                    <p className="text-xs font-mono text-gray-600">{device.serial_number || "—"}</p>
                    <p className="text-xs font-mono text-gray-400">{device.mac_address || "—"}</p>
                  </td>
                  <td><span className="text-xs font-mono text-gray-700">{device.ip_address || "—"}</span></td>
                  <td><ProtocolBadge protocol={device.protocol} /></td>
                  {user?.role === "super_admin" && (
                    <td><span className="text-xs text-gray-600 font-body">{device.operator_name || "—"}</span></td>
                  )}
                  <td><span className="text-xs font-mono text-gray-500">{device.firmware_version || "—"}</span></td>
                  <td>
                    <div className="flex items-center justify-end gap-2">
                      <Link
                        to={`/devices/${device.id}`}
                        className="p-1.5 border border-[#E6E8EB] hover:border-[#002FA7] hover:text-[#002FA7] text-gray-500 transition-colors"
                        title="View Details"
                        data-testid={`view-device-${device.id}`}
                      >
                        <ArrowRight size={14} />
                      </Link>
                      {user?.role !== "staff" && (
                        <button
                          className="p-1.5 border border-[#E6E8EB] hover:border-[#E52B20] hover:text-[#E52B20] text-gray-400 transition-colors"
                          title="Delete"
                          onClick={() => handleDelete(device.id, device.name)}
                          data-testid={`delete-device-${device.id}`}
                        >
                          <Trash size={14} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showAdd && (
        <AddDeviceModal
          operators={operators}
          onClose={() => setShowAdd(false)}
          onSuccess={() => { setShowAdd(false); fetchDevices(); }}
        />
      )}
    </div>
  );
}
