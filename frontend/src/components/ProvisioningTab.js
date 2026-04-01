import React, { useState } from "react";
import { Copy, Check, WifiHigh, Globe, Info } from "@phosphor-icons/react";

function CopyField({ label, value, mono = true, testId }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="flex items-stretch border border-[#E6E8EB]" data-testid={testId}>
      <div className="bg-[#F8F9FA] border-r border-[#E6E8EB] px-3 py-2.5 flex items-center min-w-[160px]">
        <span className="text-[11px] uppercase tracking-[0.12em] font-semibold text-gray-500 font-body">
          {label}
        </span>
      </div>
      <div className="flex-1 px-3 py-2.5 flex items-center min-w-0">
        <span className={`text-sm text-[#0A0B0D] truncate ${mono ? "font-mono" : "font-body"}`}>
          {value}
        </span>
      </div>
      <button
        onClick={handleCopy}
        className={`px-3 border-l border-[#E6E8EB] transition-colors flex items-center gap-1 text-xs font-semibold font-body ${
          copied ? "text-[#00A153] bg-green-50" : "text-gray-400 hover:text-[#002FA7] hover:bg-blue-50"
        }`}
        title="Copy to clipboard"
      >
        {copied ? <Check size={13} /> : <Copy size={13} />}
        {copied ? "Copied" : "Copy"}
      </button>
    </div>
  );
}

function SectionHeader({ icon: Icon, title, badge }) {
  return (
    <div className="flex items-center gap-2 mb-3 pb-2 border-b border-[#E6E8EB]">
      <Icon size={16} color="#002FA7" />
      <h3 className="text-sm font-bold font-heading text-[#0A0B0D]">{title}</h3>
      {badge && (
        <span className="ml-auto text-[10px] font-mono font-semibold uppercase px-2 py-0.5 bg-blue-50 text-[#002FA7] border border-blue-200">
          {badge}
        </span>
      )}
    </div>
  );
}

const TR069_ROUTER_GUIDES = [
  {
    brand: "Huawei (HG8245H / EG8145V5)",
    path: "Advanced → TR069 Management",
    note: "BSNL / MTNL routers",
  },
  {
    brand: "ZTE (F660 / F670L)",
    path: "Administration → TR069",
    note: "BSNL / ACT routers",
  },
  {
    brand: "Nokia / Alcatel (G-240G-A)",
    path: "Administration → Remote Management → TR-069",
    note: "Airtel routers",
  },
  {
    brand: "TP-Link (TD-W series / Archer VR)",
    path: "Management → TR-069",
    note: "Generic",
  },
  {
    brand: "D-Link (DSL / DWR series)",
    path: "Tools → TR-069 Client",
    note: "Generic / Jio",
  },
  {
    brand: "Sagemcom (F@ST series)",
    path: "Advanced Setup → TR-069",
    note: "Airtel / ACT",
  },
];

