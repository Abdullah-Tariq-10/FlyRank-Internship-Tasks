# Job Card

**What it does (one sentence):** Classifies incoming customer support messages to route them to the correct department with priority and confidence scores.
**Input:** `{"text": "string, 1-2000 characters"}`
**Output:** 
```json
{
  "category": "billing | technical | account | other",
  "urgency": "low | normal | high",
  "confidence": 0.0,
  "reason": "one short sentence explaining the classification"
}