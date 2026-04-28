// AdminDashboard.jsx
import { useState, useEffect, useCallback } from "react";
import {
  ArrowLeft,
  RefreshCw,
  LayoutDashboard,
  Ticket,
  Users,
  Database,
  TrendingUp,
  TrendingDown,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Plus,
  Pencil,
  Trash2,
  Eye,
  ShieldCheck,
  User,
  X,
  Search,
  ChevronRight,
  Activity,
  Layers,
  Check,
} from "lucide-react";

const API = "http://localhost:5000";

const T = {
  bg: "#04080f",
  panel: "#080f1c",
  card: "#0b1420",
  hi: "#0f1c30",
  border: "#162030",
  borderHi: "#1e2f46",
  accent: "#0ea5e9",
  accent2: "#6366f1",
  text: "#e2eaf5",
  sub: "#8499b4",
  dim: "#3a4f66",
  red: "#f43f5e",
  amber: "#f59e0b",
  green: "#10b981",
  violet: "#8b5cf6",
  orange: "#f97316",
  cyan: "#22d3ee",
};

const PRIO_MAP = {
  high: { color: T.red, bg: "#f43f5e18", label: "HIGH" },
  medium: { color: T.amber, bg: "#f59e0b18", label: "MED" },
  low: { color: T.green, bg: "#10b98118", label: "LOW" },
};
const STATUS_MAP = {
  open: { color: T.amber, bg: "#f59e0b14", label: "OPEN" },
  in_progress: { color: T.cyan, bg: "#22d3ee14", label: "IN PROGRESS" },
  resolved: { color: T.green, bg: "#10b98114", label: "RESOLVED" },
  closed: { color: T.dim, bg: "#3a4f6614", label: "CLOSED" },
};

const CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500;700&family=Outfit:wght@300;400;500;600&display=swap');
  *{box-sizing:border-box;margin:0;padding:0}
  ::-webkit-scrollbar{width:3px;height:3px}
  ::-webkit-scrollbar-thumb{background:${T.border};border-radius:2px}
  @keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
  @keyframes slideIn{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:translateX(0)}}
  @keyframes scaleIn{from{opacity:0;transform:scale(.96)}to{opacity:1;transform:scale(1)}}
  @keyframes spin{to{transform:rotate(360deg)}}
  input,select,button{font-family:'Outfit',sans-serif}
  input::placeholder{color:${T.dim}}
