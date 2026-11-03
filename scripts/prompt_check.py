import sys

sys.path.insert(0, ".")

from app.evaluation import prompts  # noqa: E402
from app.evaluation.criteria import build_evaluation_prompt  # noqa: E402
from app.evaluation.engine import init_standards, get_loaded_standards  # noqa: E402

init_standards("demo")
std = get_loaded_standards()[0]
prompt = build_evaluation_prompt(std, "## 幻灯片 1\n测试材料", "三级", 26)
print("standard:", std.filename, "| length:", len(prompt))
print("unrendered placeholders:", prompt.count("{{"))
print("---- head ----")
print(prompt[:400])
print("---- dim section ----")
start = prompt.find("### 步骤3")
print(prompt[start:start + 420])
print("---- system prompt len ----")
print(len(prompts.system_prompt()), prompts.template_hash(), prompts.template_info()["overridden"])
