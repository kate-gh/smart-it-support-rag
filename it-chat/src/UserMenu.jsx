// UserMenu.jsx
import { useState } from "react";
import {
  User,
  LogIn,
  LogOut,
  LayoutDashboard,
  ChevronDown,
  Circle,
} from "lucide-react";

const C = {
  bg: "#070c18",
  surface: "#0d1526",
  hi: "#111e35",
  border: "#1a2a42",
  accent: "#2563eb",
  text: "#e2e8f0",
  muted: "#64748b",
  green: "#10b981",
};

export default function UserMenu({ user, lang, onLogin, onLogout, onAdmin }) {
  const fr = lang === "fr";
  const [open, setOpen] = useState(false);

  if (!user) {
    return (
      <button
        onClick={onLogin}
        style={{
          padding: "5px 14px",
          background: `linear-gradient(135deg,${C.accent},#7c3aed)`,
          border: "none",
          borderRadius: 8,
          color: "#fff",
          fontSize: 12,
          fontWeight: 600,
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 6,
        }}
      >
        <LogIn size={13} />
        {fr ? "Connexion" : "Login"}
      </button>
    );
  }

  return (
    <div style={{ position: "relative" }}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "5px 12px",
          background: open ? C.hi : "transparent",
          border: `1px solid ${open ? C.accent : C.border}`,
          borderRadius: 8,
          cursor: "pointer",
          transition: "all .15s",
        }}
      >
        <div
          style={{
            width: 22,
            height: 22,
            borderRadius: "50%",
            background:
              user.role === "admin"
                ? `linear-gradient(135deg,${C.accent},#7c3aed)`
                : C.hi,
            border: `1px solid ${C.border}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 10,
            fontWeight: 700,
            color: "#fff",
          }}
        >
          {user.username?.[0]?.toUpperCase()}
        </div>
        <span style={{ fontSize: 12, color: C.text, fontWeight: 600 }}>
          {user.username}
        </span>
        {user.role === "admin" && (
          <span
            style={{
              fontSize: 8,
              fontWeight: 700,
              fontFamily: "monospace",
              padding: "1px 5px",
              borderRadius: 3,
              background: C.accent + "33",
              color: C.accent,
            }}
          >
            ADMIN
          </span>
        )}
        <ChevronDown size={11} color={C.muted} />
      </button>

      {open && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 6px)",
            right: 0,
            background: C.surface,
            border: `1px solid ${C.border}`,
            borderRadius: 10,
            minWidth: 180,
            zIndex: 200,
            boxShadow: "0 8px 32px rgba(0,0,0,.6)",
            overflow: "hidden",
          }}
        >
          {/* User info */}
          <div
            style={{
              padding: "12px 14px",
              borderBottom: `1px solid ${C.border}`,
            }}
          >
            <div style={{ fontSize: 13, fontWeight: 700, color: C.text }}>
              {user.username}
            </div>
            <div
              style={{
                fontSize: 10,
                color: C.green,
                fontFamily: "monospace",
                marginTop: 2,
                display: "flex",
                alignItems: "center",
                gap: 4,
              }}
            >
              <Circle size={6} fill={C.green} color={C.green} />
              {fr ? "Connecté" : "Connected"} · {user.role}
            </div>
          </div>

          {user.role === "admin" && (
            <button
              onClick={() => {
                setOpen(false);
                onAdmin();
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                width: "100%",
                textAlign: "left",
                padding: "10px 14px",
                background: "transparent",
                border: "none",
                borderBottom: `1px solid ${C.border}`,
                color: C.accent,
                fontSize: 12,
                cursor: "pointer",
              }}
            >
              <LayoutDashboard size={13} />
              {fr ? "Tableau de bord admin" : "Admin dashboard"}
            </button>
          )}

          <button
            onClick={() => {
              setOpen(false);
              onLogout();
            }}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              width: "100%",
              textAlign: "left",
              padding: "10px 14px",
              background: "transparent",
              border: "none",
              color: "#ef4444",
              fontSize: 12,
              cursor: "pointer",
            }}
          >
            <LogOut size={13} />
            {fr ? "Déconnexion" : "Logout"}
          </button>
        </div>
      )}
    </div>
  );
}
