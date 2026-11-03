"""Verify the prompt-template endpoints (no LLM required)."""
import httpx

BASE = "http://127.0.0.1:8000"

with httpx.Client(base_url=BASE, timeout=60) as c:
    info = c.get("/api/prompts").json()
    print("keys:", list(info["templates"]))
    print("overridden:", info["overridden"], "hash:", info["prompt_hash"])
    print("meta keys:", list(info["meta"]))
    print("vars(evaluation):", info["variables"]["evaluation_template"])

    # 1) preview with defaults
    r = c.post("/api/prompts/preview",
               json={"candidate_level": "三级", "responsibility_score": 26})
    d = r.json()
    print("\npreview:", r.status_code, d["profession"], "len:", d["length"],
          "placeholders:", d["prompt"].count("{{"))

    # 2) override a template and check the rendered prompt changes
    custom = info["templates"]["dimension_instruction"] + "\n   - 【自定义要求】请额外说明风险点"
    r = c.put("/api/prompts", json={"templates": {"dimension_instruction": custom}})
    print("\nput:", r.status_code, "overridden:", r.json()["overridden"])
    d2 = c.post("/api/prompts/preview", json={"candidate_level": "三级"}).json()
    print("preview contains custom:", "【自定义要求】" in d2["prompt"],
          "| hash changed:", d2["prompt"] != d["prompt"])

    # 3) reset
    r = c.post("/api/prompts/reset")
    print("\nreset:", r.status_code, "overridden:", r.json()["overridden"])
    d3 = c.post("/api/prompts/preview", json={"candidate_level": "三级"}).json()
    print("back to default:", "【自定义要求】" not in d3["prompt"])
