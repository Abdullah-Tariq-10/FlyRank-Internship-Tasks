import json
from pathlib import Path
import urllib.error
import urllib.request

API_URL = "http://127.0.0.1:8000/triage"
EVALS_FILE = Path(__file__).resolve().parent / "cases.json"


def run_eval():
    if not EVALS_FILE.exists():
        print(f"Error: Eval file not found at {EVALS_FILE}")
        return

    with open(EVALS_FILE, "r", encoding="utf-8") as f:
        cases = json.load(f)

    total = len(cases)
    passed_category = 0
    failures = []

    print(f"\n==========================================")
    print(f" Running LLM Evaluation Suite ({total} cases)")
    print(f" Target Endpoint: {API_URL}")
    print(f"==========================================\n")

    for case in cases:
        case_id = case["id"]
        name = case["name"]
        user_input = case["input"]
        expected_cat = case["expected_category"]

        payload = json.dumps({"text": user_input}).encode("utf-8")
        req = urllib.request.Request(
            API_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=35) as response:
                body = json.loads(response.read().decode("utf-8"))
                pred_cat = body.get("category")
                confidence = body.get("confidence")

                if pred_cat == expected_cat:
                    passed_category += 1
                    print(f" [PASS] Case #{case_id}: {name} -> Predicted: {pred_cat} (conf: {confidence})")
                else:
                    print(f" [FAIL] Case #{case_id}: {name} -> Expected: {expected_cat}, Got: {pred_cat}")
                    failures.append({
                        "id": case_id,
                        "name": name,
                        "expected": expected_cat,
                        "actual": pred_cat,
                        "reason": body.get("reason"),
                    })

        except urllib.error.HTTPError as e:
            print(f" [ERROR] Case #{case_id}: {name} returned HTTP {e.code}")
            failures.append({"id": case_id, "name": name, "error": f"HTTP {e.code}"})
        except Exception as e:
            print(f" [ERROR] Case #{case_id}: {name} failed: {str(e)}")
            failures.append({"id": case_id, "name": name, "error": str(e)})

    accuracy = (passed_category / total) * 100
    print(f"\n==========================================")
    print(f" Eval Score: {passed_category}/{total} passed ({accuracy:.1f}%)")
    print(f"==========================================\n")

    if failures:
        print("Failures Breakdown:")
        for f in failures:
            print(f" - Case #{f['id']} ({f['name']}): Expected '{f.get('expected')}', Got '{f.get('actual')}'")
        print()


if __name__ == "__main__":
    run_eval()