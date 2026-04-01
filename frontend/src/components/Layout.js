import React, { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import {
  Gauge,
  HardDrives,
  Buildings,
  Users,
  GearSix,
  Network,
  WifiHigh,
  SignOut,
  CaretDown,
  CaretUp,
  UserCircle,
  ShieldCheck,
} from "@phosphor-icons/react";

const navConfig = {
  super_admin: [
    { path: "/dashboard", label: "Dashboard", icon: Gauge },
    { path: "/operators", label: "Operators", icon: Buildings },
    { path: "/devices", label: "Devices", icon: HardDrives },
    { path: "/users", label: "Users", icon: Users },
    { path: "/router-models", label: "Router Library", icon: Network },
    { path: "/settings", label: "Global Settings", icon: GearSix },
  ],
  operator: [
    { path: "/dashboard", label: "Dashboard", icon: Gauge },
    { path: "/devices", label: "Devices", icon: HardDrives },
    { path: "/users", label: "Staff", icon: Users },
    { path: "/router-models", label: "Router Library", icon: Network },
  ],
  staff: [
    { path: "/dashboard", label: "Dashboard", icon: Gauge },
    { path: "/devices", label: "Devices", icon: HardDrives },
    { path: "/router-models", label: "Router Library", icon: Network },
  ],
};

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const navItems = navConfig[user?.role] || navConfig.staff;

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const roleColors = {
    super_admin: "bg-[#002FA7] text-white",
    operator: "bg-[#00A153] text-white",
    staff: "bg-gray-600 text-white",
  };

  const roleLabels = {
    super_admin: "Super Admin",
    operator: "Operator",
    staff: "Staff",
  };

  return (
    <div className="flex min-h-screen bg-white">
      {/* Sidebar */}
      <aside className="w-60 flex-shrink-0 border-r border-[#E6E8EB] bg-[#FAFBFC] flex flex-col" style={{ position: "sticky", top: 0, height: "100vh" }}>
        {/* Logo */}
        <div className="px-4 py-5 border-b border-[#E6E8EB]">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-[#002FA7] flex items-center justify-center flex-shrink-0">
              <WifiHigh size={18} color="white" weight="bold" />
            </div>
            <div>
              <p className="text-sm font-bold text-[#0A0B0D] font-heading leading-none">ACS Server</p>
              <p className="text-[10px] text-gray-400 font-body mt-0.5 uppercase tracking-widest">India Platform</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-3 overflow-y-auto">
          <div className="px-3 mb-2">
            <p className="text-[10px] uppercase tracking-[0.15em] font-semibold text-gray-400 px-2 mb-1">Navigation</p>
          </div>
          {navItems.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) =>
                `sidebar-item ${isActive ? "active" : ""}`
              }
              data-testid={`nav-${label.toLowerCase().replace(/\s+/g, "-")}`}
            >
              <Icon size={16} weight="regular" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="border-t border-[#E6E8EB] p-3">
          <button
            className="w-full flex items-center gap-2 p-2 hover:bg-gray-100 transition-colors duration-150"
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            data-testid="user-menu-toggle"
          >
            <div className="w-8 h-8 bg-gray-200 flex items-center justify-center flex-shrink-0">
              <UserCircle size={20} color="#666" />
            </div>
            <div className="flex-1 text-left min-w-0">
              <p className="text-xs font-semibold text-gray-800 truncate font-heading">{user?.name}</p>
              <span className={`text-[9px] px-1.5 py-0.5 font-semibold uppercase tracking-wider ${roleColors[user?.role] || "bg-gray-200"}`}>
                {roleLabels[user?.role] || user?.role}
              </span>
            </div>
            {userMenuOpen ? <CaretUp size={12} /> : <CaretDown size={12} />}
          </button>

          {userMenuOpen && (
            <div className="mt-1 border border-[#E6E8EB] bg-white shadow-sm">
              <button
                className="w-full flex items-center gap-2 px-3 py-2 text-xs text-red-600 hover:bg-red-50 transition-colors"
                onClick={handleLogout}
                data-testid="logout-button"
              >
                <SignOut size={14} />
                Sign Out
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-w-0 overflow-auto">
        {children}
      </main>
    </div>
  );
}
