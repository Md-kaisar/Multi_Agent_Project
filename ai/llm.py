"""
ai/llm.py — FoodFlow AI LLM Integration

Architecture (following Flaw #14 fix):
  Python calculates ALL facts (stock, deficits, scores)
  → LLM receives structured facts as context
  → LLM returns REASONING TEXT + chosen supplier name
  → Python VALIDATES the choice (supplier exists, qty reasonable)
  → Python executes the decision

The LLM never touches raw numbers directly.
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()


class LLMEngine:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.provider   = None
        self.client     = None
        self._init_client()

    def _init_client(self):
        if self.gemini_key and self.gemini_key not in ("your_gemini_api_key_here", ""):
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                self.client   = ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash",
                    google_api_key=self.gemini_key,
                    temperature=0.2
                )
                self.provider = "Gemini API"
                return
            except Exception as e:
                print(f"[LLM] Gemini init failed: {e} — falling back to Demo mode.")

        self.provider = "Demo / Rule-Based Mode"
        self.client   = None

    # ─── Generic reasoning ──────────────────────────────────────────────────
    def generate_reasoning(self, prompt_text: str, fallback_response: str) -> str:
        if self.client:
            try:
                return self.client.invoke(prompt_text).content
            except Exception as e:
                print(f"[LLM] Call failed: {e}")
        return fallback_response

    # ─── Procurement Recommendation ─────────────────────────────────────────
    def get_procurement_recommendation(
        self,
        order_context: dict,
        shortage: dict,
        ranked_suppliers: list,
    ) -> dict:
        """
        Python passes structured FACTS to the LLM.
        LLM returns reasoning text + recommended supplier name.
        Python then validates and executes.

        Returns:
          {
            "recommended_supplier": <name as string>,
            "reasoning": <paragraph text>,
            "mode": "gemini" | "rule-based"
          }
        """

        # ── Rule-based fallback (always correct) ──────────────────────────
        best = ranked_suppliers[0] if ranked_suppliers else None
        if best is None:
            return {
                "recommended_supplier": None,
                "reasoning": "No suppliers available for this ingredient.",
                "mode": "rule-based"
            }

        severity      = shortage.get("severity", "LOW")
        is_urgent     = severity == "CRITICAL"
        runner_up     = ranked_suppliers[1] if len(ranked_suppliers) > 1 else None

        fallback_reasoning = (
            f"OBSERVE: {shortage['ingredient']} shortage of {shortage['deficit']} {shortage['unit']} detected "
            f"[severity: {severity}].\n"
            f"REASON: Evaluated {len(ranked_suppliers)} candidate supplier(s) using "
            f"Speed×0.40 + Reliability×0.35 + Price×0.25 scoring.\n"
            f"DECIDE: Selected '{best['name']}' — composite score {best.get('composite_score', 'N/A')} "
            f"(Delivery: {best['delivery_time_hrs']} hr, Reliability: {int(best['reliability_score']*100)}%, "
            f"Price: ₹{best['price_per_unit']}/kg)."
        )
        if runner_up:
            fallback_reasoning += (
                f"\nACT: Runner-up '{runner_up['name']}' scored {runner_up.get('composite_score', 'N/A')}. "
                f"{'Urgency (CRITICAL severity) prioritises fast delivery — ' if is_urgent else ''}"
                f"'{best['name']}' wins on {'delivery speed' if best['delivery_time_hrs'] < runner_up['delivery_time_hrs'] else 'reliability'}."
            )
        fallback_reasoning += (
            f"\nVERIFY: Reorder quantity {shortage['reorder_qty']} {shortage['unit']} "
            f"(deficit {shortage['deficit']} + 20% safety buffer). "
            f"Total cost: ₹{best['price_per_unit'] * shortage['reorder_qty']:.2f}. Autonomous PO created."
        )

        # ── Gemini LLM call ──────────────────────────────────────────────
        if not self.client:
            return {
                "recommended_supplier": best["name"],
                "reasoning": fallback_reasoning,
                "mode": "rule-based"
            }

        # Build a structured prompt — LLM gets FACTS, not raw data
        supplier_list = "\n".join(
            f"  {i+1}. {s['name']}: ₹{s['price_per_unit']}/kg | "
            f"Delivery: {s['delivery_time_hrs']} hr | "
            f"Reliability: {int(s['reliability_score']*100)}% | "
            f"AI Score: {s.get('composite_score', 'N/A')} | "
            f"Can supply full qty: {s.get('capable', True)}"
            for i, s in enumerate(ranked_suppliers[:4])
        )

        prompt = f"""You are the Procurement Agent in FoodFlow AI, an autonomous supply-chain system.

SITUATION:
- Customer order: {order_context['quantity']}× {order_context['food_item']} for {order_context['customer_name']}
- Ingredient shortage: {shortage['ingredient']}
  - Required: {shortage['required']} {shortage['unit']}
  - Available: {shortage['available']} {shortage['unit']}
  - Deficit: {shortage['deficit']} {shortage['unit']}
  - Severity: {severity}
  - Reorder quantity (with 20% buffer): {shortage['reorder_qty']} {shortage['unit']}

CANDIDATE SUPPLIERS (pre-scored by Python using Speed×0.40 + Reliability×0.35 + Price×0.25):
{supplier_list}

YOUR TASK:
Using the OBSERVE → REASON → DECIDE → ACT → VERIFY framework:
1. Recommend exactly ONE supplier from the list above.
2. Explain your reasoning in 3-4 sentences covering: why this supplier, what trade-offs exist, and why the alternatives were not chosen.
3. Your response must be valid JSON in this exact format:
{{
  "recommended_supplier": "<exact supplier name>",
  "reasoning": "<3-4 sentence explanation>"
}}

Important: The recommended_supplier field must exactly match one of the supplier names listed above.
"""

        try:
            raw = self.client.invoke(prompt).content.strip()
            # Extract JSON from response
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()

            parsed = json.loads(raw)
            rec_name = parsed.get("recommended_supplier", "").strip()

            # ── VALIDATE: supplier must exist in our ranked list ─────────
            valid_names = [s["name"] for s in ranked_suppliers]
            if rec_name not in valid_names:
                print(f"[LLM] Returned unknown supplier '{rec_name}' — using rule-based best.")
                return {
                    "recommended_supplier": best["name"],
                    "reasoning": parsed.get("reasoning", fallback_reasoning) + "\n[Note: AI recommendation validated and corrected by backend.]",
                    "mode": "gemini-corrected"
                }

            return {
                "recommended_supplier": rec_name,
                "reasoning": parsed.get("reasoning", fallback_reasoning),
                "mode": "gemini"
            }

        except Exception as e:
            print(f"[LLM] Procurement recommendation failed: {e}")
            return {
                "recommended_supplier": best["name"],
                "reasoning": fallback_reasoning,
                "mode": "rule-based"
            }


# ── Singleton ────────────────────────────────────────────────────────────────
llm_engine = LLMEngine()
