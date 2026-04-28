import json
import torch
import numpy as np
import re
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class BertFeedbackClassifier:
    """
    Classifieur BERT local — remplace le LLM pour le feedback.
    Utilisation dans feedback_handler.py
    """

    LABEL_TO_FEEDBACK = {
        "resolved" : "yes",
        "failure"  : "no",
        "partial"  : "partial",
        "mixed"    : "mixed",
        "ticket"   : "ticket_direct",
        "ambiguous": None,
    }

    def __init__(self, model_path: str = "./feedback_model_pt"):
        print(f"  [BERT] Chargement depuis {model_path}...")

        with open(f"{model_path}/label_names.json") as f:
            self.label_names = json.load(f)

        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model     = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.model.eval()
        self.threshold = 0.70

        print(f"  [BERT] Prêt — {len(self.label_names)} classes")

    def predict(self, text: str,current_problem=None) -> dict:
        if current_problem and re.search(
            r"(ça marche|works|fonctionne).{0,20}(sur|on|avec|with|autre|other|different)",
            text, re.IGNORECASE
        ):
            return {
                "intent"        : "ambiguous",
                "feedback"      : None,  # → flux normal reprend
                "confidence"    : 0.95,
                "all_scores"    : {},
                "method"        : "rule_override",
                "use_llm_backup": False,
            }

        inputs = self.tokenizer(
            text,
            return_tensors = "pt",
            truncation     = True,
            max_length     = 128,
            padding        = True,
        )

        
        inputs.pop("token_type_ids", None)

        with torch.no_grad():
            logits = self.model(**inputs).logits

        probs      = torch.softmax(logits, dim=-1).numpy()[0]
        top_idx    = int(np.argmax(probs))
        top_label  = self.label_names[top_idx]
        top_conf   = float(probs[top_idx])
        second_conf= float(sorted(probs)[-2])
        gap        = top_conf - second_conf

        # Pénaliser si ambiguïté entre deux classes
        eff_conf = top_conf * (1 + gap) / 2 if gap < 0.15 else top_conf

        return {
            "intent"        : top_label,
            "feedback"      : self.LABEL_TO_FEEDBACK.get(top_label),
            "confidence"    : round(eff_conf, 3),
            "all_scores"    : {
                self.label_names[i]: round(float(p), 3)
                for i, p in enumerate(probs)
            },
            "method"        : "bert_local",
            "use_llm_backup": eff_conf < self.threshold,
        }