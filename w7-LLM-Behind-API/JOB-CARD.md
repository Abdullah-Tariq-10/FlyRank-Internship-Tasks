# Job card

**What it does (one sentence):** Classifies incoming customer support messages into deterministic routing categories with urgency levels and confidence scoring.
**Input:** `{"text": "string, 1-2000 characters"}`
**Output:** 
```json
{
  "category": "billing" | "technical" | "account" | "other",
  "urgency": "low" | "normal" | "high",
  "confidence": 0.0 - 1.0,
  "reason": "one concise sentence explaining your classification"
}