`;

/* ── tiny helpers ── */
function Spinner() {
  return (
    <div
      style={{
        width: 15,
        height: 15,
        borderRadius: "50%",
        border: `2px solid ${T.border}`,
        borderTopColor: T.accent,
        animation: "spin .7s linear infinite",
        display: "inline-block",
      }}
    />
  );
}
function Mono({ children, color, size = 11 }) {
  return (
    <span
      style={{
        fontFamily: "'JetBrains Mono',monospace",
        fontSize: size,
        color: color || T.sub,
      }}
    >
      {children}
    </span>
  );
}
function Pill({ children, color, bg }) {
  return (
    <span
      style={{
        fontFamily: "'JetBrains Mono',monospace",
        fontSize: 9,
        fontWeight: 700,
        letterSpacing: ".07em",
        padding: "3px 8px",
        borderRadius: 5,
        color: color || T.sub,
        background: bg || (color ? color + "20" : T.hi),
      }}
    >
      {children}
    </span>
  );
}
function PrioTag({ p }) {
  const d = PRIO_MAP[p?.toLowerCase()] || {
    color: T.dim,
    bg: T.hi,
    label: (p || "—").toUpperCase(),
  };
  return (
    <Pill color={d.color} bg={d.bg}>
      {d.label}
    </Pill>
  );
}
function StatusTag({ s }) {
  const d = STATUS_MAP[s?.toLowerCase()] || {
    color: T.dim,
    bg: T.hi,
    label: (s || "OPEN").toUpperCase(),
  };
  return (
    <Pill color={d.color} bg={d.bg}>
      {d.label}
    </Pill>
  );
}
function Row({ children, style = {} }) {
  return (
    <div style={{ display: "flex", alignItems: "center", ...style }}>
      {children}
    </div>
  );
}

/* ── animated counter ── */
function Counter({ value }) {
  const [d, setD] = useState(0);
  useEffect(() => {
    const t0 = Date.now(),
      dur = 800;
    const f = () => {
      const p = Math.min((Date.now() - t0) / dur, 1);
      setD(Math.round(p * value));
      if (p < 1) requestAnimationFrame(f);
    };
    requestAnimationFrame(f);
  }, [value]);
  return <>{d}</>;
}

/* ── KPI card ── */
function KPICard({ icon: Icon, label, value, color, sub }) {
  return (
    <div
      style={{
        background: T.card,
        border: `1px solid ${T.border}`,
        borderRadius: 12,
        padding: "20px 22px",
        borderLeft: `3px solid ${color}`,
        position: "relative",
        overflow: "hidden",
        animation: "fadeIn .4s ease both",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: -20,
          right: -20,
          width: 80,
          height: 80,
          borderRadius: "50%",
          background: color,
          opacity: 0.06,
          filter: "blur(20px)",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 14,
        }}
      >
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: 9,
            background: color + "18",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Icon size={17} color={color} />
        </div>
      </div>
      <div
        style={{
          fontSize: 28,
          fontWeight: 800,
          color: T.text,
          fontFamily: "'Syne',sans-serif",
          lineHeight: 1,
        }}
      >
        <Counter value={value ?? 0} />
      </div>
      <div
        style={{ fontSize: 11, color: T.sub, marginTop: 5, fontWeight: 500 }}
      >
        {label}
      </div>
      {sub && (
        <div style={{ fontSize: 10, color: T.dim, marginTop: 3 }}>{sub}</div>
      )}
    </div>
  );
}

/* ── category bar chart ── */
function CatChart({ data, total }) {
  const entries = Object.entries(data || {});
  const colors = [
    T.accent,
    T.accent2,
    T.cyan,
    T.green,
    T.orange,
    T.violet,
    T.red,
    T.amber,
  ];
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 11 }}>
      {entries.map(([cat, count], i) => {
        const pct = total > 0 ? Math.round((count / total) * 100) : 0;
        const color = colors[i % colors.length];
        return (
          <div
            key={cat}
            style={{ animation: `slideIn .3s ease ${i * 0.06}s both` }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: 5,
              }}
            >
              <Row style={{ gap: 7 }}>
                <div
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: "50%",
                    background: color,
                  }}
                />
                <span style={{ fontSize: 11, color: T.text, fontWeight: 500 }}>
                  {cat.split(" ")[0]}
                </span>
              </Row>
              <Row style={{ gap: 8 }}>
                <Mono size={10}>{count}</Mono>
                <Mono size={10} color={T.dim}>
                  {pct}%
                </Mono>
              </Row>
            </div>
            <div
              style={{
                height: 5,
                background: T.hi,
                borderRadius: 3,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  borderRadius: 3,
                  background: `linear-gradient(90deg,${color},${color}88)`,
                  width: `${pct}%`,
                  transition: "width .6s cubic-bezier(.4,0,.2,1)",
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ── priority bar chart ── */
function PrioChart({ data }) {
  const entries = Object.entries(data || {});
  const maxV = Math.max(...entries.map(([, v]) => v), 1);
  const cm = { high: T.red, medium: T.amber, low: T.green };
  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-end",
        gap: 14,
        height: 90,
        paddingTop: 10,
      }}
    >
      {entries.map(([k, v]) => {
        const color = cm[k] || T.accent;
        const h = Math.max((v / maxV) * 70, 4);
        return (
          <div
            key={k}
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 5,
            }}
          >
            <Mono size={11} color={T.text}>
              {v}
            </Mono>
            <div
              style={{
                width: "100%",
                height: `${h}px`,
                background: `linear-gradient(180deg,${color},${color}70)`,
                borderRadius: "5px 5px 0 0",
                boxShadow: `0 0 10px ${color}44`,
                transition: "height .6s cubic-bezier(.4,0,.2,1)",
              }}
            />
            <Mono size={9} color={color}>
              {k.slice(0, 3).toUpperCase()}
            </Mono>
          </div>
        );
      })}
    </div>
  );
}

/* ── donut ── */
function Donut({ value, max, color, label, sub }) {
  const r = 38,
    circ = 2 * Math.PI * r,
    pct = max > 0 ? Math.min(value / max, 1) : 0,
    dash = pct * circ;
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 8,
      }}
    >
      <svg width={96} height={96} viewBox="0 0 96 96">
        <circle
          cx={48}
          cy={48}
          r={r}
          fill="none"
          stroke={T.hi}
          strokeWidth={10}
        />
        <circle
          cx={48}
          cy={48}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={10}
          strokeDasharray={`${dash} ${circ}`}
          strokeDashoffset={circ / 4}
          strokeLinecap="round"
          style={{ transition: "stroke-dasharray .8s cubic-bezier(.4,0,.2,1)" }}
        />
        <text
          x={48}
          y={44}
          textAnchor="middle"
          style={{
            fontSize: 13,
            fontWeight: 700,
            fill: T.text,
            fontFamily: "'JetBrains Mono',monospace",
          }}
        >
          {Math.round(pct * 100)}%
        </text>
        <text
          x={48}
          y={57}
          textAnchor="middle"
          style={{
            fontSize: 8,
            fill: T.sub,
            fontFamily: "'JetBrains Mono',monospace",
          }}
        >
          {sub}
        </text>
      </svg>
      <span
        style={{
          fontSize: 11,
          color: T.sub,
          fontWeight: 500,
          textAlign: "center",
        }}
      >
        {label}
      </span>
    </div>
  );
}

/* ── side nav ── */
function SideNav({ tab, setTab, counts, fr }) {
  const items = [
    {
      id: "overview",
      icon: LayoutDashboard,
      label: fr ? "Vue d'ensemble" : "Overview",
    },
    { id: "tickets", icon: Ticket, label: "Tickets", count: counts.tickets },
    {
      id: "users",
      icon: Users,
      label: fr ? "Utilisateurs" : "Users",
      count: counts.users,
    },
    {
      id: "pending",
      icon: Database,
      label: fr ? "KB en attente" : "Pending KB",
      count: counts.pending,
      dot: counts.pending > 0,
    },
  ];
  return (
    <nav
      style={{
        width: 205,
        flexShrink: 0,
        background: T.panel,
        borderRight: `1px solid ${T.border}`,
        display: "flex",
        flexDirection: "column",
        padding: "16px 10px",
        gap: 3,
      }}
    >
      <div style={{ padding: "6px 10px 14px" }}>
        <Mono size={9} color={T.dim}>
          NAVIGATION
        </Mono>
      </div>
      {items.map(({ id, icon: Icon, label, count, dot }) => {
        const active = tab === id;
        return (
          <button
            key={id}
            onClick={() => setTab(id)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "10px 12px",
              background: active ? T.accent + "18" : "transparent",
              border: `1px solid ${active ? T.accent + "44" : "transparent"}`,
              borderRadius: 9,
              color: active ? T.accent : T.sub,
              fontSize: 13,
              fontWeight: active ? 600 : 400,
              transition: "all .15s",
              width: "100%",
              textAlign: "left",
              cursor: "pointer",
            }}
            onMouseEnter={(e) => {
              if (!active) e.currentTarget.style.background = T.hi;
            }}
            onMouseLeave={(e) => {
              if (!active) e.currentTarget.style.background = "transparent";
            }}
          >
            <Icon size={14} style={{ flexShrink: 0 }} />
            <span style={{ flex: 1 }}>{label}</span>
            {count != null && count > 0 && (
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  fontFamily: "'JetBrains Mono',monospace",
                  padding: "1px 7px",
                  borderRadius: 10,
                  background: dot ? T.red + "22" : T.hi,
                  color: dot ? T.red : T.dim,
                }}
              >
                {count}
              </span>
            )}
          </button>
        );
      })}
    </nav>
  );
}

/* ── search ── */
function SearchBox({ value, onChange, placeholder }) {
  return (
    <div style={{ position: "relative" }}>
      <Search
        size={12}
        color={T.dim}
        style={{
          position: "absolute",
          left: 10,
          top: "50%",
          transform: "translateY(-50%)",
          pointerEvents: "none",
        }}
      />
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={{
          padding: "8px 12px 8px 30px",
          background: T.hi,
          border: `1px solid ${T.border}`,
          borderRadius: 9,
          color: T.text,
          fontSize: 12,
          width: 210,
          outline: "none",
          transition: "border-color .15s",
        }}
        onFocus={(e) => (e.target.style.borderColor = T.accent)}
        onBlur={(e) => (e.target.style.borderColor = T.border)}
      />
    </div>
  );
}

/* ── section header ── */
function SectionH({ title, sub, right }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        marginBottom: 18,
      }}
    >
      <div>
        <div
          style={{
            fontSize: 16,
            fontWeight: 700,
            color: T.text,
            fontFamily: "'Syne',sans-serif",
          }}
        >
          {title}
        </div>
        {sub && (
          <div style={{ fontSize: 11, color: T.sub, marginTop: 2 }}>{sub}</div>
        )}
      </div>
      {right}
    </div>
  );
}

/* ── ticket detail modal ── */
function TicketModal({ ticket, lang, onClose, onUpdate, fetchWithAuth }) {
  const fr = lang === "fr";
  const [status, setStatus] = useState(ticket.status || "open");
  const [saving, setSaving] = useState(false);
  async function upd(ns) {
    setSaving(true);
    try {
      await fetchWithAuth(`${API}/admin/tickets/${ticket.ticket_id}/status`, {
        method: "PUT",
        body: JSON.stringify({ status: ns }),
      });
      setStatus(ns);
      onUpdate(ticket.ticket_id, ns);
    } catch(e) {console.error(e);}
    setSaving(false);
  }
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(4,8,15,.85)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 999,
        backdropFilter: "blur(4px)",
      }}
    >
      <div
        style={{
          background: T.card,
          border: `1px solid ${T.borderHi}`,
          borderRadius: 16,
          padding: 28,
          width: 520,
          boxShadow: "0 24px 80px rgba(0,0,0,.8)",
          animation: "scaleIn .2s ease",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 22,
          }}
        >
          <Row style={{ gap: 12 }}>
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: 10,
                background: T.orange + "18",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Ticket size={18} color={T.orange} />
            </div>
            <div>
              <Mono size={13} color={T.orange}>
                {ticket.ticket_id}
              </Mono>
              <div style={{ fontSize: 11, color: T.sub, marginTop: 1 }}>
                {fr ? "Détails du ticket" : "Ticket details"}
              </div>
            </div>
          </Row>
          <Row style={{ gap: 8 }}>
            <PrioTag p={ticket.priority} />
            <StatusTag s={status} />
            <button
              onClick={onClose}
              style={{
                background: "none",
                border: "none",
                color: T.sub,
                padding: 4,
                display: "flex",
                cursor: "pointer",
                borderRadius: 6,
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = T.text)}
              onMouseLeave={(e) => (e.currentTarget.style.color = T.sub)}
            >
              <X size={16} />
            </button>
          </Row>
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 10,
            marginBottom: 18,
          }}
        >
          {[
            {
              l: fr ? "Utilisateur" : "User",
              v: ticket.user_id || "anonymous",
            },
            { l: fr ? "Catégorie" : "Category", v: ticket.category || "—" },
            { l: fr ? "Source" : "Source", v: ticket.source || "kb" },
            {
              l: fr ? "Créé le" : "Created",
              v: ticket.created_at
                ? new Date(ticket.created_at).toLocaleString()
                : "—",
            },
          ].map(({ l, v }) => (
            <div
              key={l}
              style={{
                background: T.hi,
                borderRadius: 8,
                padding: "11px 14px",
              }}
            >
              <Mono size={9} color={T.dim}>
                {l.toUpperCase()}
              </Mono>
              <div
                style={{
                  fontSize: 13,
                  color: T.text,
                  fontWeight: 500,
                  marginTop: 4,
                }}
              >
                {v}
              </div>
            </div>
          ))}
        </div>
        <div
          style={{
            background: T.hi,
            borderRadius: 10,
            padding: "13px 16px",
            marginBottom: 20,
          }}
        >
          <Mono size={9} color={T.dim}>
            {fr ? "DESCRIPTION" : "SUMMARY"}
          </Mono>
          <div
            style={{
              fontSize: 13,
              color: T.text,
              lineHeight: 1.65,
              marginTop: 7,
            }}
          >
            {ticket.summary || "—"}
          </div>
        </div>
        <div style={{ marginBottom: 22 }}>
          <Mono size={9} color={T.dim}>
            {fr ? "CHANGER STATUT" : "UPDATE STATUS"}
          </Mono>
          <div style={{ display: "flex", gap: 7, marginTop: 10 }}>
            {["open", "in_progress", "resolved", "closed"].map((st) => {
              const d = STATUS_MAP[st];
              const active = status === st;
              return (
                <button
                  key={st}
                  onClick={() => !saving && upd(st)}
                  style={{
                    flex: 1,
                    padding: "8px 0",
                    borderRadius: 8,
                    fontSize: 9,
                    fontWeight: 700,
                    fontFamily: "'JetBrains Mono',monospace",
                    letterSpacing: ".06em",
                    border: `1px solid ${active ? d.color + "88" : T.border}`,
                    background: active ? d.bg : "transparent",
                    color: active ? d.color : T.dim,
                    cursor: saving ? "wait" : "pointer",
                    transition: "all .15s",
                  }}
                >
                  {saving && active ? "…" : d.label}
                </button>
              );
            })}
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            width: "100%",
            padding: "10px 0",
            background: "transparent",
            border: `1px solid ${T.border}`,
            borderRadius: 9,
            color: T.sub,
            fontSize: 13,
            cursor: "pointer",
            transition: "all .15s",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = T.borderHi;
            e.currentTarget.style.color = T.text;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = T.border;
            e.currentTarget.style.color = T.sub;
          }}
        >
          {fr ? "Fermer" : "Close"}
        </button>
      </div>
    </div>
  );
}

/* ── user modal ── */
function UserModal({ lang, user, onSave, onClose }) {
  const fr = lang === "fr";
  const isEdit = !!user;
  const [form, setForm] = useState({
    username: user?.username || "",
    password: "",
    role: user?.role || "user",
    full_name: user?.full_name || "",
    email: user?.email || "",
    department: user?.department || "",
    phone: user?.phone || "",
    location: user?.location || "",
    is_active: user?.is_active !== undefined ? !!user.is_active : true,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const set = (k, v) => setForm((p) => ({ ...p, [k]: v }));

  const iStyle = {
    width: "100%",
    padding: "10px 13px",
    background: T.hi,
    border: `1px solid ${T.border}`,
    borderRadius: 9,
    color: T.text,
    fontSize: 13,
    outline: "none",
    transition: "border-color .15s",
  };

  async function save() {
    if (!form.username || (!isEdit && !form.password)) {
      setError(
        fr ? "Champs obligatoires manquants." : "Required fields missing.",
      );
      return;
    }
    setLoading(true);
    setError("");
    try {
      const d = await fetchWithAuth(
        isEdit
          ? `${API}/admin/users/${user.user_id}`
          : `${API}/admin/users/create`,
        { method: isEdit ? "PUT" : "POST", body: JSON.stringify(form) },
      );
      if (!d) return;
      if (d.status === "ok") onSave();
      else setError(d.message || "Error");
    } catch {
      setError(fr ? "Erreur réseau." : "Network error.");
    }
    setLoading(false);
  }

  const FIELDS = [
    { key: "username", label: "Username *", type: "text", ph: "ex: john.doe" },
    {
      key: "password",
      label: isEdit
        ? fr
          ? "Nouveau mot de passe (vide = inchangé)"
          : "New password (blank = keep)"
        : fr
          ? "Mot de passe *"
          : "Password *",
      type: "password",
      ph: "••••••••",
    },
    {
      key: "full_name",
      label: fr ? "Nom complet" : "Full name",
      type: "text",
      ph: "ex: John Doe",
    },
    { key: "email", label: "Email", type: "email", ph: "john@company.com" },
    {
      key: "department",
      label: fr ? "Département" : "Department",
      type: "text",
      ph: "ex: Finance",
    },
    {
      key: "phone",
      label: fr ? "Téléphone" : "Phone",
      type: "text",
      ph: "+212 6XX XXX XXX",
    },
    {
      key: "location",
      label: fr ? "Localisation" : "Location",
      type: "text",
      ph: "ex: Casablanca",
    },
  ];

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(4,8,15,.85)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 999,
        backdropFilter: "blur(4px)",
      }}
    >
      <div
        style={{
          background: T.card,
          border: `1px solid ${T.borderHi}`,
          borderRadius: 16,
          padding: 28,
          width: 480,
          maxHeight: "85vh",
          overflowY: "auto",
          boxShadow: "0 24px 80px rgba(0,0,0,.8)",
          animation: "scaleIn .2s ease",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 22,
          }}
        >
          <Row style={{ gap: 10 }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 9,
                background: T.accent + "18",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <User size={16} color={T.accent} />
            </div>
            <div>
              <div
                style={{
                  fontSize: 14,
                  fontWeight: 700,
                  color: T.text,
                  fontFamily: "'Syne',sans-serif",
                }}
              >
                {isEdit
                  ? fr
                    ? "Modifier l'utilisateur"
                    : "Edit user"
                  : fr
                    ? "Nouvel utilisateur"
                    : "New user"}
              </div>
              <div style={{ fontSize: 11, color: T.sub, marginTop: 1 }}>
                {isEdit
                  ? `@${user.username}`
                  : fr
                    ? "Créer un compte"
                    : "Create account"}
              </div>
            </div>
          </Row>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              color: T.sub,
              padding: 4,
              display: "flex",
              cursor: "pointer",
              borderRadius: 6,
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Fields */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 12,
            marginBottom: 14,
          }}
        >
          {FIELDS.map(({ key, label, type, ph }) => (
            <div
              key={key}
              style={{
                gridColumn:
                  key === "username" || key === "password"
                    ? "span 2"
                    : "span 1",
              }}
            >
              <div
                style={{
                  fontSize: 9,
                  color: T.dim,
                  fontWeight: 700,
                  letterSpacing: ".1em",
                  fontFamily: "'JetBrains Mono',monospace",
                  marginBottom: 6,
                }}
              >
                {label.toUpperCase()}
              </div>
              <input
                type={type}
                value={form[key]}
                onChange={(e) => set(key, e.target.value)}
                placeholder={ph}
                style={iStyle}
                onFocus={(e) => (e.target.style.borderColor = T.accent)}
                onBlur={(e) => (e.target.style.borderColor = T.border)}
              />
            </div>
          ))}
        </div>

        {/* Role */}
        <div style={{ marginBottom: 14 }}>
          <div
            style={{
              fontSize: 9,
              color: T.dim,
              fontWeight: 700,
              letterSpacing: ".1em",
              fontFamily: "'JetBrains Mono',monospace",
              marginBottom: 8,
            }}
          >
            ROLE
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {["user", "admin"].map((r) => {
              const active = form.role === r;
              const color = r === "admin" ? T.accent2 : T.accent;
              return (
                <button
                  key={r}
                  onClick={() => set("role", r)}
                  style={{
                    flex: 1,
                    padding: "10px 0",
                    borderRadius: 9,
                    fontSize: 12,
                    fontWeight: 600,
                    border: `1px solid ${active ? color + "88" : T.border}`,
                    background: active ? color + "18" : "transparent",
                    color: active ? color : T.sub,
                    transition: "all .15s",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 6,
                    cursor: "pointer",
                  }}
                >
                  {r === "admin" ? (
                    <ShieldCheck size={13} />
                  ) : (
                    <User size={13} />
                  )}
                  {r.charAt(0).toUpperCase() + r.slice(1)}
                  {active && <Check size={11} />}
                </button>
              );
            })}
          </div>
        </div>

        {/* is_active — seulement en mode edit */}
        {isEdit && (
          <div style={{ marginBottom: 14 }}>
            <div
              style={{
                fontSize: 9,
                color: T.dim,
                fontWeight: 700,
                letterSpacing: ".1em",
                fontFamily: "'JetBrains Mono',monospace",
                marginBottom: 8,
              }}
            >
              STATUS
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              {[
                { val: true, label: "Active", color: T.green },
                { val: false, label: "Inactive", color: T.red },
              ].map(({ val, label, color }) => {
                const active = form.is_active === val;
                return (
                  <button
                    key={label}
                    onClick={() => set("is_active", val)}
                    style={{
                      flex: 1,
                      padding: "9px 0",
                      borderRadius: 9,
                      fontSize: 12,
                      fontWeight: 600,
                      border: `1px solid ${active ? color + "88" : T.border}`,
                      background: active ? color + "18" : "transparent",
                      color: active ? color : T.sub,
                      transition: "all .15s",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 6,
                      cursor: "pointer",
                    }}
                  >
                    {label}
                    {active && <Check size={11} />}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {error && (
          <div
            style={{
              fontSize: 12,
              color: T.red,
              marginBottom: 12,
              padding: "8px 12px",
              background: T.red + "12",
              borderRadius: 7,
              border: `1px solid ${T.red}33`,
            }}
          >
            {error}
          </div>
        )}

        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={save}
            disabled={loading}
            style={{
              flex: 1,
              padding: "11px 0",
              background: `linear-gradient(135deg,${T.accent},${T.accent2})`,
              border: "none",
              borderRadius: 9,
              color: "#fff",
              fontSize: 13,
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6,
              cursor: "pointer",
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? (
              <Spinner />
            ) : (
              <>
                <CheckCircle2 size={14} />
                {fr ? "Enregistrer" : "Save"}
              </>
            )}
          </button>
          <button
            onClick={onClose}
            style={{
              padding: "11px 18px",
              background: "transparent",
              border: `1px solid ${T.border}`,
              borderRadius: 9,
              color: T.sub,
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            {fr ? "Annuler" : "Cancel"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── delete confirm ── */
function DeleteModal({ lang, label, onConfirm, onClose }) {
  const fr = lang === "fr";
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(4,8,15,.85)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        backdropFilter: "blur(4px)",
      }}
    >
      <div
        style={{
          background: T.card,
          border: `1px solid ${T.red}44`,
          borderRadius: 16,
          padding: 26,
          width: 360,
          boxShadow: "0 24px 80px rgba(0,0,0,.8)",
          animation: "scaleIn .2s ease",
        }}
      >
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: 12,
            background: T.red + "18",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: 16,
          }}
        >
          <AlertCircle size={22} color={T.red} />
        </div>
        <div
          style={{
            fontSize: 16,
            fontWeight: 700,
            color: T.text,
            fontFamily: "'Syne',sans-serif",
            marginBottom: 8,
          }}
        >
          {fr ? "Confirmer la suppression" : "Confirm deletion"}
        </div>
        <div
          style={{
            fontSize: 13,
            color: T.sub,
            marginBottom: 22,
            lineHeight: 1.55,
          }}
        >
          {fr
            ? `Supprimer "${label}" ? Action irréversible.`
            : `Delete "${label}"? This cannot be undone.`}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={onConfirm}
            style={{
              flex: 1,
              padding: "10px 0",
              background: T.red + "18",
              border: `1px solid ${T.red}55`,
              borderRadius: 9,
              color: T.red,
              fontSize: 13,
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6,
              cursor: "pointer",
            }}
          >
            <Trash2 size={13} />
            {fr ? "Supprimer" : "Delete"}
          </button>
          <button
            onClick={onClose}
            style={{
              padding: "10px 18px",
              background: "transparent",
              border: `1px solid ${T.border}`,
              borderRadius: 9,
              color: T.sub,
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            {fr ? "Annuler" : "Cancel"}
          </button>
        </div>
      </div>
    </div>
  );
}

function UserDetailModal({ user, lang, onClose, onEdit }) {
  const fr = lang === "fr";
  const fields = [
    { label: "Username", value: user.username },
    { label: "Full name", value: user.full_name || "—" },
    { label: "Email", value: user.email || "—" },
    { label: fr ? "Département" : "Department", value: user.department || "—" },
    { label: fr ? "Téléphone" : "Phone", value: user.phone || "—" },
    { label: fr ? "Localisation" : "Location", value: user.location || "—" },
    { label: "Role", value: user.role?.toUpperCase() },
    { label: "Status", value: user.is_active ? "Active" : "Inactive" },
    {
      label: fr ? "Dernière connexion" : "Last login",
      value: user.last_login
        ? new Date(user.last_login).toLocaleString()
        : "Never",
    },
    {
      label: fr ? "Créé le" : "Created",
      value: user.created_at
        ? new Date(user.created_at).toLocaleDateString()
        : "—",
    },
  ];

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(4,8,15,.85)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 999,
        backdropFilter: "blur(4px)",
      }}
    >
      <div
        style={{
          background: T.card,
          border: `1px solid ${T.borderHi}`,
          borderRadius: 16,
          padding: 28,
          width: 440,
          maxHeight: "80vh",
          overflowY: "auto",
          boxShadow: "0 24px 80px rgba(0,0,0,.8)",
          animation: "scaleIn .2s ease",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 22,
          }}
        >
          <Row style={{ gap: 12 }}>
            <div
              style={{
                width: 46,
                height: 46,
                borderRadius: 12,
                background:
                  user.role === "admin"
                    ? `linear-gradient(135deg,${T.accent},${T.accent2})`
                    : T.hi,
                border: `1px solid ${T.border}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 18,
                fontWeight: 700,
                color: "#fff",
              }}
            >
              {user.username?.[0]?.toUpperCase()}
            </div>
            <div>
              <div
                style={{
                  fontSize: 15,
                  fontWeight: 700,
                  color: T.text,
                  fontFamily: "'Syne',sans-serif",
                }}
              >
                {user.username}
              </div>
              <Row style={{ gap: 6, marginTop: 3 }}>
                <Pill color={user.role === "admin" ? T.accent2 : T.sub}>
                  {user.role?.toUpperCase()}
                </Pill>
                <Pill color={user.is_active ? T.green : T.red}>
                  {user.is_active ? "ACTIVE" : "INACTIVE"}
                </Pill>
              </Row>
            </div>
          </Row>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              color: T.sub,
              padding: 4,
              display: "flex",
              cursor: "pointer",
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Fields grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 10,
            marginBottom: 20,
          }}
        >
          {fields.map(({ label, value }) => (
            <div
              key={label}
              style={{
                background: T.hi,
                borderRadius: 8,
                padding: "11px 14px",
              }}
            >
              <Mono size={9} color={T.dim}>
                {label.toUpperCase()}
              </Mono>
              <div
                style={{
                  fontSize: 12,
                  color: T.text,
                  fontWeight: 500,
                  marginTop: 4,
                  wordBreak: "break-all",
                }}
              >
                {value}
              </div>
            </div>
          ))}
        </div>

        {/* Actions */}
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => {
              onClose();
              onEdit(user);
            }}
            style={{
              flex: 1,
              padding: "10px 0",
              background: `linear-gradient(135deg,${T.accent},${T.accent2})`,
              border: "none",
              borderRadius: 9,
              color: "#fff",
              fontSize: 13,
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6,
              cursor: "pointer",
            }}
          >
            <Pencil size={13} />
            {fr ? "Modifier" : "Edit"}
          </button>
          <button
            onClick={onClose}
            style={{
              padding: "10px 18px",
              background: "transparent",
              border: `1px solid ${T.border}`,
              borderRadius: 9,
              color: T.sub,
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            {fr ? "Fermer" : "Close"}
          </button>
        </div>
      </div>
    </div>
  );
}

