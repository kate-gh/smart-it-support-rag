// ConversationSidebar.jsx — version complète
import { useState, useEffect, useRef } from "react";
import {
  MoreVertical,
  Pencil,
  Trash2,
  Plus,
  Search,
  X,
  AlertTriangle,
} from "lucide-react";

const API = "http://localhost:5000";

const C = {
  bg: "#070c18",
  surface: "#0d1526",
  hi: "#111e35",
  border: "#1a2a42",
  borderHi: "#253b5c",
  accent: "#2563eb",
  glow: "#3b82f6",
  text: "#e2e8f0",
  muted: "#64748b",
  dim: "#2a3a50",
  green: "#10b981",
  amber: "#f59e0b",
  violet: "#8b5cf6",
  red: "#ef4444",
  orange: "#f97316",
};

function timeAgo(dateStr, lang) {
  const diff = Math.floor((Date.now() - new Date(dateStr)) / 1000);
  if (diff < 60) return lang === "fr" ? "À l'instant" : "Just now";
  if (diff < 3600)
    return lang === "fr"
      ? `Il y a ${Math.floor(diff / 60)} min`
      : `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400)
    return lang === "fr"
      ? `Il y a ${Math.floor(diff / 3600)}h`
      : `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800)
    return lang === "fr"
      ? `Il y a ${Math.floor(diff / 86400)}j`
      : `${Math.floor(diff / 86400)}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

function SourceBadge({ source }) {
  const map = {
    kb: { label: "KB", color: "#3b82f6", bg: "#1a2e52" },
    llm: { label: "AI", color: "#8b5cf6", bg: "#2d1b6e" },
    other: { label: "—", color: "#64748b", bg: "#111e35" },
  };
  const d = map[source] || map.other;
  return (
    <span
      style={{
        fontFamily: "IBM Plex Mono,monospace",
        fontSize: 8,
        fontWeight: 700,
        padding: "1px 5px",
        borderRadius: 3,
        background: d.bg,
        color: d.color,
      }}
    >
      {d.label}
    </span>
  );
}

// ── Statut ticket ─────────────────────────────────────────────────────────────
function TicketBadge({ ticketId, ticketStatus, lang }) {
  if (!ticketId) return null;
  const fr = lang === "fr";
  const map = {
    open: { emoji: "🟡", label: fr ? "Ouvert" : "Open", color: "#f59e0b" },
    in_progress: {
      emoji: "🔵",
      label: fr ? "En cours" : "In progress",
      color: "#3b82f6",
    },
    resolved: {
      emoji: "🟢",
      label: fr ? "Résolu" : "Resolved",
      color: "#10b981",
    },
    closed: { emoji: "⚪", label: fr ? "Fermé" : "Closed", color: "#64748b" },
  };
  const d = map[ticketStatus] || map.open;
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 4,
        marginTop: 4,
        padding: "3px 7px",
        borderRadius: 5,
        background: d.color + "15",
        border: `1px solid ${d.color}30`,
      }}
    >
      <span style={{ fontSize: 9 }}>{d.emoji}</span>
      <span
        style={{
          fontFamily: "IBM Plex Mono,monospace",
          fontSize: 8,
          fontWeight: 700,
          color: d.color,
        }}
      >
        {ticketId.slice(0, 14)} · {d.label}
      </span>
    </div>
  );
}

// ── Modal confirmation suppression ───────────────────────────────────────────
function DeleteConfirmModal({ lang, title, onConfirm, onClose }) {
  const fr = lang === "fr";
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,.75)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 2000,
        backdropFilter: "blur(5px)",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 320,
          background: C.surface,
          border: `1px solid ${C.red}44`,
          borderRadius: 16,
          padding: 24,
          boxShadow: "0 24px 60px rgba(0,0,0,.85)",
        }}
      >
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: 12,
            background: C.red + "18",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: 14,
          }}
        >
          <AlertTriangle size={22} color={C.red} />
        </div>
        <div
          style={{
            fontSize: 15,
            fontWeight: 700,
            color: C.text,
            marginBottom: 8,
          }}
        >
          {fr ? "Supprimer la conversation ?" : "Delete conversation?"}
        </div>
        <div
          style={{
            fontSize: 12,
            color: C.muted,
            marginBottom: 20,
            lineHeight: 1.55,
          }}
        >
          {fr
            ? `"${title}" sera définitivement supprimée.`
            : `"${title}" will be permanently deleted.`}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={onConfirm}
            style={{
              flex: 1,
              padding: "9px 0",
              background: C.red + "18",
              border: `1px solid ${C.red}55`,
              borderRadius: 9,
              color: C.red,
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
              padding: "9px 16px",
              background: "transparent",
              border: `1px solid ${C.border}`,
              borderRadius: 9,
              color: C.muted,
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

// ── Modal renommage ───────────────────────────────────────────────────────────
function RenameModal({ lang, currentTitle, onSave, onClose }) {
  const fr = lang === "fr";
  const [value, setValue] = useState(currentTitle || "");
  const ref = useRef(null);
  useEffect(() => {
    setTimeout(() => ref.current?.focus(), 50);
  }, []);
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,.65)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 2000,
        backdropFilter: "blur(4px)",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 320,
          background: C.surface,
          border: `1px solid ${C.borderHi}`,
          borderRadius: 16,
          padding: 22,
          boxShadow: "0 24px 60px rgba(0,0,0,.85)",
        }}
      >
        <div
          style={{
            fontSize: 15,
            fontWeight: 700,
            color: C.text,
            marginBottom: 14,
          }}
        >
          {fr ? "Renommer" : "Rename conversation"}
        </div>
        <input
          ref={ref}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && value.trim()) onSave(value.trim());
          }}
          style={{
            width: "100%",
            padding: "10px 13px",
            background: C.hi,
            border: `1px solid ${C.border}`,
            borderRadius: 9,
            color: C.text,
            fontSize: 13,
            outline: "none",
            fontFamily: "DM Sans,sans-serif",
            boxSizing: "border-box",
          }}
          onFocus={(e) => (e.target.style.borderColor = C.accent)}
          onBlur={(e) => (e.target.style.borderColor = C.border)}
        />
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            gap: 8,
            marginTop: 14,
          }}
        >
          <button
            onClick={onClose}
            style={{
              padding: "8px 14px",
              background: "transparent",
              border: `1px solid ${C.border}`,
              borderRadius: 8,
              color: C.muted,
              fontSize: 12,
              cursor: "pointer",
            }}
          >
            {fr ? "Annuler" : "Cancel"}
          </button>
          <button
            onClick={() => value.trim() && onSave(value.trim())}
            disabled={!value.trim()}
            style={{
              padding: "8px 14px",
              background: value.trim() ? C.accent : C.dim,
              border: "none",
              borderRadius: 8,
              color: "#fff",
              fontSize: 12,
              cursor: value.trim() ? "pointer" : "not-allowed",
            }}
          >
            {fr ? "Enregistrer" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Composant principal ───────────────────────────────────────────────────────
export default function ConversationSidebar({
  user,
  lang,
  currentSessionId,
  onLoadConversation,
  onNewConversation,
  authHeaders,
}) {
  const fr = lang === "fr";
  const [convs, setConvs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeLoaded, setActiveLoaded] = useState(null);
  const [search, setSearch] = useState("");
  const [openMenu, setOpenMenu] = useState(null);
  const [renameTarget, setRenameTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const menuRef = useRef(null);

  const loadConvs = () => {
    if (!user) return;
    setLoading(true);
    fetch(`${API}/user/conversations`, { headers: authHeaders() })
      .then((r) => r.json())
      .then((data) => setConvs(Array.isArray(data) ? data : []))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadConvs();
  }, [user, currentSessionId]);

  useEffect(() => {
    const h = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target))
        setOpenMenu(null);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const filtered = convs.filter((c) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      (c.title || "").toLowerCase().includes(q) ||
      (c.ticket_id || "").toLowerCase().includes(q)
    );
  });

  async function loadDetail(sessionId) {
    if (sessionId === currentSessionId) return;
    setActiveLoaded(sessionId);
    try {
      const rows = await fetch(`${API}/user/conversations/${sessionId}`, {
        headers: authHeaders(),
      }).then((r) => r.json());
      onLoadConversation(sessionId, rows);
    } catch (e) {
      console.error(e);
    }
  }

  async function doDelete(conv) {
    try {
      await fetch(`${API}/user/conversations/${conv.session_id}`, {
        method: "DELETE",
        headers: authHeaders(),
      });
      setConvs((prev) => prev.filter((c) => c.session_id !== conv.session_id));
    } catch (e) {
      console.error(e);
    }
    setDeleteTarget(null);
  }

  async function doRename(conv, title) {
    try {
      await fetch(`${API}/user/conversations/${conv.session_id}/rename`, {
        method: "PUT",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      });
      setConvs((prev) =>
        prev.map((c) =>
          c.session_id === conv.session_id ? { ...c, title } : c,
        ),
      );
    } catch (e) {
      console.error(e);
    }
    setRenameTarget(null);
  }

  if (!user) return null;

  return (
    <>
      <aside
        style={{
          width: 235,
          flexShrink: 0,
          background: C.surface,
          borderRight: `1px solid ${C.border}`,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* ── En-tête ──────────────────────────────────────────────────────── */}
        <div
          style={{
            padding: "12px 10px 10px",
            borderBottom: `1px solid ${C.border}`,
            flexShrink: 0,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 10,
            }}
          >
            <span
              style={{
                fontSize: 9,
                fontWeight: 700,
                letterSpacing: ".1em",
                color: C.muted,
                fontFamily: "IBM Plex Mono,monospace",
              }}
            >
              {fr ? "CONVERSATIONS" : "CONVERSATIONS"}
            </span>
            <span
              style={{
                fontSize: 9,
                color: C.dim,
                fontFamily: "IBM Plex Mono,monospace",
              }}
            >
              {convs.length}
            </span>
          </div>

          {/* Bouton + Nouvelle conversation */}
          <button
            onClick={onNewConversation}
            style={{
              width: "100%",
              padding: "8px 12px",
              background: `linear-gradient(135deg,${C.accent}22,${C.violet}22)`,
              border: `1px solid ${C.accent}44`,
              borderRadius: 9,
              color: C.accent,
              fontSize: 12,
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 7,
              cursor: "pointer",
              transition: "all .15s",
              marginBottom: 8,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = `linear-gradient(135deg,${C.accent}35,${C.violet}35)`;
              e.currentTarget.style.borderColor = C.accent + "88";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = `linear-gradient(135deg,${C.accent}22,${C.violet}22)`;
              e.currentTarget.style.borderColor = C.accent + "44";
            }}
          >
            <Plus size={13} strokeWidth={2.5} />
            {fr ? "Nouvelle conversation" : "New conversation"}
          </button>

          {/* Recherche */}
          <div style={{ position: "relative" }}>
            <Search
              size={11}
              color={C.dim}
              style={{
                position: "absolute",
                left: 9,
                top: "50%",
                transform: "translateY(-50%)",
                pointerEvents: "none",
              }}
            />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={fr ? "Rechercher…" : "Search…"}
              style={{
                width: "100%",
                padding: "7px 26px 7px 27px",
                background: C.hi,
                border: `1px solid ${C.border}`,
                borderRadius: 8,
                color: C.text,
                fontSize: 12,
                outline: "none",
                fontFamily: "DM Sans,sans-serif",
                boxSizing: "border-box",
                transition: "border-color .15s",
              }}
              onFocus={(e) => (e.target.style.borderColor = C.accent)}
              onBlur={(e) => (e.target.style.borderColor = C.border)}
            />
            {search && (
              <button
                onClick={() => setSearch("")}
                style={{
                  position: "absolute",
                  right: 7,
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "none",
                  border: "none",
                  color: C.muted,
                  cursor: "pointer",
                  display: "flex",
                  padding: 0,
                }}
              >
                <X size={11} />
              </button>
            )}
          </div>
        </div>

        {/* ── Liste ────────────────────────────────────────────────────────── */}
        <div style={{ overflowY: "auto", flex: 1, padding: "6px 7px" }}>
          {loading ? (
            <div
              style={{
                padding: 24,
                textAlign: "center",
                color: C.muted,
                fontSize: 11,
              }}
            >
              {fr ? "Chargement…" : "Loading…"}
            </div>
          ) : filtered.length === 0 ? (
            <div
              style={{
                padding: 24,
                textAlign: "center",
                color: C.dim,
                fontSize: 11,
              }}
            >
              {search
                ? fr
                  ? "Aucun résultat"
                  : "No results"
                : fr
                  ? "Aucune conversation"
                  : "No conversations yet"}
            </div>
          ) : (
            filtered.map((conv) => {
              const isCurrent = conv.session_id === currentSessionId;
              const isLoaded = conv.session_id === activeLoaded;
              const selected = isCurrent || isLoaded;

              return (
                <div
                  key={conv.session_id}
                  onClick={() => loadDetail(conv.session_id)}
                  style={{
                    position: "relative",
                    padding: "10px 10px",
                    borderRadius: 9,
                    marginBottom: 3,
                    cursor: "pointer",
                    background: selected ? C.hi : "transparent",
                    border: `1px solid ${selected ? C.borderHi : "transparent"}`,
                    borderLeft: `3px solid ${selected ? C.accent : "transparent"}`,
                    transition: "all .15s",
                  }}
                  onMouseEnter={(e) => {
                    if (!selected)
                      e.currentTarget.style.background = C.hi + "88";
                  }}
                  onMouseLeave={(e) => {
                    if (!selected)
                      e.currentTarget.style.background = "transparent";
                  }}
                >
                  {/* Ligne 1 : icône + badges + menu */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      marginBottom: 4,
                    }}
                  >
                    <div
                      style={{ display: "flex", alignItems: "center", gap: 5 }}
                    >
                      <span style={{ fontSize: 12 }}>
                        {conv.ticket_id ? "🎫" : conv.resolved ? "✅" : "🔄"}
                      </span>
                      <SourceBadge source={conv.source} />
                      {isCurrent && (
                        <span
                          style={{
                            fontSize: 8,
                            color: C.green,
                            fontFamily: "IBM Plex Mono,monospace",
                            fontWeight: 700,
                          }}
                        >
                          {fr ? "EN COURS" : "LIVE"}
                        </span>
                      )}
                    </div>

                    {/* Menu ⋮ */}
                    <div
                      ref={openMenu === conv.session_id ? menuRef : null}
                      style={{ position: "relative" }}
                    >
                      <div
                        onClick={(e) => {
                          e.stopPropagation();
                          setOpenMenu(
                            openMenu === conv.session_id
                              ? null
                              : conv.session_id,
                          );
                        }}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          width: 20,
                          height: 20,
                          borderRadius: 5,
                          color: C.muted,
                          cursor: "pointer",
                          transition: "color .15s",
                        }}
                        onMouseEnter={(e) =>
                          (e.currentTarget.style.color = C.text)
                        }
                        onMouseLeave={(e) =>
                          (e.currentTarget.style.color = C.muted)
                        }
                      >
                        <MoreVertical size={13} />
                      </div>

                      {openMenu === conv.session_id && (
                        <div
                          onClick={(e) => e.stopPropagation()}
                          style={{
                            position: "absolute",
                            top: 22,
                            right: 0,
                            background: C.surface,
                            border: `1px solid ${C.borderHi}`,
                            borderRadius: 9,
                            zIndex: 100,
                            overflow: "hidden",
                            minWidth: 130,
                            boxShadow: "0 8px 28px rgba(0,0,0,.7)",
                          }}
                        >
                          {[
                            {
                              icon: <Pencil size={12} />,
                              label: fr ? "Renommer" : "Rename",
                              color: C.text,
                              action: () => {
                                setRenameTarget(conv);
                                setOpenMenu(null);
                              },
                            },
                            {
                              icon: <Trash2 size={12} />,
                              label: fr ? "Supprimer" : "Delete",
                              color: C.red,
                              action: () => {
                                setDeleteTarget(conv);
                                setOpenMenu(null);
                              },
                            },
                          ].map((item) => (
                            <div
                              key={item.label}
                              onClick={item.action}
                              style={{
                                padding: "9px 12px",
                                cursor: "pointer",
                                fontSize: 12,
                                color: item.color,
                                display: "flex",
                                alignItems: "center",
                                gap: 8,
                                transition: "background .12s",
                              }}
                              onMouseEnter={(e) =>
                                (e.currentTarget.style.background = C.hi)
                              }
                              onMouseLeave={(e) =>
                                (e.currentTarget.style.background =
                                  "transparent")
                              }
                            >
                              {item.icon}
                              {item.label}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Titre */}
                  <div
                    style={{
                      fontSize: 12,
                      color: selected ? C.text : "#94a3b8",
                      fontWeight: selected ? 600 : 400,
                      lineHeight: 1.4,
                      overflow: "hidden",
                      display: "-webkit-box",
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: "vertical",
                      marginBottom: 4,
                    }}
                  >
                    {conv.title || (fr ? "Conversation" : "Conversation")}
                  </div>

                  {/* Ticket status */}
                  <TicketBadge
                    ticketId={conv.ticket_id}
                    ticketStatus={conv.ticket_status}
                    lang={lang}
                  />

                  {/* Méta */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      marginTop: 5,
                    }}
                  >
                    <span
                      style={{
                        fontSize: 9,
                        color: C.dim,
                        fontFamily: "IBM Plex Mono,monospace",
                      }}
                    >
                      {timeAgo(conv.last_activity, lang)}
                    </span>
                    <span
                      style={{
                        fontSize: 9,
                        color: C.dim,
                        fontFamily: "IBM Plex Mono,monospace",
                      }}
                    >
                      {conv.message_count} msg
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </aside>

      {deleteTarget && (
        <DeleteConfirmModal
          lang={lang}
          title={deleteTarget.title || "conversation"}
          onConfirm={() => doDelete(deleteTarget)}
          onClose={() => setDeleteTarget(null)}
        />
      )}
      {renameTarget && (
        <RenameModal
          lang={lang}
          currentTitle={renameTarget.title || ""}
          onSave={(title) => doRename(renameTarget, title)}
          onClose={() => setRenameTarget(null)}
        />
      )}
    </>
  );
}
