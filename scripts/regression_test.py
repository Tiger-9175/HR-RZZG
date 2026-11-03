"""Verify the consistency regression workflow (mock LLM, no token cost)."""
import json
import sys
import time

import httpx

sys.path.insert(0, ".")

BASE = "http://127.0.0.1:8000"
CASES = [
    "公开 冶金_任职资格认证答辩PPT_程丹_三级.pptx",
    "公开 冶金_任职资格认证答辩PPT_郭楠_三级.pptx",
]

with httpx.Client(base_url=BASE, timeout=300) as c:
    print("mock config:", c.post("/api/config/llm", json={
        "api_key": "sk-mock", "base_url": "http://127.0.0.1:8111/v1",
        "model": "mock-eval"}).status_code)

    r = c.post("/api/regression/run", json={
        "cases": CASES, "repeats": 2, "responsibility_score": 26})
    print("run:", r.status_code)
    job = r.json()
    job_id = job["id"]
    print(f"  job={job_id} total={job['total']} repeats={job['repeats']} hash={job['prompt_hash']}")

    for _ in range(120):
        time.sleep(2)
        detail = c.get(f"/api/regression/jobs/{job_id}").json()
        if detail["status"] != "running":
            break

    print(f"status={detail['status']} progress={detail['progress']}")
    for case in detail["results"]:
        st = case.get("stats") or {}
        print(f"  {case['candidate']} {case['level']} err={case['error'][:40]!r}")
        print(f"    mean={st.get('mean_percentage')} std={st.get('std_percentage')} "
              f"min={st.get('min_percentage')} max={st.get('max_percentage')} "
              f"pass_rate={st.get('pass_rate')} runs={st.get('runs')}")
        print(f"    dims={list((st.get('dimensions') or {}).keys())[:3]}…")

    print("\nsave baseline:", c.post("/api/regression/baseline",
                                    json={"job_id": job_id}).status_code)
    base = c.get("/api/regression/baseline").json()
    print("baseline cases:", list(base["cases"]), "hash:", base["prompt_hash"])

    # simulate drift: shift one baseline mean by +8
    first = CASES[0]
    base["cases"][first]["mean_percentage"] = round(
        base["cases"][first]["mean_percentage"] + 8, 1)
    with open("data/regression_baseline.json", "w", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, indent=2)

    r = c.post("/api/regression/run", json={"cases": [first], "repeats": 1,
                                            "responsibility_score": 26})
    job2 = r.json()["id"]
    for _ in range(120):
        time.sleep(2)
        d2 = c.get(f"/api/regression/jobs/{job2}").json()
        if d2["status"] != "running":
            break
    case = d2["results"][0]
    print("\ndrift check: baseline=", case["baseline"]["mean_percentage"],
          "current=", case["stats"]["mean_percentage"], "delta=", case["delta"])
    print("dimension deltas:", case.get("dimension_delta"))

    print("\njobs list:", len(c.get("/api/regression/jobs").json()["items"]))
    print("delete baseline:", c.delete("/api/regression/baseline").status_code)
    print("baseline after delete:", c.get("/api/regression/baseline").json()["cases"])
