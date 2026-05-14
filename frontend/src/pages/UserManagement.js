import React, { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import axios from "axios";
import {
  Plus,
  X,
  PencilSimple,
  Trash,
  CheckCircle,
  XCircle,
  Buildings,
  Users,
  Key,
  Eye,
  EyeSlash,
  ArrowsClockwise,
  Copy,
  Check,
} from "@phosphor-icons/react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TABS = [
  { id: "operators", label: "Operators", icon: Buildings, roles: ["super_admin"] },
  { id: "users", label: "Users & Staff", icon: Users, roles: ["super_admin", "operator"] },
];

function OperatorModal({ operator, onClose, onSuccess }) {
  const genPassword = () => {
    const chars = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789@#!";
    return Array.from({ length: 12 }, () => chars[Math.floor(Math.random() * chars.length)]).join("");
  };

  const [form, setForm] = useState(
    operator
      ? { ...operator }
      : { name: "", code: "", contact_email: "", contact_phone: "", address: "", is_active: true, acs_username: "", acs_password: genPassword() }
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [copied, setCopied] = useState("");
  const [acsUserEdited, setAcsUserEdited] = useState(!!operator?.acs_username);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleCodeChange = (v) => {
    const upper = v.toUpperCase();
    setForm((f) => ({
      ...f,
      code: upper,
      acs_username: acsUserEdited ? f.acs_username : upper.toLowerCase(),
    }));
  };

  const handleAcsUserChange = (v) => {
    setAcsUserEdited(true);
    set("acs_username", v.toLowerCase().replace(/[^a-z0-9-_]/g, ""));
  };

  const copyToClipboard = (text, key) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(key);
      setTimeout(() => setCopied(""), 2000);
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (operator) {
        await axios.put(`${API}/operators/${operator.id}`, form, { withCredentials: true });
      } else {
        await axios.post(`${API}/operators`, form, { withCredentials: true });
      }
      onSuccess();
    } catch (err) { setError(err.response?.data?.detail || "Operation failed"); }
    setLoading(false);
  };

  const inp = "w-full border border-[#E6E8EB] px-3 py-2 text-sm focus:outline-none focus:border-[#002FA7] font-body";
  const lbl = "block text-xs uppercase tracking-[0.12em] font-semibold text-gray-500 mb-1 font-body";
  const cwmpUrl = `${window.location.origin}/api/acs/cwmp`;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white w-full max-w-lg my-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E6E8EB]">
          <h2 className="text-lg font-bold font-heading">{operator ? "Edit Operator" : "Add Operator"}</h2>
          <button onClick={onClose}><X size={18} /></button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && <div className="p-3 border border-[#E52B20] bg-red-50 text-sm text-[#E52B20]">{error}</div>}

          {/* Basic Info */}
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className={lbl}>Company Name *</label>
              <input className={inp} value={form.name} onChange={(e) => set("name", e.target.value)} required data-testid="operator-name-input" />
            </div>
            <div>
              <label className={lbl}>Short Code *</label>
              <input className={inp} value={form.code} onChange={(e) => handleCodeChange(e.target.value)} required maxLength={10} placeholder="e.g. BSNL" data-testid="operator-code-input" />
            </div>
            <div>
              <label className={lbl}>Contact Email *</label>
              <input className={inp} type="email" value={form.contact_email} onChange={(e) => set("contact_email", e.target.value)} required />
            </div>
            <div>
              <label className={lbl}>Phone</label>
              <input className={inp} value={form.contact_phone} onChange={(e) => set("contact_phone", e.target.value)} />
            </div>
            <div>
              <label className={lbl}>Status</label>
              <select className={inp} value={form.is_active ? "true" : "false"} onChange={(e) => set("is_active", e.target.value === "true")}>
                <option value="true">Active</option>
                <option value="false">Inactive</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className={lbl}>Address</label>
              <input className={inp} value={form.address} onChange={(e) => set("address", e.target.value)} />
            </div>
          </div>

          {/* ACS Credentials */}
          <div className="border-2 border-[#002FA7]/20 bg-blue-50/30 p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Key size={14} className="text-[#002FA7]" />
              <p className="text-xs uppercase tracking-[0.15em] font-bold text-[#002FA7] font-heading">Router ACS Credentials</p>
            </div>
            <p className="text-xs text-gray-500 font-body">Configure these in every router's CWMP settings under this operator. The ACS auto-assigns the router to this operator on first connect.</p>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={lbl}>ACS Username</label>
                <input
                  className={inp + " bg-white"}
                  value={form.acs_username}
                  onChange={(e) => handleAcsUserChange(e.target.value)}
                  placeholder="auto from code"
                />
              </div>
              <div>
                <label className={lbl}>ACS Password</label>
                <div className="flex gap-1">
                  <div className="relative flex-1">
                    <input
                      className={inp + " bg-white pr-8"}
                      type={showPass ? "text" : "password"}
                      value={form.acs_password}
                      onChange={(e) => set("acs_password", e.target.value)}
                    />
                    <button type="button" className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                      onClick={() => setShowPass(!showPass)}>
                      {showPass ? <EyeSlash size={13} /> : <Eye size={13} />}
                    </button>
                  </div>
                  <button type="button" title="Regenerate password"
                    className="px-2 border border-[#E6E8EB] bg-white hover:bg-gray-50 text-gray-500 hover:text-[#002FA7]"
                    onClick={() => set("acs_password", genPassword())}>
                    <ArrowsClockwise size={13} />
                  </button>
                </div>
              </div>
            </div>

            {/* CWMP Setup Reference Card */}
            <div className="bg-[#0A0B0D] text-green-400 font-mono text-[11px] p-3 space-y-1.5 mt-1">
              <p className="text-gray-400 text-[10px] uppercase tracking-wider mb-2">TP-Link / Any Router — CWMP Settings</p>
              {[
                { label: "CWMP", value: "Enable (toggle ON)" },
                { label: "Inform", value: "Enable (toggle ON)" },
                { label: "Inform Interval", value: "300  (seconds)" },
                { label: "ACS URL", value: cwmpUrl, key: "url" },
                { label: "ACS Username", value: form.acs_username || "<set code above>", key: "user" },
                { label: "ACS Password", value: showPass ? (form.acs_password || "…") : "••••••••", key: "pass" },
              ].map(({ label, value, key }) => (
                <div key={label} className="flex items-center gap-2">
                  <span className="text-gray-500 w-32 shrink-0">{label}</span>
                  <span className="text-green-300 flex-1 truncate">{value}</span>
                  {key && (
                    <button type="button" className="text-gray-600 hover:text-green-400 shrink-0"
                      onClick={() => copyToClipboard(key === "url" ? cwmpUrl : key === "user" ? form.acs_username : form.acs_password, key)}>
                      {copied === key ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm border border-[#E6E8EB] hover:bg-gray-50 font-body">Cancel</button>
            <button type="submit" disabled={loading} className="px-6 py-2 text-sm bg-[#002FA7] text-white font-semibold hover:bg-[#0035C4] disabled:opacity-60 font-body" data-testid="operator-submit-btn">
              {loading ? "Saving..." : operator ? "Update" : "Create Operator"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function UserModal({ targetUser, operators, currentUser, onClose, onSuccess }) {
  const [form, setForm] = useState(targetUser || {
    name: "", email: "", password: "", role: currentUser.role === "operator" ? "staff" : "operator",
    operator_id: currentUser.role === "operator" ? currentUser.operator_id : "",
  });
  const [resetMode, setResetMode] = useState(false);
  const [newPwd, setNewPwd] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (targetUser) {
        if (resetMode) {
          await axios.post(`${API}/users/${targetUser.id}/reset-password`, { new_password: newPwd }, { withCredentials: true });
        } else {
          await axios.put(`${API}/users/${targetUser.id}`, { name: form.name, email: form.email, is_active: form.is_active }, { withCredentials: true });
        }
      } else {
        await axios.post(`${API}/users`, form, { withCredentials: true });
      }
      onSuccess();
    } catch (err) { setError(err.response?.data?.detail || "Operation failed"); }
    setLoading(false);
  };

  const inp = "w-full border border-[#E6E8EB] px-3 py-2 text-sm focus:outline-none focus:border-[#002FA7] font-body";
  const lbl = "block text-xs uppercase tracking-[0.12em] font-semibold text-gray-500 mb-1 font-body";

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-lg">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E6E8EB]">
          <h2 className="text-lg font-bold font-heading">{targetUser ? `Edit User: ${targetUser.name}` : "Add User"}</h2>
          <button onClick={onClose}><X size={18} /></button>
        </div>
        {targetUser && (
          <div className="flex border-b border-[#E6E8EB]">
            <button className={`px-4 py-2 text-xs font-semibold font-body ${!resetMode ? "bg-white border-b-2 border-[#002FA7] text-[#002FA7]" : "text-gray-500 hover:bg-gray-50"}`} onClick={() => setResetMode(false)}>Edit Details</button>
            <button className={`px-4 py-2 text-xs font-semibold font-body flex items-center gap-1 ${resetMode ? "bg-white border-b-2 border-[#002FA7] text-[#002FA7]" : "text-gray-500 hover:bg-gray-50"}`} onClick={() => setResetMode(true)}><Key size={12} />Reset Password</button>
          </div>
        )}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && <div className="p-3 border border-[#E52B20] bg-red-50 text-sm text-[#E52B20]">{error}</div>}
          {!resetMode ? (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={lbl}>Full Name *</label>
                <input className={inp} value={form.name} onChange={(e) => set("name", e.target.value)} required data-testid="user-name-input" />
              </div>
              <div>
                <label className={lbl}>Email *</label>
                <input className={inp} type="email" value={form.email} onChange={(e) => set("email", e.target.value)} required data-testid="user-email-input" />
              </div>
              {!targetUser && (
                <div>
                  <label className={lbl}>Password *</label>
                  <input className={inp} type="password" value={form.password} onChange={(e) => set("password", e.target.value)} required minLength={6} data-testid="user-password-input" />
                </div>
              )}
              {currentUser.role === "super_admin" && !targetUser && (
                <>
                  <div>
                    <label className={lbl}>Role *</label>
                    <select className={inp} value={form.role} onChange={(e) => set("role", e.target.value)} data-testid="user-role-select">
                      <option value="operator">Operator Admin</option>
                      <option value="staff">Staff</option>
                      <option value="super_admin">Super Admin</option>
                    </select>
                  </div>
                  {form.role !== "super_admin" && (
                    <div>
                      <label className={lbl}>Operator</label>
                      <select className={inp} value={form.operator_id} onChange={(e) => set("operator_id", e.target.value)}>
                        <option value="">Select Operator</option>
                        {operators.map((op) => <option key={op.id} value={op.id}>{op.name}</option>)}
                      </select>
                    </div>
                  )}
                </>
              )}
              {targetUser && (
                <div>
                  <label className={lbl}>Status</label>
                  <select className={inp} value={form.is_active ? "true" : "false"} onChange={(e) => set("is_active", e.target.value === "true")}>
                    <option value="true">Active</option>
                    <option value="false">Inactive</option>
                  </select>
                </div>
              )}
            </div>
          ) : (
            <div>
              <label className={lbl}>New Password *</label>
              <input className={inp} type="password" value={newPwd} onChange={(e) => setNewPwd(e.target.value)} required minLength={6} />
            </div>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm border border-[#E6E8EB] hover:bg-gray-50 font-body">Cancel</button>
            <button type="submit" disabled={loading} className="px-6 py-2 text-sm bg-[#002FA7] text-white font-semibold hover:bg-[#0035C4] disabled:opacity-60 font-body" data-testid="user-submit-btn">
              {loading ? "Saving..." : targetUser ? (resetMode ? "Reset Password" : "Update") : "Create User"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function UserManagement() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState(user?.role === "operator" ? "users" : "operators");
  const [operators, setOperators] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOp, setModalOp] = useState(null);
  const [modalUser, setModalUser] = useState(null);
  const [showAddOp, setShowAddOp] = useState(false);
  const [showAddUser, setShowAddUser] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const calls = [];
      if (user?.role === "super_admin") calls.push(axios.get(`${API}/operators`, { withCredentials: true }));
      calls.push(axios.get(`${API}/users`, { withCredentials: true }));
      const results = await Promise.all(calls);
      if (user?.role === "super_admin") { setOperators(results[0].data); setUsers(results[1].data); }
      else setUsers(results[0].data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, []);

  const deleteOperator = async (op) => {
    if (!window.confirm(`Delete operator "${op.name}"?`)) return;
    try {
      await axios.delete(`${API}/operators/${op.id}`, { withCredentials: true });
      fetchData();
    } catch (e) { alert(e.response?.data?.detail || "Delete failed"); }
  };

  const deleteUser = async (u) => {
    if (!window.confirm(`Delete user "${u.name}"?`)) return;
    try {
      await axios.delete(`${API}/users/${u.id}`, { withCredentials: true });
      fetchData();
    } catch (e) { alert(e.response?.data?.detail || "Delete failed"); }
  };

  const visibleTabs = TABS.filter((t) => t.roles.includes(user?.role));

  return (
    <div className="fade-in">
      <div className="px-6 md:px-8 py-6 border-b border-[#E6E8EB]">
        <p className="text-xs uppercase tracking-[0.2em] font-semibold text-gray-400 mb-0.5 font-body">Administration</p>
        <h1 className="text-2xl font-black text-[#0A0B0D] font-heading">User Management</h1>
      </div>

      <div className="border-b border-[#E6E8EB] px-6 md:px-8 flex">
        {visibleTabs.map(({ id, label, icon: Icon }) => (
          <button key={id} className={`flex items-center gap-1.5 px-4 py-3 text-xs font-semibold uppercase tracking-wider border-b-2 transition-colors font-body ${activeTab === id ? "border-[#002FA7] text-[#002FA7]" : "border-transparent text-gray-500 hover:text-gray-800"}`}
            onClick={() => setActiveTab(id)} data-testid={`tab-${id}`}>
            <Icon size={14} />{label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="p-12 flex justify-center"><div className="w-8 h-8 border-2 border-[#002FA7] border-t-transparent rounded-full animate-spin"></div></div>
      ) : (
        <div className="p-6 md:p-8">
          {/* OPERATORS TAB */}
          {activeTab === "operators" && (
            <div>
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-sm font-bold font-heading">{operators.length} Operators</h2>
                <button className="flex items-center gap-2 bg-[#002FA7] text-white px-4 py-2 text-sm font-semibold hover:bg-[#0035C4]" onClick={() => setShowAddOp(true)} data-testid="add-operator-button">
                  <Plus size={14} /> Add Operator
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="data-table w-full">
                  <thead>
                    <tr><th>Status</th><th>Operator</th><th>Code</th><th>ACS User</th><th>Devices</th><th>Staff</th><th className="text-right">Actions</th></tr>
                  </thead>
                  <tbody>
                    {operators.map((op) => (
                      <tr key={op.id} data-testid={`operator-row-${op.id}`}>
                        <td>
                          <span className={`inline-flex items-center gap-1 text-[10px] font-semibold uppercase px-2 py-0.5 ${op.is_active ? "status-online" : "status-offline"}`}>
                            {op.is_active ? <CheckCircle size={10} /> : <XCircle size={10} />}
                            {op.is_active ? "Active" : "Inactive"}
                          </span>
                        </td>
                        <td>
                          <p className="text-sm font-semibold font-heading">{op.name}</p>
                          <p className="text-xs text-gray-400 font-body">{op.contact_email}</p>
                        </td>
                        <td><span className="font-mono text-xs font-bold text-[#002FA7]">{op.code}</span></td>
                        <td>
                          <span className="font-mono text-xs text-gray-600 bg-gray-100 px-1.5 py-0.5">{op.acs_username || "—"}</span>
                        </td>
                        <td><span className="text-xs font-mono font-bold">{op.device_count || 0}</span></td>
                        <td><span className="text-xs font-mono font-bold">{op.staff_count || 0}</span></td>
                        <td>
                          <div className="flex items-center justify-end gap-2">
                            <button className="p-1.5 border border-[#E6E8EB] hover:border-[#002FA7] hover:text-[#002FA7] text-gray-400 transition-colors" onClick={() => setModalOp(op)} data-testid={`edit-operator-${op.id}`}><PencilSimple size={13} /></button>
                            <button className="p-1.5 border border-[#E6E8EB] hover:border-[#E52B20] hover:text-[#E52B20] text-gray-400 transition-colors" onClick={() => deleteOperator(op)} data-testid={`delete-operator-${op.id}`}><Trash size={13} /></button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {operators.length === 0 && <tr><td colSpan={7} className="text-center py-8 text-gray-400 text-sm font-body">No operators yet.</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* USERS TAB */}
          {activeTab === "users" && (
            <div>
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-sm font-bold font-heading">{users.length} Users</h2>
                <button className="flex items-center gap-2 bg-[#002FA7] text-white px-4 py-2 text-sm font-semibold hover:bg-[#0035C4]" onClick={() => setShowAddUser(true)} data-testid="add-user-button">
                  <Plus size={14} /> Add User
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="data-table w-full">
                  <thead>
                    <tr><th>Status</th><th>User</th><th>Role</th>{user?.role === "super_admin" && <th>Operator</th>}<th>Created</th><th className="text-right">Actions</th></tr>
                  </thead>
                  <tbody>
                    {users.map((u) => (
                      <tr key={u.id} data-testid={`user-row-${u.id}`}>
                        <td>
                          <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 ${u.is_active !== false ? "status-online" : "status-offline"}`}>
                            {u.is_active !== false ? "Active" : "Inactive"}
                          </span>
                        </td>
                        <td>
                          <p className="text-sm font-semibold font-heading">{u.name}</p>
                          <p className="text-xs text-gray-400 font-body">{u.email}</p>
                        </td>
                        <td>
                          <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 font-mono ${
                            u.role === "super_admin" ? "bg-[#002FA7] text-white" :
                            u.role === "operator" ? "bg-[#00A153] text-white" :
                            "bg-gray-200 text-gray-700"
                          }`}>{u.role}</span>
                        </td>
                        {user?.role === "super_admin" && <td><span className="text-xs font-body">{u.operator_name || "—"}</span></td>}
                        <td><span className="text-xs text-gray-400 font-mono">{u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}</span></td>
                        <td>
                          <div className="flex items-center justify-end gap-2">
                            <button className="p-1.5 border border-[#E6E8EB] hover:border-[#002FA7] hover:text-[#002FA7] text-gray-400 transition-colors" onClick={() => setModalUser(u)} data-testid={`edit-user-${u.id}`}><PencilSimple size={13} /></button>
                            <button className="p-1.5 border border-[#E6E8EB] hover:border-[#E52B20] hover:text-[#E52B20] text-gray-400 transition-colors" onClick={() => deleteUser(u)} data-testid={`delete-user-${u.id}`}><Trash size={13} /></button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {users.length === 0 && <tr><td colSpan={6} className="text-center py-8 text-gray-400 text-sm font-body">No users yet.</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {(showAddOp || modalOp) && (
        <OperatorModal operator={modalOp} onClose={() => { setShowAddOp(false); setModalOp(null); }} onSuccess={() => { setShowAddOp(false); setModalOp(null); fetchData(); }} />
      )}
      {(showAddUser || modalUser) && (
        <UserModal targetUser={modalUser} operators={operators} currentUser={user} onClose={() => { setShowAddUser(false); setModalUser(null); }} onSuccess={() => { setShowAddUser(false); setModalUser(null); fetchData(); }} />
      )}
    </div>
  );
}
