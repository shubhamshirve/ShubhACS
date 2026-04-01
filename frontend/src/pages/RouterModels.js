import React, { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import axios from "axios";
import {
  Plus,
  X,
  PencilSimple,
  Trash,
  MagnifyingGlass,
  Network,
  WifiHigh,
} from "@phosphor-icons/react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ISP_OPTIONS = ["BSNL", "MTNL", "Airtel", "Jio", "ACT Fibernet", "Hathway", "You Broadband", "Generic"];
const CATEGORY_OPTIONS = ["GPON ONT", "ADSL Router", "VDSL2 Router", "Fiber Router", "4G LTE Router", "SFP ONT", "Wireless Router", "Cable Modem"];

function RouterModelModal({ model, onClose, onSuccess }) {
  const [form, setForm] = useState(model || {
    brand: "", model: "", isps: [], protocols: ["TR-069"], chipset: "", category: "", ports: {}, notes: "", is_active: true,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const toggleIsp = (isp) => {
    setForm((f) => ({
      ...f,
      isps: f.isps.includes(isp) ? f.isps.filter((x) => x !== isp) : [...f.isps, isp],
    }));
  };
  const toggleProto = (proto) => {
    setForm((f) => ({
      ...f,
      protocols: f.protocols.includes(proto) ? f.protocols.filter((x) => x !== proto) : [...f.protocols, proto],
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (model) {
        await axios.put(`${API}/router-models/${model.id}`, form, { withCredentials: true });
      } else {
        await axios.post(`${API}/router-models`, form, { withCredentials: true });
      }
      onSuccess();
    } catch (err) { setError(err.response?.data?.detail || "Operation failed"); }
    setLoading(false);
  };

  const inp = "w-full border border-[#E6E8EB] px-3 py-2 text-sm focus:outline-none focus:border-[#002FA7] font-body";
  const lbl = "block text-xs uppercase tracking-[0.12em] font-semibold text-gray-500 mb-1 font-body";

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E6E8EB]">
          <h2 className="text-lg font-bold font-heading">{model ? "Edit Router Model" : "Add Router Model"}</h2>
          <button onClick={onClose}><X size={18} /></button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && <div className="p-3 border border-[#E52B20] bg-red-50 text-sm text-[#E52B20]">{error}</div>}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={lbl}>Brand *</label>
              <input className={inp} value={form.brand} onChange={(e) => setForm({ ...form, brand: e.target.value })} required placeholder="e.g. Huawei, ZTE, Nokia" data-testid="router-brand-input" />
            </div>
            <div>
              <label className={lbl}>Model *</label>
              <input className={inp} value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} required placeholder="e.g. HG8245H, F660" data-testid="router-model-input" />
            </div>
            <div>
              <label className={lbl}>Chipset</label>
              <input className={inp} value={form.chipset} onChange={(e) => setForm({ ...form, chipset: e.target.value })} placeholder="e.g. Broadcom BCM6362" />
            </div>
            <div>
              <label className={lbl}>Category</label>
              <select className={inp} value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                <option value="">Select Category</option>
                {CATEGORY_OPTIONS.map((c) => <option key={c}>{c}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className={lbl}>Compatible ISPs</label>
            <div className="flex flex-wrap gap-2 mt-1">
              {ISP_OPTIONS.map((isp) => (
                <button key={isp} type="button"
                  className={`px-3 py-1 text-xs font-semibold border transition-colors font-body ${form.isps.includes(isp) ? "bg-[#002FA7] text-white border-[#002FA7]" : "border-[#E6E8EB] text-gray-600 hover:border-[#002FA7]"}`}
                  onClick={() => toggleIsp(isp)} data-testid={`isp-${isp}`}>
                  {isp}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className={lbl}>Supported Protocols</label>
            <div className="flex gap-2 mt-1">
              {["TR-069", "TR-369"].map((proto) => (
                <button key={proto} type="button"
                  className={`px-3 py-1 text-xs font-semibold border transition-colors font-mono ${form.protocols.includes(proto) ? "bg-[#002FA7] text-white border-[#002FA7]" : "border-[#E6E8EB] text-gray-600 hover:border-[#002FA7]"}`}
                  onClick={() => toggleProto(proto)}>
                  {proto}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className={lbl}>Notes</label>
            <textarea className={`${inp} resize-none`} rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })}></textarea>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm border border-[#E6E8EB] hover:bg-gray-50 font-body">Cancel</button>
            <button type="submit" disabled={loading} className="px-6 py-2 text-sm bg-[#002FA7] text-white font-semibold hover:bg-[#0035C4] disabled:opacity-60 font-body" data-testid="router-model-submit">
              {loading ? "Saving..." : model ? "Update Model" : "Add Model"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function RouterModels() {
  const { user } = useAuth();
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterIsp, setFilterIsp] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editModel, setEditModel] = useState(null);

  const fetch = async () => {
    setLoading(true);
    try {
      const params = {};
      if (search) params.search = search;
      if (filterIsp) params.isp = filterIsp;
      const { data } = await axios.get(`${API}/router-models`, { params, withCredentials: true });
      setModels(data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => { fetch(); }, [search, filterIsp]);

  const handleDelete = async (m) => {
    if (!window.confirm(`Delete "${m.brand} ${m.model}"?`)) return;
    try {
      await axios.delete(`${API}/router-models/${m.id}`, { withCredentials: true });
      fetch();
    } catch (e) { alert(e.response?.data?.detail || "Delete failed"); }
  };

  return (
    <div className="fade-in">
      <div className="px-6 md:px-8 py-6 border-b border-[#E6E8EB] flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] font-semibold text-gray-400 mb-0.5 font-body">Device Reference</p>
          <h1 className="text-2xl font-black text-[#0A0B0D] font-heading">Router Library</h1>
        </div>
        {user?.role === "super_admin" && (
          <button className="flex items-center gap-2 bg-[#002FA7] text-white px-4 py-2 text-sm font-semibold hover:bg-[#0035C4]" onClick={() => { setEditModel(null); setShowModal(true); }} data-testid="add-router-model-button">
            <Plus size={14} /> Add Model
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="px-6 md:px-8 py-3 border-b border-[#E6E8EB] flex flex-wrap gap-3 items-center bg-[#FAFBFC]">
        <div className="flex items-center gap-2 border border-[#E6E8EB] bg-white px-3 py-2 flex-1 min-w-[200px] max-w-sm">
          <MagnifyingGlass size={14} className="text-gray-400" />
          <input className="flex-1 text-sm outline-none font-body" placeholder="Search brand, model, chipset..." value={search} onChange={(e) => setSearch(e.target.value)} data-testid="router-search-input" />
        </div>
        <select className="border border-[#E6E8EB] px-3 py-2 text-sm focus:outline-none focus:border-[#002FA7] font-body bg-white" value={filterIsp} onChange={(e) => setFilterIsp(e.target.value)} data-testid="router-isp-filter">
          <option value="">All ISPs</option>
          {ISP_OPTIONS.map((isp) => <option key={isp}>{isp}</option>)}
        </select>
        <span className="text-xs text-gray-400 font-mono ml-auto">{models.length} models</span>
      </div>

      {loading ? (
        <div className="p-12 flex justify-center"><div className="w-8 h-8 border-2 border-[#002FA7] border-t-transparent rounded-full animate-spin"></div></div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-6 md:p-8" data-testid="router-models-grid">
          {models.map((m) => (
            <div key={m.id} className="border border-[#E6E8EB] hover:shadow-sm transition-shadow" data-testid={`router-card-${m.id}`}>
              <div className="px-4 py-3 border-b border-[#E6E8EB] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Network size={16} color="#002FA7" />
                  <div>
                    <p className="text-xs font-bold font-heading text-[#002FA7]">{m.brand}</p>
                    <p className="text-sm font-black font-heading text-[#0A0B0D]">{m.model}</p>
                  </div>
                </div>
                {user?.role === "super_admin" && (
                  <div className="flex gap-1">
                    <button className="p-1 text-gray-400 hover:text-[#002FA7] transition-colors" onClick={() => { setEditModel(m); setShowModal(true); }} data-testid={`edit-router-${m.id}`}><PencilSimple size={13} /></button>
                    <button className="p-1 text-gray-400 hover:text-[#E52B20] transition-colors" onClick={() => handleDelete(m)} data-testid={`delete-router-${m.id}`}><Trash size={13} /></button>
                  </div>
                )}
              </div>
              <div className="p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase tracking-wider text-gray-400 font-body">Category</span>
                  <span className="text-xs font-semibold text-gray-700 font-body">{m.category || "—"}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase tracking-wider text-gray-400 font-body">Chipset</span>
                  <span className="text-xs font-mono text-gray-600">{m.chipset || "—"}</span>
                </div>
                <div className="flex flex-wrap gap-1 mt-2">
                  {m.protocols?.map((p) => (
                    <span key={p} className="text-[10px] font-mono font-semibold px-1.5 py-0.5 bg-blue-50 text-blue-700 border border-blue-200">{p}</span>
                  ))}
                </div>
                <div className="flex flex-wrap gap-1 mt-1">
                  {m.isps?.slice(0, 3).map((isp) => (
                    <span key={isp} className="text-[10px] font-body px-1.5 py-0.5 bg-gray-100 text-gray-600">{isp}</span>
                  ))}
                  {m.isps?.length > 3 && <span className="text-[10px] text-gray-400 font-body">+{m.isps.length - 3}</span>}
                </div>
              </div>
            </div>
          ))}
          {models.length === 0 && (
            <div className="col-span-full text-center py-16">
              <Network size={40} className="text-gray-200 mx-auto mb-4" />
              <p className="text-sm font-semibold text-gray-500 font-heading">No router models found</p>
              <p className="text-xs text-gray-400 mt-1 font-body">Try adjusting your search or filters.</p>
            </div>
          )}
        </div>
      )}

      {showModal && (
        <RouterModelModal model={editModel} onClose={() => { setShowModal(false); setEditModel(null); }} onSuccess={() => { setShowModal(false); setEditModel(null); fetch(); }} />
      )}
    </div>
  );
}
