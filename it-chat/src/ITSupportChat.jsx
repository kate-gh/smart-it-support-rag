import { useState, useRef, useEffect } from "react";
import AutoLearnBanner from "./AutoLearnBanner";
import LoginModal from "./LoginModal";
import ConfirmAddModal from "./ConfirmAddModal";
import UserMenu from "./UserMenu";
import AdminDashboard from "./AdminDashboard";

const API = "http://localhost:5000";

// ── Palette ───────────────────────────────────────────────
const C = {
  bg: "#070c18",
  surface: "#0d1526",
  hi: "#111e35",
  border: "#1a2a42",
  borderHi: "#253b5c",
  accent: "#2563eb",
  glow: "#3b82f6",
  soft: "#1a2e52",
  text: "#e2e8f0",
  muted: "#64748b",
  dim: "#2a3a50",
  red: "#ef4444",
  amber: "#f59e0b",
  green: "#10b981",
  violet: "#8b5cf6",
  orange: "#f97316",
};

const now = () =>
  new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

// ── Shared CSS injected once ──────────────────────────────
const CSS = `
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=DM+Sans:wght@400;500;600;700&display=swap');
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:${C.bg}}
  ::-webkit-scrollbar{width:3px}
  ::-webkit-scrollbar-thumb{background:${C.border};border-radius:2px}
  @keyframes fadeUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
  @keyframes slideRight{from{opacity:0;transform:translateX(-10px)}to{opacity:1;transform:translateX(0)}}
  @keyframes bounce{0%,80%,100%{transform:translateY(0);opacity:.35}40%{transform:translateY(-7px);opacity:1}}
  @keyframes spin{to{transform:rotate(360deg)}}
  @keyframes glow{0%,100%{box-shadow:0 0 0 0 rgba(37,99,235,.4)}50%{box-shadow:0 0 0 8px rgba(37,99,235,0)}}
  @keyframes toast{0%{opacity:0;transform:translateX(-50%) translateY(-8px)}100%{opacity:1;transform:translateX(-50%) translateY(0)}}
  textarea{resize:none;outline:none;border:none}
  button{cursor:pointer}
`;

// ── Badges ────────────────────────────────────────────────
const PBadge = ({ p }) => {
  const m = {
    high: [C.red, "HIGH"],
    medium: [C.amber, "MED"],
    low: [C.green, "LOW"],
  }[p?.toLowerCase()] || [C.muted, "—"];
  return (
    <span
      style={{
        fontFamily: "IBM Plex Mono,monospace",
        fontSize: 9,
        fontWeight: 600,
        color: m[0],
        letterSpacing: ".08em",
        display: "inline-flex",
        alignItems: "center",
        gap: 3,
      }}
    >
      <span
        style={{
          width: 5,
          height: 5,
          borderRadius: "50%",
          background: m[0],
          display: "inline-block",
        }}
      />
      {m[1]}
    </span>
  );
};

const TBadge = ({ t }) => {
  const m = {
    kb: [C.soft, C.glow, "KB"],
    llm_fallback: ["#2d1b6e", C.violet, "AI"],
    ticket: ["#2a1200", C.orange, "INC"],
    error: ["#1a0000", C.red, "ERR"],
    out_scope: [C.hi, C.muted, "OOB"],
  }[t] || [C.hi, C.muted, t?.toUpperCase() || "—"];
  return (
    <span
      style={{
        fontFamily: "IBM Plex Mono,monospace",
        fontSize: 9,
        fontWeight: 700,
        letterSpacing: ".1em",
        padding: "2px 6px",
        borderRadius: 3,
        background: m[0],
        color: m[1],
      }}
    >
      {m[2]}
    </span>
  );
};

// ── Typing dots ───────────────────────────────────────────
const Dots = () => (
  <div style={{ display: "flex", gap: 5, padding: "6px 0" }}>
    {[0, 1, 2].map((i) => (
      <span
        key={i}
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: C.glow,
          display: "inline-block",
          animation: `bounce 1.2s ease ${i * 0.2}s infinite`,
        }}
      />
    ))}
  </div>
);

