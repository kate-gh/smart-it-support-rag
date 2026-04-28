// LoginModal.jsx
import { useState } from "react";
import { Lock, User, Eye, EyeOff, X, LogIn } from "lucide-react";

const API = "http://localhost:5000";

export default function LoginModal({ lang, onLogin, onClose }) {
  const fr = lang === "fr";
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPwd, setShowPwd] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const inputStyle = {
    width: "100%",
    padding: "9px 12px 9px 36px",
    background: "#111e35",
    border: "1px solid #1a2a42",
    borderRadius: 8,
    color: "#e2e8f0",
    fontSize: 14,
    outline: "none",
    fontFamily: "inherit",
  };

  async function submit() {
    if (!username || !password) return;
    setLoading(true);
    setError("");
    try {
      const r = await fetch(`${API}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (r.ok) {
          const userData = await r.json();
          // Stocker le token
          if (userData.token) {
              localStorage.setItem("auth_token", userData.token);
          }
          onLogin(userData);
          localStorage.setItem("user", JSON.stringify(userData));
      } else {
        setError(fr ? "Identifiants incorrects." : "Invalid credentials.");
      }
    } catch {
      setError(fr ? "Erreur de connexion." : "Connection error.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.7)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 999,
      }}
    >
      <div
        style={{
          background: "#0d1526",
          border: "1px solid #1a2a42",
          borderRadius: 14,
          padding: 28,
          width: 320,
          boxShadow: "0 8px 40px rgba(0,0,0,.8)",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 20,
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Lock size={15} color="#2563eb" />
              <span style={{ fontSize: 16, fontWeight: 700, color: "#e2e8f0" }}>
                {fr ? "Connexion" : "Login"}
              </span>
            </div>
            <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
              {fr
                ? "Connectez-vous pour accéder aux fonctionnalités"
                : "Sign in to access all features"}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "#64748b",
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Username field */}
        <div style={{ marginBottom: 14 }}>
          <div
            style={{
              fontSize: 11,
              color: "#64748b",
              marginBottom: 5,
              fontFamily: "monospace",
            }}
          >
            {fr ? "Nom d'utilisateur" : "Username"}
          </div>
          <div style={{ position: "relative" }}>
            <User
              size={13}
              color="#64748b"
              style={{
                position: "absolute",
                left: 11,
                top: "50%",
                transform: "translateY(-50%)",
              }}
            />
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              style={inputStyle}
            />
          </div>
        </div>

        {/* Password field */}
        <div style={{ marginBottom: 14 }}>
          <div
            style={{
              fontSize: 11,
              color: "#64748b",
              marginBottom: 5,
              fontFamily: "monospace",
            }}
          >
            {fr ? "Mot de passe" : "Password"}
          </div>
          <div style={{ position: "relative" }}>
            <Lock
              size={13}
              color="#64748b"
              style={{
                position: "absolute",
                left: 11,
                top: "50%",
                transform: "translateY(-50%)",
              }}
            />
            <input
              type={showPwd ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              style={{ ...inputStyle, paddingRight: 36 }}
            />
            <button
              onClick={() => setShowPwd((s) => !s)}
              style={{
                position: "absolute",
                right: 10,
                top: "50%",
                transform: "translateY(-50%)",
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "#64748b",
                padding: 0,
              }}
            >
              {showPwd ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          </div>
        </div>

        {error && (
          <div style={{ fontSize: 12, color: "#ef4444", marginBottom: 12 }}>
            {error}
          </div>
        )}

        <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
          <button
            onClick={submit}
            disabled={loading}
            style={{
              flex: 1,
              padding: "9px 0",
              background: loading
                ? "#1a2a42"
                : "linear-gradient(135deg,#2563eb,#7c3aed)",
              border: "none",
              borderRadius: 8,
              color: "#fff",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6,
            }}
          >
            {loading ? (
              "…"
            ) : (
              <>
                <LogIn size={13} />
                {fr ? "Se connecter" : "Login"}
              </>
            )}
          </button>
          <button
            onClick={onClose}
            style={{
              padding: "9px 16px",
              background: "#111e35",
              border: "1px solid #1a2a42",
              borderRadius: 8,
              color: "#64748b",
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            {fr ? "Annuler" : "Cancel"}
          </button>
        </div>

        <div
          style={{
            fontSize: 10,
            color: "#2a3a50",
            marginTop: 14,
            textAlign: "center",
            fontFamily: "monospace",
          }}
        >
          demo: admin / admin123
        </div>
      </div>
    </div>
  );
}
