"""Temporary OpenAI-compatible mock LLM (port 8111) for regression testing."""
import json
import time

import uvicorn
from fastapi import FastAPI, Request

app = FastAPI()

ANSWER = {
    "candidate": {"name": "程丹", "department": "4车间", "applied_level": "三级",
                  "current_level": "二级", "years_of_experience": "3年",
                  "performance_last_two_years": "B/A", "professional_title": "助理工程师"},
    "threshold_check": {
        "performance": {"status": "✅满足", "detail": "近两年 B/A"},
        "work_years": {"status": "✅满足", "detail": "满3年"},
        "overall_pass": True,
    },
    "dimensions": [
        {"name": "责任贡献", "full_score": 30, "threshold": 18, "score": 26,
         "score_percentage": 86.7, "comments": "人工评分", "details": "[人工评分]"},
        {"name": "洞察规划能力", "full_score": 15, "threshold": 9, "score": 12,
         "score_percentage": 80, "comments": "规划清晰", "details": "风险评估",
         "evidence": [{"page": 3, "quote": "完成型号风险评估报告", "note": "规划能力"}]},
        {"name": "工艺（方案）设计能力", "full_score": 25, "threshold": 15, "score": 20,
         "score_percentage": 80, "comments": "设计规范", "details": "工艺规程",
         "evidence": [{"page": 4, "quote": "完成工艺研究与应用", "note": "设计能力"}]},
        {"name": "问题识别解决能力", "full_score": 15, "threshold": 9, "score": 12,
         "score_percentage": 80, "comments": "定位准确", "details": "迎检",
         "evidence": [{"page": 5, "quote": "以0不符合项通过", "note": "解决能力"}]},
        {"name": "创新能力", "full_score": 10, "threshold": 6, "score": 8,
         "score_percentage": 80, "comments": "有改善", "details": "改造",
         "evidence": [{"page": 6, "quote": "完成真空炉改造", "note": "创新"}]},
        {"name": "沟通协调能力", "full_score": 5, "threshold": 3, "score": 4,
         "score_percentage": 80, "comments": "顺畅", "details": "评审", "evidence": []},
    ],
    "total_score": 82, "total_full_score": 100, "total_percentage": 82, "passed": True,
    "chain_of_thought": "步骤1……步骤2……",
    "summary": "整体达到三级要求。",
    "strengths": ["工艺经验扎实"], "improvements": ["论文不足"],
    "suggestions": "建议牵头课题。",
}


@app.post("/v1/chat/completions")
async def chat(request: Request):
    body = await request.json()
    text = "```json\n" + json.dumps(ANSWER, ensure_ascii=False) + "\n```"
    return {"id": "mock", "object": "chat.completion", "created": int(time.time()),
            "model": body.get("model", "mock"),
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": text}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300}}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8111, log_level="warning")