// ── Avatar ────────────────────────────────────────────────
const Avatar = ({ active }) => (
  <div
    style={{
      flexShrink: 0,
      width: 32,
      height: 32,
      borderRadius: "50%",
      background: `linear-gradient(135deg,${C.accent},#7c3aed)`,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: 15,
      boxShadow: active ? `0 0 0 2px ${C.bg},0 0 0 4px ${C.accent}` : "none",
      transition: "box-shadow .3s",
    }}
  >
    🤖
  </div>
);

// ── Message ───────────────────────────────────────────────
const Msg = ({ msg, isLast }) => {
  if (msg.role === "user")
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          marginBottom: 16,
          animation: "fadeUp .25s ease",
        }}
      >
        <div
          style={{
            maxWidth: "72%",
            background: `linear-gradient(135deg,${C.accent},#1d4ed8)`,
            borderRadius: "14px 14px 3px 14px",
            padding: "10px 15px",
            fontSize: 14,
            color: "#fff",
            lineHeight: 1.65,
            boxShadow: `0 3px 16px rgba(37,99,235,.3)`,
          }}
        >
          {msg.content}
        </div>
      </div>
    );

  const lines = (msg.content || "").split("\n").filter(Boolean);

  return (
    <div
      style={{
        display: "flex",
        gap: 10,
        marginBottom: 20,
        animation: "fadeUp .3s ease",
      }}
    >
      <Avatar active={isLast} />
      <div style={{ flex: 1, minWidth: 0 }}>
        {/* meta row */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 7,
            marginBottom: 5,
            flexWrap: "wrap",
          }}
        >
          <span
            style={{
              fontSize: 12,
              fontWeight: 700,
              color: C.text,
              fontFamily: "IBM Plex Mono,monospace",
            }}
          >
            IT Assistant
          </span>
          {msg.type && <TBadge t={msg.type} />}
          {msg.category && (
            <span
              style={{
                fontSize: 10,
                color: C.muted,
                fontFamily: "IBM Plex Mono,monospace",
              }}
            >
              {msg.category}
            </span>
          )}
          {msg.priority && <PBadge p={msg.priority} />}
        </div>
        {/* bubble */}
        <div
          style={{
            background: C.hi,
            border: `1px solid ${C.border}`,
            borderRadius: "3px 14px 14px 14px",
            padding: "12px 15px",
            color: C.text,
            fontSize: 14,
            lineHeight: 1.7,
          }}
        >
          {lines.map((ln, i) => {
            const step = ln.match(/^(\d+)\.\s(.+)/);
            if (step)
              return (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    gap: 9,
                    marginBottom: 9,
                    animation: `slideRight .3s ease ${i * 0.07}s both`,
                  }}
                >
                  <span
                    style={{
                      flexShrink: 0,
                      width: 20,
                      height: 20,
                      borderRadius: "50%",
                      background: C.soft,
                      border: `1px solid ${C.accent}`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 9,
                      fontWeight: 700,
                      color: C.glow,
                      fontFamily: "IBM Plex Mono,monospace",
                      marginTop: 2,
                    }}
                  >
                    {step[1]}
                  </span>
                  <span style={{ flex: 1 }}>{step[2]}</span>
                </div>
              );
            const ticket = ln.match(/(INC\d+)/);
            if (ticket)
              return (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 9,
                    background: "#180d00",
                    border: `1px solid ${C.orange}33`,
                    borderRadius: 8,
                    padding: "8px 11px",
                    marginTop: 6,
                  }}
                >
                  <span style={{ fontSize: 17 }}>🎫</span>
                  <div>
                    <div
                      style={{
                        fontSize: 11,
                        fontWeight: 700,
                        color: C.orange,
                        fontFamily: "IBM Plex Mono,monospace",
                      }}
                    >
                      {ticket[1]}
                    </div>
                    <div style={{ fontSize: 11, color: C.muted, marginTop: 1 }}>
                      {ln.replace(ticket[1], "").trim()}
                    </div>
                  </div>
                </div>
              );
            return (
              <p key={i} style={{ margin: "0 0 3px" }}>
                {ln}
              </p>
            );
          })}
        </div>
        <div
          style={{
            fontSize: 10,
            color: C.dim,
            marginTop: 3,
            fontFamily: "IBM Plex Mono,monospace",
          }}
        >
          {msg.time}
        </div>
      </div>
    </div>
  );
};

