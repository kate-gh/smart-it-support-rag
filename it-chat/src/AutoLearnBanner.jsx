// AutoLearnBanner.jsx
import { Sparkles, CheckCircle, TicketX } from "lucide-react";

export default function AutoLearnBanner({ lang, onYes, onNo }) {
  const fr = lang === "fr";
  return (
    <div
      style={{
        margin: "8px 0 4px 44px",
        padding: "10px 14px",
        background: "#0d1122",
        border: "0.5px solid #1a2a42",
        borderLeft: "3px solid #8b5cf6",
        borderRadius: "0 8px 8px 0",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 12,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, flex: 1 }}>
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 4,
            fontSize: 11,
            background: "#2d1b6e",
            color: "#8b5cf6",
            padding: "2px 7px",
            borderRadius: 4,
            fontWeight: 700,
            fontFamily: "monospace",
            flexShrink: 0,
          }}
        >
          <Sparkles size={10} />
          AI
        </span>
        <span style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.4 }}>
          {fr
            ? "Réponse générée par IA — a-t-elle résolu votre problème ?"
            : "AI-generated answer — did it resolve your issue?"}
        </span>
      </div>
      <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
        <button
          onClick={onYes}
          style={{
            padding: "5px 12px",
            background: "#0f2a1a",
            border: "0.5px solid #10b981",
            borderRadius: 6,
            color: "#10b981",
            fontSize: 12,
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 5,
          }}
        >
          <CheckCircle size={12} />
          {fr ? "Oui, résolu" : "Yes, solved"}
        </button>
        <button
          onClick={onNo}
          style={{
            padding: "5px 12px",
            background: "#1a0808",
            border: "0.5px solid #ef4444",
            borderRadius: 6,
            color: "#ef4444",
            fontSize: 12,
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 5,
          }}
        >
          <TicketX size={12} />
          {fr ? "Non, ticket" : "No, ticket"}
        </button>
      </div>
    </div>
  );
}