export default function ProvisioningTab({
  device, acsUrl, uspUrl, cwmpUser, cwmpPass, informInterval, settings,
}) {
  const [activeProto, setActiveProto] = useState(
    device?.protocol === "tr369" ? "tr369" : "tr069"
  );

  const tr069Enabled = settings?.tr069_enabled !== false;
  const tr369Enabled = settings?.tr369_enabled !== false;

  const cnxReqUrl = device?.ip_address
    ? `http://${device.ip_address}:7547/`
    : "(Device IP not set)";

  return (
    <div data-testid="provisioning-tab" className="max-w-3xl">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-lg font-bold font-heading">Provisioning Guide</h2>
        <p className="text-xs text-gray-500 font-body mt-1">
          Enter these settings in your router/CPE admin panel to connect it to this ACS server.
        </p>
      </div>

      {/* Protocol selector */}
      <div className="flex gap-0 mb-6 border border-[#E6E8EB]">
        {tr069Enabled && (
          <button
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-xs font-semibold uppercase tracking-wider transition-colors font-body ${
              activeProto === "tr069"
                ? "bg-[#002FA7] text-white"
                : "text-gray-500 hover:bg-gray-50"
            }`}
            onClick={() => setActiveProto("tr069")}
            data-testid="proto-tab-tr069"
          >
            <Globe size={14} />
            TR-069 (CWMP)
          </button>
        )}
        {tr369Enabled && (
          <button
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-xs font-semibold uppercase tracking-wider transition-colors font-body border-l border-[#E6E8EB] ${
              activeProto === "tr369"
                ? "bg-[#002FA7] text-white"
                : "text-gray-500 hover:bg-gray-50"
            }`}
            onClick={() => setActiveProto("tr369")}
            data-testid="proto-tab-tr369"
          >
            <WifiHigh size={14} />
            TR-369 (USP)
          </button>
        )}
      </div>

      {/* TR-069 Section */}
      {activeProto === "tr069" && (
        <div className="space-y-6">
          {/* ACS Server Settings */}
          <div className="border border-[#E6E8EB] p-4">
            <SectionHeader icon={Globe} title="ACS Server Settings" badge="Enter in router admin" />
            <div className="space-y-1.5">
              <CopyField label="ACS URL" value={acsUrl} testId="copy-acs-url" />
              <CopyField label="ACS Username" value={cwmpUser} testId="copy-cwmp-user" />
              <CopyField label="ACS Password" value={cwmpPass} testId="copy-cwmp-pass" />
              <CopyField label="Periodic Inform" value="Enable" mono={false} />
              <CopyField label="Inform Interval" value={`${informInterval}`} testId="copy-inform-interval" />
              <CopyField label="Connection Req. URL" value={cnxReqUrl} testId="copy-cnx-req-url" />
            </div>
          </div>

          {/* Device Info */}
          <div className="border border-[#E6E8EB] p-4">
            <SectionHeader icon={Globe} title="Device Identification" badge="Auto-detected" />
            <div className="space-y-1.5">
              <CopyField label="Serial Number" value={device?.serial_number || "(not set)"} testId="copy-serial" />
              <CopyField label="MAC Address" value={device?.mac_address || "(not set)"} />
              <CopyField label="Provision Code" value={device?.provision_code || "(not set)"} testId="copy-provision-code" />
            </div>
            <p className="text-xs text-gray-400 font-body mt-3 flex items-center gap-1">
              <Info size={11} />
              The router sends its Serial Number in the Inform message — it will be auto-matched to this device.
            </p>
          </div>

          {/* Raw config block */}
          <div className="border border-[#E6E8EB] p-4">
            <SectionHeader icon={Globe} title="Configuration Summary" />
            <div className="terminal-output text-[11px] leading-relaxed">{[
              `[TR-069 / CWMP Settings]`,
              ``,
              `ACS URL              : ${acsUrl}`,
              `ACS Username         : ${cwmpUser}`,
              `ACS Password         : ${cwmpPass}`,
              `Periodic Inform      : Enable`,
              `Inform Interval      : ${informInterval} seconds`,
              `Connection Req. URL  : ${cnxReqUrl}`,
              ``,
              `[Device Info]`,
              `Serial Number        : ${device?.serial_number || "(not set)"}`,
              `MAC Address          : ${device?.mac_address || "(not set)"}`,
              `Provision Code       : ${device?.provision_code || "(not set)"}`,
            ].join("\n")}</div>
          </div>

          {/* Router-specific guides */}
          <div className="border border-[#E6E8EB] p-4">
            <SectionHeader icon={Globe} title="Where to find TR-069 settings — by router brand" />
            <div className="space-y-0 divide-y divide-[#F0F2F4]">
              {TR069_ROUTER_GUIDES.map((g) => (
                <div key={g.brand} className="flex items-start gap-3 py-2.5">
                  <div className="w-1 h-1 rounded-full bg-[#002FA7] mt-1.5 flex-shrink-0"></div>
                  <div className="flex-1">
                    <p className="text-xs font-semibold font-heading text-[#0A0B0D]">{g.brand}</p>
                    <p className="text-xs text-gray-500 font-body">
                      Router Admin → <span className="font-mono text-[#002FA7]">{g.path}</span>
                    </p>
                  </div>
                  <span className="text-[10px] text-gray-400 font-body whitespace-nowrap">{g.note}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TR-369 Section */}
      {activeProto === "tr369" && (
        <div className="space-y-6">
          <div className="border border-[#E6E8EB] p-4">
            <SectionHeader icon={WifiHigh} title="USP Controller Settings" badge="Enter in router admin" />
            <div className="space-y-1.5">
              <CopyField label="Controller URL" value={uspUrl} testId="copy-usp-url" />
              <CopyField label="Endpoint ID" value={device?.serial_number || "(device serial number)"} testId="copy-endpoint-id" />
              <CopyField label="Protocol" value="REST / HTTP" mono={false} />
            </div>
          </div>

          <div className="border border-[#E6E8EB] p-4">
            <SectionHeader icon={WifiHigh} title="Configuration Summary" />
            <div className="terminal-output text-[11px] leading-relaxed">{[
              `[TR-369 / USP Settings]`,
              ``,
              `Controller URL  : ${uspUrl}`,
              `Endpoint ID     : ${device?.serial_number || "(device serial number)"}`,
              `Protocol        : REST / HTTP`,
              ``,
              `[Device Info]`,
              `Serial Number   : ${device?.serial_number || "(not set)"}`,
              `MAC Address     : ${device?.mac_address || "(not set)"}`,
            ].join("\n")}</div>
          </div>

          <div className="p-4 border border-yellow-200 bg-yellow-50 flex gap-3">
            <Info size={16} className="text-yellow-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-xs font-semibold text-yellow-800 font-body">TR-369 (USP) Notice</p>
              <p className="text-xs text-yellow-700 font-body mt-1">
                This ACS implements a simplified REST-based TR-369 registration endpoint. Full USP MQTT/WebSocket support can be added for production deployments.
                Supported on: Nokia G-240G-A (Airtel), ZTE F670L, TP-Link Archer VR900, ASUS DSL-AC68U.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
