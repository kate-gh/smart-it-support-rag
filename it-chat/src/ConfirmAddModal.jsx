// ConfirmAddModal.jsx
import { useState } from "react";
import { CheckCircle, Clock, Star as StarIcon, X } from "lucide-react";

const API = "http://localhost:5000";

export function authHeaders() {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${localStorage.getItem("auth_token") || ""}`,
  };
}

export async function fetchWithAuth(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: {
      ...authHeaders(),
      ...(options.headers || {}),
    },
  });

  // 🔐 gestion session expirée
  if (res.status === 401) {
    localStorage.removeItem("auth_token");
    alert("Session expirée");
    window.location.reload();
    return null;
  }

  return res.json();
}

const StarRating = ({ stars, hover, onSet, onHover, onLeave, fr }) => (
  <div>
    <div
      style={{
        fontSize: 11,
        color: "#64748b",
        marginBottom: 6,
        fontFamily: "monospace",
      }}
    >
      {fr ? "Votre évaluation" : "Your rating"}
    </div>
    <div
      style={{ display: "flex", gap: 4, alignItems: "center" }}
      onMouseLeave={onLeave}
    >
      {[1, 2, 3, 4, 5].map((n) => (
        <StarIcon
          key={n}
          size={22}
          onClick={() => onSet(n)}
          onMouseEnter={() => onHover(n)}
          style={{ cursor: "pointer", transition: "color .15s" }}
          color={n <= (hover || stars) ? "#f59e0b" : "#1a2a42"}
          fill={n <= (hover || stars) ? "#f59e0b" : "none"}
        />
      ))}
      {stars > 0 && (
        <span
          style={{
            fontSize: 11,
            color: "#64748b",
            marginLeft: 6,
            fontFamily: "monospace",
          }}
        >
          {fr
            ? ["", "Très mauvais", "Mauvais", "Correct", "Bon", "Excellent"][
                stars
              ]
            : ["", "Very poor", "Poor", "Fair", "Good", "Excellent"][stars]}
        </span>
      )}
    </div>
    {stars === 0 && (
      <div style={{ fontSize: 11, color: "#f59e0b", marginTop: 4 }}>
        {fr ? "Notez avant de confirmer" : "Please rate before confirming"}
      </div>
    )}
  </div>
);

export default function ConfirmAddModal({
  lang,
  fallback,
  sessionId,
  user,
  onDone,
  onClose,
}) {
  const fr = lang === "fr";
  const [stars, setStars] = useState(3);
  const [hover, setHover] = useState(0);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  async function confirm() {
    if (stars === 0) return;
    setLoading(true);

    try {
      const d = await fetchWithAuth(`${API}/kb/add`, {
        method: "POST",
        body: JSON.stringify({
          session_id: sessionId,
          user_id: user.user_id,
          user_score: stars,
        }),
      });

      if (!d) return; // session expirée

      setResult(d);
    } catch {
      setResult({
        status: "error",
        feedback: fr ? "Erreur réseau." : "Network error.",
      });
    } finally {
      setLoading(false);
    }
  }
  const btnBase = {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    borderRadius: 8,
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.75)",
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
          width: 380,
          boxShadow: "0 8px 40px rgba(0,0,0,.8)",
        }}
      >
        {result ? (
          /* ── Result screen ── */
          <div>
            {result.status === "approved" ? (
              <div style={{ textAlign: "center" }}>
                <CheckCircle
                  size={40}
                  color="#10b981"
                  style={{ margin: "0 auto 12px" }}
                />
                <div
                  style={{
                    fontSize: 15,
                    fontWeight: 700,
                    color: "#10b981",
                    marginBottom: 8,
                  }}
                >
                  {fr
                    ? "Ajouté directement à la base !"
                    : "Added to knowledge base!"}
                </div>
                <div style={{ fontSize: 12, color: "#94a3b8" }}>
                  {fr
                    ? `Note donnée : ${result.score}/5`
                    : `Your rating: ${result.score}/5`}
                </div>
              </div>
            ) : result.status === "pending" ? (
              <div style={{ textAlign: "center" }}>
                <Clock
                  size={40}
                  color="#f59e0b"
                  style={{ margin: "0 auto 12px" }}
                />
                <div
                  style={{
                    fontSize: 15,
                    fontWeight: 700,
                    color: "#f59e0b",
                    marginBottom: 8,
                  }}
                >
                  {fr
                    ? "Ajout en attente de validation"
                    : "Added as pending review"}
                </div>
                <div style={{ fontSize: 12, color: "#94a3b8" }}>
                  {fr
                    ? `Note donnée : ${result.score}/5`
                    : `Your rating: ${result.score}/5`}
                </div>
              </div>
            ) : (
              <div
                style={{ color: "#ef4444", textAlign: "center", fontSize: 13 }}
              >
                {result.feedback}
              </div>
            )}
            <button
              onClick={() => {
                setResult(null);
                onDone(result);
              }}
              style={{
                ...btnBase,
                width: "100%",
                marginTop: 18,
                padding: "9px 0",
                background: "#111e35",
                border: "1px solid #1a2a42",
                color: "#94a3b8",
              }}
            >
              {fr ? "Fermer" : "Close"}
            </button>
          </div>
        ) : (
          /* ── Form screen ── */
          <>
            {/* Header */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                marginBottom: 16,
              }}
            >
              <div>
                <div
                  style={{ fontSize: 15, fontWeight: 700, color: "#e2e8f0" }}
                >
                  {fr
                    ? "Ajouter à la base de connaissances ?"
                    : "Add to knowledge base?"}
                </div>
                <div
                  style={{
                    fontSize: 11,
                    color: "#64748b",
                    marginTop: 4,
                    fontFamily: "monospace",
                  }}
                >
                  {fr
                    ? `Connecté en tant que ${user.username}`
                    : `Logged in as ${user.username}`}
                </div>
              </div>
              <button
                onClick={onClose}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: "#64748b",
                  padding: 2,
                }}
              >
                <X size={16} />
              </button>
            </div>

            {/* Q/A preview */}
            <div
              style={{
                background: "#111e35",
                borderRadius: 8,
                padding: 12,
                marginBottom: 16,
                maxHeight: 140,
                overflowY: "auto",
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  color: "#2563eb",
                  fontWeight: 700,
                  fontFamily: "monospace",
                  marginBottom: 4,
                }}
              >
                Q
              </div>
              <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 10 }}>
                {fallback.question}
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: "#10b981",
                  fontWeight: 700,
                  fontFamily: "monospace",
                  marginBottom: 4,
                }}
              >
                A
              </div>
              <div style={{ fontSize: 12, color: "#94a3b8" }}>
                {fallback.answer?.slice(0, 180)}…
              </div>
            </div>

            {/* Stars */}
            <div style={{ marginBottom: 16 }}>
              <StarRating
                stars={stars}
                hover={hover}
                onSet={setStars}
                onHover={setHover}
                onLeave={() => setHover(0)}
                fr={fr}
              />
            </div>

            {/* Buttons */}
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={confirm}
                disabled={loading || stars === 0}
                style={{
                  ...btnBase,
                  flex: 1,
                  padding: "9px 0",
                  background:
                    stars === 0 || loading
                      ? "#111e35"
                      : "linear-gradient(135deg,#2563eb,#7c3aed)",
                  border: `1px solid ${stars === 0 || loading ? "#1a2a42" : "transparent"}`,
                  color: stars === 0 || loading ? "#2a3a50" : "#fff",
                  cursor: stars === 0 ? "not-allowed" : "pointer",
                }}
              >
                {loading ? "…" : fr ? "Confirmer l'ajout" : "Confirm add"}
              </button>
              <button
                onClick={onClose}
                style={{
                  ...btnBase,
                  padding: "9px 16px",
                  background: "#111e35",
                  border: "1px solid #1a2a42",
                  color: "#64748b",
                }}
              >
                {fr ? "Annuler" : "Cancel"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