// ── Chip ──────────────────────────────────────────────────
const Chip = ({ label, onClick }) => {
  const [hov, setHov] = useState(false);
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        padding: "4px 11px",
        borderRadius: 20,
        background: hov ? C.soft : C.hi,
        border: `1px solid ${hov ? C.accent : C.border}`,
        color: hov ? C.text : C.muted,
        fontSize: 11,
        fontFamily: "IBM Plex Mono,monospace",
        transition: "all .15s",
      }}
    >
      {label}
    </button>
  );
};

// ── Main ──────────────────────────────────────────────────
export default function ITSupportChat() {
  const [showAdmin, setShowAdmin] = useState(false);
  const [user, setUser] = useState(null);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [lang, setLang] = useState("en");
  const [tickets, setTickets] = useState([]);
  const [showTix, setShowTix] = useState(false);
  const [toast, setToast] = useState(null);
  const [feedback, setFeedback] = useState(false);
  const [lastFB, setLastFB] = useState(null);
  const [bannerMsgIndex, setBannerMsgIndex] = useState(null);
  const [lastFallback, setLastFallback] = useState(null);
  const [status, setStatus] = useState("idle");
  const [sessionId] = useState(() => crypto.randomUUID());
  const bottom = useRef(null);
  const inp = useRef(null);

  const statusTxt = {
    idle: lang === "fr" ? "En ligne" : "Online",
    think: lang === "fr" ? "Analyse…" : "Analyzing…",
    type: lang === "fr" ? "Rédaction…" : "Typing…",
  }[status];

  useEffect(() => {
    setMsgs([
      {
        role: "agent",
        content:
          lang === "fr"
            ? "Bonjour ! Je suis votre assistant IT self-service. Comment puis-je vous aider ?"
            : "Hello! I'm your IT self-service assistant. How can I help you today?",
        type: "kb",
        time: now(),
      },
    ]);
  }, []);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs, loading]);

  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    const savedUser = localStorage.getItem("user");

    if (token && savedUser) {
      setUser(JSON.parse(savedUser));
    }
  }, []);

  const CHIPS = {
    fr: [
      "Mot de passe expiré",
      "VPN ne fonctionne pas",
      "Imprimante HS",
      "Besoin technicien",
    ],
    en: [
      "Password expired",
      "VPN not connecting",
      "Printer not working",
      "Need a technician",
    ],
  };

  if (showAdmin) {

    // 🔒 pas connecté
    if (!user) {
      return (
        <div style={{ color: "white", padding: 20 }}>
          Please login first
        </div>
      );
    }

    // 🔒 pas admin
    if (user.role !== "admin") {
      return (
        <div style={{ color: "red", padding: 20 }}>
          Access denied — admin only
        </div>
      );
    }

    // ✅ autorisé
    return (
      <AdminDashboard
        user={user}
        lang={lang}
        onBack={() => setShowAdmin(false)}
      />
    );
  }

  async function fetchWithAuth(url, options = {}) {
    const res = await fetch(url, {
      ...options,
      headers: {
        ...authHeaders(),
        ...(options.headers || {}),
      },
    });

    if (res.status === 401) {
      localStorage.removeItem("auth_token");
      alert("Session expirée");
      window.location.reload();
      return null;
    }

    return res.json();
  }

  function authHeaders() {
    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${localStorage.getItem("auth_token") || ""}`,
    };
  }

  async function send() {
    if (!input.trim() || loading) return;
    const txt = input.trim();
    setInput("");
    setMsgs((p) => [...p, { role: "user", content: txt, time: now() }]);
    setLoading(true);
    setStatus("think");
    setFeedback(false);

    try {
      const d = await fetchWithAuth(`${API}/chat`, {
        method: "POST",
        body: JSON.stringify({
          message: txt,
          lang: lang,
          session_id: sessionId,
          user_id: user?.user_id || null,
          is_logged: !!user,
        }),
      });

      if (!d) return;
      setStatus("type");
      await new Promise((r) => setTimeout(r, 280));

      setMsgs((p) => [
        ...p,
        {
          role: "agent",
          content: d.response,
          type: d.type,
          category: d.category,
          priority: d.priority,
          time: now(),
        },
      ]);

      if (d.ticket_id) {
        const t = {
          ticket_id: d.ticket_id,
          category: d.category,
          priority: d.priority,
        };
        setTickets((p) => [...p, t]);
        setToast(t);
        setTimeout(() => setToast(null), 3500);
      }
      if (d.type === "llm_fallback") {
        setBannerMsgIndex(msgs.length);
        setLastFallback((prev) => ({
          // garder la question originale si elle existe déjà
          question:
            prev?.question && prev.question !== txt
              ? prev.question // garde l'ancienne question IT
              : txt, // première fois → prend txt
          answer: d.response,
          category: d.category,
          priority: d.priority,
        }));
      } else if (d.type === "kb") {
        // ✅ Quand KB répond → stocker la vraie question pour plus tard
        setLastFallback((prev) => ({
          ...prev,
          question: txt, // toujours garder la vraie question IT
        }));
        setBannerMsgIndex(null);
      }
    } catch {
      setMsgs((p) => [
        ...p,
        {
          role: "agent",
          type: "error",
          time: now(),
          content:
            lang === "fr"
              ? "Erreur de connexion. Vérifiez que le backend Flask tourne sur le port 5000."
              : "Connection error. Make sure the Flask backend is running on port 5000.",
        },
      ]);
    } finally {
      setLoading(false);
      setStatus("idle");
      inp.current?.focus();
    }
  }

  async function submitFeedback(helpful) {
    setBannerMsgIndex(null);

    if (helpful) {
      await fetchWithAuth(`${API}/feedback`, {
        method: "POST",
        body: JSON.stringify({ ...lastFallback, helpful: true }),
      });

      setMsgs((prev) => [
        ...prev,
        {
          role: "agent",
          type: "kb",
          time: now(),
          content:
            lang === "fr"
              ? "Réponse sauvegardée pour enrichir la base de connaissances. Merci !"
              : "Answer saved to improve the knowledge base. Thank you!",
        },
      ]);
    } else {
      const d = await fetchWithAuth(`${API}/ticket`, {
        method: "POST",
        body: JSON.stringify({
          summary: lastFallback.question,
          category: lastFallback.category || "IT Support",
          priority: lastFallback.priority || "medium",
        }),
      });
      if (!d) return;
      setTickets((prev) => [...prev, d]);

      setMsgs((prev) => [
        ...prev,
        {
          role: "agent",
          type: "ticket",
          time: now(),
          content:
            lang === "fr"
              ? `Ticket ${d.ticket_id} créé. L'équipe IT vous contactera dans ${d.delay}.`
              : `Ticket ${d.ticket_id} created. IT team will contact you within ${d.delay}.`,
        },
      ]);
    }

    setLastFallback(null);
  }

  async function confirmAdd() {
    setShowConfirmModal(false);

    await fetchWithAuth(`${API}/kb/add`, {
      method: "POST",
      body: JSON.stringify({
        ...lastFallback,
        user_id: user?.user_id,
      }),
    });

    setMsgs((prev) => [
      ...prev,
      {
        role: "agent",
        type: "kb",
        time: now(),
        content:
          lang === "fr"
            ? "Ajouté à la base de connaissances ✔"
            : "Added to knowledge base ✔",
      },
    ]);

    setLastFallback(null);
  }

  function handleAdd() {
    if (!user) {
      setShowLoginModal(true); // pas connecté → login d'abord
    } else {
      setShowConfirmModal(true); // connecté → confirm + étoiles
    }
  }

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        background: C.bg,
        color: C.text,
        fontFamily: "DM Sans,Segoe UI,sans-serif",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <style>{CSS}</style>

      {/* grid bg */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          backgroundImage: `linear-gradient(${C.border}12 1px,transparent 1px),linear-gradient(90deg,${C.border}12 1px,transparent 1px)`,
          backgroundSize: "48px 48px",
          zIndex: 0,
        }}
      />

      {/* ── HEADER ── */}
      <header
        style={{
          position: "relative",
          zIndex: 10,
          background: `${C.surface}f0`,
          backdropFilter: "blur(14px)",
          borderBottom: `1px solid ${C.border}`,
          padding: "11px 20px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background: `linear-gradient(135deg,${C.accent},#7c3aed)`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 18,
              boxShadow: `0 0 20px ${C.accent}40`,
            }}
          >
            🛡️
          </div>
          <div>
            <div
              style={{ fontSize: 15, fontWeight: 700, letterSpacing: "-.02em" }}
            >
              IT Self-Service
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                marginTop: 1,
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: status === "idle" ? C.green : C.amber,
                  display: "inline-block",
                  animation: status !== "idle" ? "glow 1.5s infinite" : "none",
                }}
              />
              <span
                style={{
                  fontSize: 10,
                  color: C.muted,
                  fontFamily: "IBM Plex Mono,monospace",
                }}
              >
                {statusTxt}
              </span>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
          {/* lang toggle — inchangé */}
          <div
            style={{
              display: "flex",
              background: C.hi,
              border: `1px solid ${C.border}`,
              borderRadius: 8,
              overflow: "hidden",
            }}
          >
            {["en", "fr"].map((l) => (
              <button
                key={l}
                onClick={() => setLang(l)}
                style={{
                  padding: "5px 13px",
                  background: lang === l ? C.accent : "transparent",
                  border: "none",
                  color: lang === l ? "#fff" : C.muted,
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: ".06em",
                  fontFamily: "IBM Plex Mono,monospace",
                  transition: "all .15s",
                }}
              >
                {l.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Tickets badge — inchangé */}
          {tickets.length > 0 && (
            <button
              onClick={() => setShowTix((s) => !s)}
              style={{
                position: "relative",
                background: showTix ? C.soft : C.hi,
                border: `1px solid ${showTix ? C.accent : C.border}`,
                borderRadius: 8,
                padding: "5px 12px",
                color: C.text,
                fontSize: 13,
                display: "flex",
                alignItems: "center",
                gap: 5,
              }}
            >
              🎫
              <span
                style={{
                  position: "absolute",
                  top: -5,
                  right: -5,
                  width: 17,
                  height: 17,
                  borderRadius: "50%",
                  background: C.orange,
                  fontSize: 9,
                  fontWeight: 700,
                  color: "#fff",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontFamily: "IBM Plex Mono,monospace",
                }}
              >
                {tickets.length}
              </span>
            </button>
          )}

          {/* UserMenu — NOUVEAU */}
          <UserMenu
            user={user}
            lang={lang}
            onLogin={() => setShowLoginModal(true)}
            onLogout={() => {
              localStorage.removeItem("auth_token");
              setUser(null);
              window.location.reload();
            }}
            onAdmin={() => setShowAdmin(true)}
          />
        </div>
      </header>

      {/* tickets dropdown */}
      {showTix && (
        <div
          style={{
            position: "absolute",
            top: 62,
            right: 16,
            zIndex: 100,
            background: C.surface,
            border: `1px solid ${C.border}`,
            borderRadius: 12,
            padding: 13,
            minWidth: 230,
            boxShadow: "0 8px 32px rgba(0,0,0,.6)",
            animation: "fadeUp .18s ease",
          }}
        >
          <div
            style={{
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: ".1em",
              color: C.muted,
              marginBottom: 9,
              fontFamily: "IBM Plex Mono,monospace",
            }}
          >
            TICKETS ({tickets.length})
          </div>
          {tickets.map((t, i) => (
            <div
              key={i}
              style={{
                padding: "8px 10px",
                background: C.hi,
                borderRadius: 8,
                marginBottom: 6,
                borderLeft: `3px solid ${C.orange}`,
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  color: C.orange,
                  fontFamily: "IBM Plex Mono,monospace",
                }}
              >
                {t.ticket_id}
              </div>
              <div style={{ fontSize: 11, color: C.muted, marginTop: 2 }}>
                {t.category} · {t.priority}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* toast */}
      {toast && (
        <div
          style={{
            position: "absolute",
            top: 70,
            left: "50%",
            transform: "translateX(-50%)",
            background: "#180d00",
            border: `1px solid ${C.orange}`,
            borderRadius: 10,
            padding: "9px 18px",
            display: "flex",
            alignItems: "center",
            gap: 10,
            zIndex: 200,
            boxShadow: "0 4px 24px rgba(0,0,0,.7)",
            animation: "toast .22s ease",
            whiteSpace: "nowrap",
          }}
        >
          <span style={{ fontSize: 18 }}>🎫</span>
          <div>
            <div
              style={{
                fontSize: 12,
                fontWeight: 700,
                color: C.orange,
                fontFamily: "IBM Plex Mono,monospace",
              }}
            >
              Ticket {toast.ticket_id}
            </div>
            <div style={{ fontSize: 11, color: C.muted }}>
              {toast.category} · {toast.priority}
            </div>
          </div>
        </div>
      )}

      {/* ── CHAT ── */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "22px 20px",
          position: "relative",
          zIndex: 1,
        }}
      >
        <div style={{ maxWidth: 700, margin: "0 auto" }}>
          {msgs.map((msg, i) => (
            <div key={i}>
              <Msg msg={msg} isLast={i === msgs.length - 1} />
              {bannerMsgIndex === i && (
                <AutoLearnBanner
                  lang={lang}
                  onYes={() => handleAdd()}
                  onNo={() => submitFeedback(false)}
                />
              )}
            </div>
          ))}
          {loading && (
            <div style={{ display: "flex", gap: 10, marginBottom: 20 }}>
              <Avatar active />
              <div
                style={{
                  background: C.hi,
                  border: `1px solid ${C.border}`,
                  borderRadius: "3px 14px 14px 14px",
                  padding: "8px 15px",
                }}
              >
                <Dots />
              </div>
            </div>
          )}
          <div ref={bottom} />
        </div>
      </div>

      {/* ── FEEDBACK ── */}
      {feedback && (
        <div
          style={{
            position: "relative",
            zIndex: 5,
            background: "#0a1020",
            borderTop: `1px solid ${C.border}`,
            padding: "10px 20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            animation: "fadeUp .2s ease",
          }}
        >
          <span style={{ fontSize: 13, color: C.muted }}>
            {lang === "fr"
              ? "Cette réponse a-t-elle résolu votre problème ?"
              : "Did this answer resolve your issue?"}
          </span>
          <div style={{ display: "flex", gap: 8 }}>
            {[
              {
                l: lang === "fr" ? "✓  Oui" : "✓  Yes",
                v: true,
                bg: C.soft,
                c: C.glow,
                b: C.accent,
              },
              {
                l: lang === "fr" ? "✕  Non" : "✕  No",
                v: false,
                bg: "#1a0808",
                c: C.red,
                b: C.red,
              },
            ].map((btn) => (
              <button
                key={btn.l}
                onClick={() => doFeedback(btn.v)}
                style={{
                  padding: "6px 16px",
                  background: btn.bg,
                  border: `1px solid ${btn.b}`,
                  borderRadius: 8,
                  color: btn.c,
                  fontSize: 12,
                  fontWeight: 600,
                  transition: "opacity .15s",
                }}
              >
                {btn.l}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── INPUT ── */}
      <div
        style={{
          position: "relative",
          zIndex: 5,
          background: `${C.surface}f0`,
          backdropFilter: "blur(14px)",
          borderTop: `1px solid ${C.border}`,
          padding: "14px 20px 18px",
        }}
      >
        <div style={{ maxWidth: 700, margin: "0 auto" }}>
          {/* chips */}
          <div
            style={{
              display: "flex",
              gap: 6,
              flexWrap: "wrap",
              marginBottom: 10,
            }}
          >
            {CHIPS[lang].map((c) => (
              <Chip
                key={c}
                label={c}
                onClick={() => {
                  setInput(c);
                  inp.current?.focus();
                }}
              />
            ))}
          </div>

          {/* row */}
          <div style={{ display: "flex", gap: 9, alignItems: "flex-end" }}>
            <div
              style={{
                flex: 1,
                background: C.hi,
                border: `1px solid ${C.borderHi}`,
                borderRadius: 14,
                padding: "10px 14px",
                display: "flex",
                alignItems: "flex-end",
                gap: 8,
              }}
            >
              <textarea
                ref={inp}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKey}
                placeholder={
                  lang === "fr"
                    ? "Décrivez votre problème IT…"
                    : "Describe your IT issue…"
                }
                rows={1}
                style={{
                  flex: 1,
                  background: "transparent",
                  color: C.text,
                  fontSize: 14,
                  lineHeight: 1.6,
                  fontFamily: "DM Sans,Segoe UI,sans-serif",
                  maxHeight: 110,
                  overflowY: "auto",
                }}
                onInput={(e) => {
                  e.target.style.height = "auto";
                  e.target.style.height =
                    Math.min(e.target.scrollHeight, 110) + "px";
                }}
              />
            </div>
            <button
              onClick={send}
              disabled={loading || !input.trim()}
              style={{
                width: 44,
                height: 44,
                borderRadius: 12,
                flexShrink: 0,
                background:
                  loading || !input.trim()
                    ? C.hi
                    : `linear-gradient(135deg,${C.accent},#7c3aed)`,
                border: `1px solid ${loading || !input.trim() ? C.border : "transparent"}`,
                color: loading || !input.trim() ? C.dim : "#fff",
                fontSize: loading ? "" : 18,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transition: "all .2s",
                boxShadow:
                  loading || !input.trim()
                    ? "none"
                    : `0 4px 18px ${C.accent}50`,
              }}
            >
              {loading ? (
                <span
                  style={{
                    width: 15,
                    height: 15,
                    borderRadius: "50%",
                    border: `2px solid ${C.dim}`,
                    borderTopColor: "transparent",
                    display: "inline-block",
                    animation: "spin .8s linear infinite",
                  }}
                />
              ) : (
                "↑"
              )}
            </button>
          </div>

          <div
            style={{
              textAlign: "center",
              marginTop: 7,
              fontSize: 10,
              color: C.dim,
              fontFamily: "IBM Plex Mono,monospace",
            }}
          >
            RAG · ChromaDB · Groq llama-3.3-70b ·{" "}
            {lang === "fr" ? "Entrée pour envoyer" : "Enter to send"}
          </div>
        </div>
      </div>

      {showLoginModal && (
        <LoginModal
          lang={lang}
          onLogin={(u) => {
            setUser(u);
            setShowLoginModal(false);
          }}
          onClose={() => setShowLoginModal(false)}
        />
      )}

      {showConfirmModal && lastFallback && user && (
        <ConfirmAddModal
          lang={lang}
          fallback={lastFallback}
          user={user}
          sessionId={sessionId}
          onDone={(result) => {
            setShowConfirmModal(false);
            if (result.status === "added") {
              setMsgs((p) => [
                ...p,
                {
                  role: "agent",
                  type: "kb",
                  time: now(),
                  content:
                    lang === "fr"
                      ? `✓ Ajouté à la KB (score IA: ${result.score}/5)`
                      : `✓ Added to KB (AI score: ${result.score}/5)`,
                },
              ]);
              setLastFallback(null);
              setBannerMsgIndex(null);
            }
          }}
          onClose={() => setShowConfirmModal(false)}
        />
      )}
    </div>
  );
}