// MAIN
export default function AdminDashboard({ user, lang, onBack }) {
  const fr = lang === "fr";
  const [tab, setTab] = useState("overview");
  const [stats, setStats] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [pending, setPending] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [ticketModal, setTicketModal] = useState(null);
  const [userModal, setUserModal] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const [userDetail, setUserDetail] = useState(null);
  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [s, t, p, u] = await Promise.all([
        fetchWithAuth(`${API}/admin/stats`),
        fetchWithAuth(`${API}/admin/tickets`),
        fetchWithAuth(`${API}/admin/pending`),
        fetchWithAuth(`${API}/admin/users`),
      ]);

      if (!s) return; // si 401 déjà géré

      setStats(s);
      setTickets(t);
      setPending(p);
      setUsers(u);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, []);

  function authHeaders() {
    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${localStorage.getItem("auth_token") || ""}`,
    };
  }

  // fonction globale avec gestion 401
  async function fetchWithAuth(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...authHeaders(),
        ...(options.headers || {}),
      },
    });

    // gestion session expirée
    if (response.status === 401) {
      localStorage.removeItem("auth_token");
      alert("Session expirée");
      window.location.reload();
      return null;
    }

    return response.json();
  }

  async function validatePending(question, action) {
    await fetchWithAuth(`${API}/admin/pending/validate`, {
      method: "POST",
      body: JSON.stringify({ question, action }),
    });
    fetchAll();
  }
  async function deleteUser(userId) {
    await fetchWithAuth(`${API}/admin/users/${userId}`, {
      method: "DELETE",
    });
    fetchAll();
    setDeleteTarget(null);
  }
  function onTicketUpdate(id, ns) {
    setTickets((prev) =>
      prev.map((t) => (t.ticket_id === id ? { ...t, status: ns } : t)),
    );
  }

  const pendingCount = pending.filter((p) => !p.validated).length;
  const ftT = tickets.filter(
    (t) =>
      !search ||
      t.ticket_id?.toLowerCase().includes(search.toLowerCase()) ||
      t.category?.toLowerCase().includes(search.toLowerCase()) ||
      t.user_id?.toLowerCase().includes(search.toLowerCase()),
  );
  const ftU = users.filter(
    (u) => !search || u.username?.toLowerCase().includes(search.toLowerCase()),
  );

  const iconBtn = (tip, Icon, color, action) => (
    <button
      title={tip}
      onClick={action}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        width: 30,
        height: 30,
        borderRadius: 7,
        background: "none",
        border: `1px solid ${T.border}`,
        color: T.dim,
        cursor: "pointer",
        transition: "all .15s",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = color + "88";
        e.currentTarget.style.color = color;
        e.currentTarget.style.background = color + "12";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = T.border;
        e.currentTarget.style.color = T.dim;
        e.currentTarget.style.background = "none";
      }}
    >
      <Icon size={12} />
    </button>
  );

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        background: T.bg,
        color: T.text,
        fontFamily: "'Outfit',Segoe UI,sans-serif",
        overflow: "hidden",
      }}
    >
      <style>{CSS}</style>

      {/* top bar */}
      <header
        style={{
          background: T.panel,
          borderBottom: `1px solid ${T.border}`,
          padding: "0 24px",
          height: 55,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexShrink: 0,
        }}
      >
        <Row style={{ gap: 14 }}>
          <button
            onClick={onBack}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 7,
              padding: "6px 12px",
              background: "transparent",
              border: `1px solid ${T.border}`,
              borderRadius: 8,
              color: T.sub,
              fontSize: 12,
              fontWeight: 500,
              cursor: "pointer",
              transition: "all .15s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = T.borderHi;
              e.currentTarget.style.color = T.text;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = T.border;
              e.currentTarget.style.color = T.sub;
            }}
          >
            <ArrowLeft size={13} />
            {fr ? "Retour" : "Back to chat"}
          </button>
          <div style={{ width: 1, height: 20, background: T.border }} />
          <Row style={{ gap: 9 }}>
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 7,
                background: `linear-gradient(135deg,${T.accent},${T.accent2})`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Layers size={13} color="#fff" />
            </div>
            <div>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 700,
                  fontFamily: "'Syne',sans-serif",
                  color: T.text,
                }}
              >
                {fr ? "Tableau de bord" : "Admin Dashboard"}
              </div>
              <Mono size={9} color={T.dim}>
                IT Self-Service · {user?.username}
              </Mono>
            </div>
          </Row>
        </Row>
        <Row style={{ gap: 8 }}>
          <Row
            style={{
              gap: 6,
              background: T.hi,
              border: `1px solid ${T.border}`,
              borderRadius: 8,
              padding: "5px 10px",
            }}
          >
            <div
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: T.green,
                boxShadow: `0 0 6px ${T.green}`,
              }}
            />
            <Mono size={10} color={T.green}>
              {fr ? "Système actif" : "System active"}
            </Mono>
          </Row>
          <button
            onClick={fetchAll}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "6px 12px",
              background: "transparent",
              border: `1px solid ${T.border}`,
              borderRadius: 8,
              color: T.sub,
              fontSize: 12,
              cursor: "pointer",
              transition: "all .15s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = T.text)}
            onMouseLeave={(e) => (e.currentTarget.style.color = T.sub)}
          >
            <RefreshCw size={12} />
            {fr ? "Actualiser" : "Refresh"}
          </button>
        </Row>
      </header>

      {/* body */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <SideNav
          tab={tab}
          setTab={(t) => {
            setTab(t);
            setSearch("");
          }}
          counts={{
            tickets: tickets.length,
            users: users.length,
            pending: pendingCount,
          }}
          fr={fr}
        />

        <main style={{ flex: 1, overflowY: "auto", padding: 24 }}>
          {loading ? (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "60%",
                gap: 12,
                color: T.sub,
              }}
            >
              <Spinner />
              <span style={{ fontSize: 13 }}>
                {fr ? "Chargement…" : "Loading…"}
              </span>
            </div>
          ) : (
            <>
              {/* ── OVERVIEW ── */}
              {tab === "overview" && (
                <div style={{ animation: "fadeIn .35s ease" }}>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(4,1fr)",
                      gap: 14,
                      marginBottom: 22,
                    }}
                  >
                    <KPICard
                      icon={Ticket}
                      label={fr ? "Total tickets" : "Total tickets"}
                      value={stats?.tickets_total ?? 0}
                      color={T.orange}
                    />
                    <KPICard
                      icon={AlertCircle}
                      label={fr ? "Tickets ouverts" : "Open tickets"}
                      value={stats?.tickets_open ?? 0}
                      color={T.red}
                    />
                    <KPICard
                      icon={Database}
                      label={fr ? "KB en attente" : "Pending KB"}
                      value={stats?.pending_kb ?? 0}
                      color={T.violet}
                    />
                    <KPICard
                      icon={Activity}
                      label={fr ? "Sessions actives" : "Active sessions"}
                      value={stats?.active_sessions ?? 0}
                      color={T.green}
                    />
                  </div>

                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 220px 185px",
                      gap: 14,
                      marginBottom: 22,
                    }}
                  >
                    <div
                      style={{
                        background: T.card,
                        border: `1px solid ${T.border}`,
                        borderRadius: 12,
                        padding: 22,
                      }}
                    >
                      <Mono size={9} color={T.dim}>
                        {fr ? "RÉPARTITION PAR CATÉGORIE" : "BY CATEGORY"}
                      </Mono>
                      <div style={{ marginTop: 18 }}>
                        <CatChart
                          data={stats?.by_category}
                          total={stats?.tickets_total || 1}
                        />
                      </div>
                    </div>
                    <div
                      style={{
                        background: T.card,
                        border: `1px solid ${T.border}`,
                        borderRadius: 12,
                        padding: 22,
                      }}
                    >
                      <Mono size={9} color={T.dim}>
                        {fr ? "PAR PRIORITÉ" : "BY PRIORITY"}
                      </Mono>
                      <div style={{ marginTop: 8 }}>
                        <PrioChart data={stats?.by_priority} />
                      </div>
                    </div>
                    <div
                      style={{
                        background: T.card,
                        border: `1px solid ${T.border}`,
                        borderRadius: 12,
                        padding: 22,
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: 14,
                      }}
                    >
                      <Donut
                        value={
                          (stats?.tickets_total ?? 0) -
                          (stats?.tickets_open ?? 0)
                        }
                        max={stats?.tickets_total || 1}
                        color={T.green}
                        label={fr ? "Taux de résolution" : "Resolution rate"}
                        sub={fr ? "résolus" : "resolved"}
                      />
                      {[
                        {
                          l: fr ? "Résolus" : "Resolved",
                          v:
                            (stats?.tickets_total ?? 0) -
                            (stats?.tickets_open ?? 0),
                          c: T.green,
                        },
                        {
                          l: fr ? "Ouverts" : "Open",
                          v: stats?.tickets_open ?? 0,
                          c: T.red,
                        },
                      ].map(({ l, v, c }) => (
                        <div
                          key={l}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            background: T.hi,
                            borderRadius: 7,
                            padding: "6px 10px",
                            width: "100%",
                          }}
                        >
                          <Row style={{ gap: 6 }}>
                            <div
                              style={{
                                width: 6,
                                height: 6,
                                borderRadius: "50%",
                                background: c,
                              }}
                            />
                            <span style={{ fontSize: 11, color: T.sub }}>
                              {l}
                            </span>
                          </Row>
                          <Mono size={11} color={c}>
                            {v}
                          </Mono>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* recent tickets */}
                  <div
                    style={{
                      background: T.card,
                      border: `1px solid ${T.border}`,
                      borderRadius: 12,
                      padding: 22,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        marginBottom: 16,
                      }}
                    >
                      <Mono size={9} color={T.dim}>
                        {fr ? "TICKETS RÉCENTS" : "RECENT TICKETS"}
                      </Mono>
                      <button
                        onClick={() => setTab("tickets")}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 5,
                          background: "none",
                          border: "none",
                          color: T.accent,
                          fontSize: 11,
                          fontWeight: 600,
                          cursor: "pointer",
                        }}
                      >
                        {fr ? "Voir tout" : "View all"}
                        <ChevronRight size={12} />
                      </button>
                    </div>
                    {tickets.slice(0, 5).map((t, i) => (
                      <div
                        key={t.ticket_id}
                        onClick={() => setTicketModal(t)}
                        style={{
                          display: "grid",
                          gridTemplateColumns:
                            "150px 1fr 130px 80px 100px 30px",
                          alignItems: "center",
                          gap: 10,
                          padding: "10px 12px",
                          borderRadius: 8,
                          cursor: "pointer",
                          borderBottom:
                            i < 4 ? `1px solid ${T.border}` : "none",
                          transition: "background .15s",
                        }}
                        onMouseEnter={(e) =>
                          (e.currentTarget.style.background = T.hi)
                        }
                        onMouseLeave={(e) =>
                          (e.currentTarget.style.background = "transparent")
                        }
                      >
                        <Mono size={11} color={T.orange}>
                          {t.ticket_id}
                        </Mono>
                        <span
                          style={{
                            fontSize: 12,
                            color: T.text,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {t.summary || "—"}
                        </span>
                        <Mono size={10}>{t.category}</Mono>
                        <PrioTag p={t.priority} />
                        <StatusTag s={t.status || "open"} />
                        <Eye size={12} color={T.dim} />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ── TICKETS ── */}
              {tab === "tickets" && (
                <div style={{ animation: "fadeIn .35s ease" }}>
                  <SectionH
                    title={fr ? "Gestion des tickets" : "Ticket Management"}
                    sub={`${ftT.length} ${fr ? "tickets" : "tickets"}`}
                    right={
                      <SearchBox
                        value={search}
                        onChange={setSearch}
                        placeholder={fr ? "Rechercher…" : "Search…"}
                      />
                    }
                  />
                  <div
                    style={{
                      background: T.card,
                      border: `1px solid ${T.border}`,
                      borderRadius: 12,
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "160px 1fr 140px 85px 115px 70px",
                        padding: "11px 18px",
                        background: T.hi,
                        borderBottom: `1px solid ${T.border}`,
                        gap: 10,
                      }}
                    >
                      {[
                        "ID",
                        "Summary",
                        "Category",
                        "Priority",
                        "Status",
                        "",
                      ].map((h, i) => (
                        <Mono key={i} size={9} color={T.dim}>
                          {h.toUpperCase()}
                        </Mono>
                      ))}
                    </div>
                    {ftT.length === 0 ? (
                      <div
                        style={{
                          padding: 40,
                          textAlign: "center",
                          color: T.sub,
                          fontSize: 13,
                        }}
                      >
                        {fr ? "Aucun ticket trouvé" : "No tickets found"}
                      </div>
                    ) : (
                      ftT.map((t, i) => (
                        <div
                          key={t.ticket_id}
                          onClick={() => setTicketModal(t)}
                          style={{
                            display: "grid",
                            gridTemplateColumns:
                              "160px 1fr 140px 85px 115px 70px",
                            padding: "13px 18px",
                            alignItems: "center",
                            gap: 10,
                            cursor: "pointer",
                            borderBottom:
                              i < ftT.length - 1
                                ? `1px solid ${T.border}`
                                : "none",
                            transition: "background .15s",
                          }}
                          onMouseEnter={(e) =>
                            (e.currentTarget.style.background = T.hi)
                          }
                          onMouseLeave={(e) =>
                            (e.currentTarget.style.background = "transparent")
                          }
                        >
                          <Mono size={11} color={T.orange}>
                            {t.ticket_id}
                          </Mono>
                          <span
                            style={{
                              fontSize: 12,
                              color: T.text,
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {t.summary || "—"}
                          </span>
                          <span style={{ fontSize: 11, color: T.sub }}>
                            {t.category}
                          </span>
                          <PrioTag p={t.priority} />
                          <StatusTag s={t.status || "open"} />
                          <div
                            style={{
                              display: "flex",
                              justifyContent: "flex-end",
                            }}
                          >
                            {iconBtn(
                              fr ? "Voir" : "View",
                              Eye,
                              T.accent,
                              (e) => {
                                e.stopPropagation();
                                setTicketModal(t);
                              },
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}

              {/* ── USERS ── */}
              {tab === "users" && (
                <div style={{ animation: "fadeIn .35s ease" }}>
                  <SectionH
                    title={fr ? "Gestion des utilisateurs" : "User Management"}
                    sub={`${ftU.length} ${fr ? "utilisateurs" : "users"}`}
                    right={
                      <Row style={{ gap: 9 }}>
                        <SearchBox
                          value={search}
                          onChange={setSearch}
                          placeholder={fr ? "Rechercher…" : "Search…"}
                        />
                        <button
                          onClick={() => setUserModal("new")}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 6,
                            padding: "8px 14px",
                            background: `linear-gradient(135deg,${T.accent},${T.accent2})`,
                            border: "none",
                            borderRadius: 9,
                            color: "#fff",
                            fontSize: 12,
                            fontWeight: 600,
                            cursor: "pointer",
                            boxShadow: `0 4px 16px ${T.accent}44`,
                          }}
                        >
                          <Plus size={13} />
                          {fr ? "Nouvel utilisateur" : "New user"}
                        </button>
                      </Row>
                    }
                  />
                  <div
                    style={{
                      background: T.card,
                      border: `1px solid ${T.border}`,
                      borderRadius: 12,
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "1fr 140px 180px 80px 90px",
                        padding: "11px 18px",
                        background: T.hi,
                        borderBottom: `1px solid ${T.border}`,
                        gap: 10,
                      }}
                    >
                      {["User", "Department", "Email", "Role", "Actions"].map(
                        (h) => (
                          <Mono key={h} size={9} color={T.dim}>
                            {h.toUpperCase()}
                          </Mono>
                        ),
                      )}
                    </div>
                    {ftU.length === 0 ? (
                      <div
                        style={{
                          padding: 40,
                          textAlign: "center",
                          color: T.sub,
                          fontSize: 13,
                        }}
                      >
                        {fr ? "Aucun utilisateur" : "No users found"}
                      </div>
                    ) : (
                      ftU.map((u, i) => (
                        <div
                          key={u.user_id}
                          style={{
                            display: "grid",
                            gridTemplateColumns: "1fr 140px 180px 80px 90px",
                            padding: "13px 18px",
                            alignItems: "center",
                            gap: 10,
                            borderBottom:
                              i < ftU.length - 1
                                ? `1px solid ${T.border}`
                                : "none",
                            transition: "background .15s",
                            cursor: "pointer",
                          }}
                          onMouseEnter={(e) =>
                            (e.currentTarget.style.background = T.hi)
                          }
                          onMouseLeave={(e) =>
                            (e.currentTarget.style.background = "transparent")
                          }
                          onClick={() => setUserDetail(u)}
                        >
                          <Row style={{ gap: 10 }}>
                            <div
                              style={{
                                width: 32,
                                height: 32,
                                borderRadius: 8,
                                background:
                                  u.role === "admin"
                                    ? `linear-gradient(135deg,${T.accent},${T.accent2})`
                                    : T.hi,
                                border: `1px solid ${T.border}`,
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                fontSize: 12,
                                fontWeight: 700,
                                color: "#fff",
                              }}
                            >
                              {u.username?.[0]?.toUpperCase()}
                            </div>
                            <div>
                              <div
                                style={{
                                  fontSize: 13,
                                  color: T.text,
                                  fontWeight: 500,
                                }}
                              >
                                {u.username}
                              </div>
                              <Mono
                                size={9}
                                color={u.is_active ? T.green : T.red}
                              >
                                {u.is_active ? "active" : "inactive"}
                              </Mono>
                            </div>
                          </Row>
                          <span style={{ fontSize: 11, color: T.sub }}>
                            {u.department || "—"}
                          </span>

                          <Mono size={10} color={T.dim}>
                            {u.email?.slice(0, 22) || "—"}
                          </Mono>

                          <Pill color={u.role === "admin" ? T.accent2 : T.sub}>
                            {u.role?.toUpperCase()}
                          </Pill>

                          <Row style={{ gap: 6 }}>
                            {iconBtn(
                              fr ? "Détails" : "Details",
                              Eye,
                              T.cyan,
                              (e) => {
                                e.stopPropagation();
                                setUserDetail(u);
                              },
                            )}

                            {iconBtn(
                              fr ? "Modifier" : "Edit",
                              Pencil,
                              T.accent,
                              (e) => {
                                e.stopPropagation();
                                setUserModal(u);
                              },
                            )}

                            {iconBtn(
                              fr ? "Supprimer" : "Delete",
                              Trash2,
                              T.red,
                              (e) => {
                                e.stopPropagation();
                                setDeleteTarget({
                                  id: u.user_id,
                                  label: u.username,
                                });
                              },
                            )}
                          </Row>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}

              {/* ── PENDING KB ── */}
              {tab === "pending" && (
                <div style={{ animation: "fadeIn .35s ease" }}>
                  <SectionH
                    title={
                      fr
                        ? "Base de connaissances — En attente"
                        : "Knowledge Base — Pending"
                    }
                    sub={`${pendingCount} ${fr ? "entrée(s) à valider" : "entry(ies) to review"}`}
                  />
                  {pendingCount === 0 ? (
                    <div
                      style={{
                        background: T.card,
                        border: `1px solid ${T.border}`,
                        borderRadius: 12,
                        padding: 48,
                        textAlign: "center",
                        color: T.sub,
                      }}
                    >
                      <CheckCircle2
                        size={36}
                        color={T.green}
                        style={{ marginBottom: 12, opacity: 0.6 }}
                      />
                      <div
                        style={{
                          fontSize: 14,
                          fontWeight: 600,
                          color: T.text,
                          marginBottom: 4,
                        }}
                      >
                        {fr ? "Tout est à jour !" : "All caught up!"}
                      </div>
                      <div style={{ fontSize: 12 }}>
                        {fr
                          ? "Aucune entrée en attente."
                          : "No pending entries."}
                      </div>
                    </div>
                  ) : (
                    pending
                      .filter((p) => !p.validated)
                      .map((p, i) => (
                        <div
                          key={p.question}
                          style={{
                            background: T.card,
                            border: `1px solid ${T.border}`,
                            borderRadius: 12,
                            padding: 22,
                            marginBottom: 14,
                            borderLeft: `3px solid ${T.violet}`,
                            animation: `slideIn .3s ease ${i * 0.07}s both`,
                          }}
                        >
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              marginBottom: 14,
                            }}
                          >
                            <Row style={{ gap: 8 }}>
                              <Pill color={T.accent}>
                                {p.category || "IT Support"}
                              </Pill>
                              <PrioTag p={p.priority} />
                            </Row>
                            <Mono size={9} color={T.dim}>
                              {p.timestamp
                                ? new Date(p.timestamp).toLocaleString()
                                : ""}
                            </Mono>
                          </div>
                          <div
                            style={{
                              display: "grid",
                              gridTemplateColumns: "1fr 1fr",
                              gap: 12,
                              marginBottom: 16,
                            }}
                          >
                            <div
                              style={{
                                background: T.hi,
                                borderRadius: 9,
                                padding: "12px 14px",
                              }}
                            >
                              <Mono size={9} color={T.accent}>
                                QUESTION
                              </Mono>
                              <div
                                style={{
                                  fontSize: 12,
                                  color: T.text,
                                  marginTop: 6,
                                  lineHeight: 1.55,
                                }}
                              >
                                {p.question}
                              </div>
                            </div>
                            <div
                              style={{
                                background: T.hi,
                                borderRadius: 9,
                                padding: "12px 14px",
                              }}
                            >
                              <Mono size={9} color={T.green}>
                                ANSWER
                              </Mono>
                              <div
                                style={{
                                  fontSize: 12,
                                  color: T.sub,
                                  marginTop: 6,
                                  lineHeight: 1.55,
                                  maxHeight: 80,
                                  overflow: "hidden",
                                }}
                              >
                                {p.answer?.slice(0, 200)}
                                {p.answer?.length > 200 ? "…" : ""}
                              </div>
                            </div>
                          </div>
                          <div style={{ display: "flex", gap: 9 }}>
                            <button
                              onClick={() =>
                                validatePending(p.question, "approve")
                              }
                              style={{
                                flex: 1,
                                padding: "9px 0",
                                background: T.green + "14",
                                border: `1px solid ${T.green}55`,
                                borderRadius: 9,
                                color: T.green,
                                fontSize: 12,
                                fontWeight: 600,
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                gap: 7,
                                cursor: "pointer",
                                transition: "background .15s",
                              }}
                              onMouseEnter={(e) =>
                                (e.currentTarget.style.background =
                                  T.green + "22")
                              }
                              onMouseLeave={(e) =>
                                (e.currentTarget.style.background =
                                  T.green + "14")
                              }
                            >
                              <CheckCircle2 size={13} />
                              {fr ? "Approuver → KB" : "Approve → KB"}
                            </button>
                            <button
                              onClick={() =>
                                validatePending(p.question, "reject")
                              }
                              style={{
                                flex: 1,
                                padding: "9px 0",
                                background: T.red + "14",
                                border: `1px solid ${T.red}55`,
                                borderRadius: 9,
                                color: T.red,
                                fontSize: 12,
                                fontWeight: 600,
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                gap: 7,
                                cursor: "pointer",
                                transition: "background .15s",
                              }}
                              onMouseEnter={(e) =>
                                (e.currentTarget.style.background =
                                  T.red + "22")
                              }
                              onMouseLeave={(e) =>
                                (e.currentTarget.style.background =
                                  T.red + "14")
                              }
                            >
                              <XCircle size={13} />
                              {fr ? "Rejeter" : "Reject"}
                            </button>
                          </div>
                        </div>
                      ))
                  )}
                </div>
              )}
            </>
          )}
        </main>
      </div>

      {ticketModal && (
        <TicketModal
          ticket={ticketModal}
          lang={lang}
          onClose={() => setTicketModal(null)}
          onUpdate={onTicketUpdate}
          fetchWithAuth={fetchWithAuth}
        />
      )}
      {userModal && (
        <UserModal
          lang={lang}
          user={userModal === "new" ? null : userModal}
          onSave={() => {
            setUserModal(null);
            fetchAll();
          }}
          onClose={() => setUserModal(null)}
        />
      )}
      {deleteTarget && (
        <DeleteModal
          lang={lang}
          label={deleteTarget.label}
          onConfirm={() => deleteUser(deleteTarget.id)}
          onClose={() => setDeleteTarget(null)}
        />
      )}
      {userDetail && (
        <UserDetailModal
          user={userDetail}
          lang={lang}
          onClose={() => setUserDetail(null)}
          onEdit={(u) => {
            setUserModal(u);
            setUserDetail(null);
          }}
        />
      )}
    </div>
  );
}
