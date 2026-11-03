package com.changfei.eval.service;

import java.util.*;

public class PromptBuilder {

    public static final String SYSTEM_PROMPT =
            "# 角色定位\n\n" +
            "你是\"任职资格智能评价专家\"，服务于国内大型制造企业的任职资格认证工作。\n\n" +
            "## 核心职责\n\n" +
            "你的唯一职责是对候选人每个评价维度进行评分。不管门槛条件是否满足，\n" +
            "你都必须给出每个维度的具体分数和详细评语。禁止输出空维度数组。\n\n" +
            "## 评价原则\n\n" +
            "1. 客观公正：基于事实和证据进行评价\n" +
            "2. 标准对齐：严格对照提供的任职资格标准进行评分\n" +
            "3. 举证为本：评分必须有候选人的举证材料支撑\n" +
            "4. 全面覆盖：覆盖所有评价维度，一个都不能少\n" +
            "5. 必须评分：即使候选人某项门槛未过，也要基于材料对每个维度独立评分\n\n" +
            "请严格按照标准执行评价，输出JSON格式结果。dimensions数组长度必须等于维度总数。";

    public static String build(StandardParser standard, String pptContent,
                               String candidateLevel, double responsibilityScore) {
        String profession = standard != null ? standard.profession : "未知专业";
        int levelNum = levelToNum(candidateLevel);

        // Build dimension list WITHOUT 责任贡献
        Map<String, Double> allDims = null;
        if (standard != null) allDims = standard.weights.get(levelNum);
        if (allDims == null) allDims = defaultDims();

        Map<String, Double> aiDims = new LinkedHashMap<>();
        double respFullScore = 0;
        for (Map.Entry<String, Double> e : allDims.entrySet()) {
            if (e.getKey().contains("责任贡献") || e.getKey().contains("责任结果")) {
                respFullScore = e.getValue();
            } else if (!e.getKey().contains("基本条件") && !e.getKey().contains("知识与技能")
                    && !e.getKey().contains("通用素质") && !e.getKey().contains("岗位技能")
                    && !e.getKey().contains("流程规范") && !e.getKey().contains("技术知识")
                    && !e.getKey().contains("专业知识")) {
                aiDims.put(e.getKey(), e.getValue());
            }
        }
        if (respFullScore == 0) respFullScore = 30;
        // If filtering removed everything, use defaults
        if (aiDims.isEmpty()) aiDims = defaultDims();

        // Strip ALL threshold/basic-condition content from raw standard
        String rawStd = standard != null ? standard.rawText : "";
        rawStd = stripBasicConditions(rawStd);

        StringBuilder sb = new StringBuilder();
        sb.append("请对以下候选人进行").append(profession).append("专业任职资格评价。\n\n");

        // Manual score
        sb.append("## 手动评分项\n");
        sb.append("责任贡献已由人工评委打分：**").append(responsibilityScore)
                .append(" / ").append((int) respFullScore).append(" 分**。\n");
        sb.append("你在dimensions中不要输出此维度，系统会自动补入。\n\n");

        // Standard (stripped)
        sb.append("## 评价标准\n\n").append(rawStd).append("\n\n");

        // Candidate material
        sb.append("## 候选人材料\n\n").append(pptContent).append("\n\n");

        // Dimensions to score
        sb.append("## 你必须评分的维度（共").append(aiDims.size()).append("个）\n\n");
        int i = 0;
        for (Map.Entry<String, Double> e : aiDims.entrySet()) {
            i++;
            sb.append(i).append(". **").append(e.getKey())
                    .append("** — 满分").append(e.getValue().intValue()).append("分\n");
        }
        sb.append("\n## 评分要求\n\n");
        sb.append("对以上").append(aiDims.size()).append("个维度**逐一打分**。dimensions数组必须包含").append(aiDims.size()).append("个元素，缺一不可。\n");
        sb.append("即使候选人不满足门槛条件，也必须基于PPT中已有的举证材料给予分维度评分。\n");
        sb.append("每个维度都必须填写：name, full_score, threshold, score, score_percentage, comments, details。\n\n");

        sb.append("## JSON格式\n\n```json\n{\n");
        sb.append("  \"candidate\": {\"name\":\"\",\"department\":\"\",\"applied_level\":\"\",\"years_of_experience\":\"\",\"performance_last_two_years\":\"\",\"professional_title\":\"\"},\n");
        sb.append("  \"threshold_check\": {\"performance\":{\"status\":\"\",\"detail\":\"\"},\"professional_title\":{\"status\":\"\",\"detail\":\"\"},\"work_years\":{\"status\":\"\",\"detail\":\"\"},\"organization_contribution\":{\"status\":\"\",\"detail\":\"\"},\"overall_pass\":true},\n");
        sb.append("  \"dimensions\": [{\"name\":\"\",\"full_score\":0,\"threshold\":0,\"score\":0,\"score_percentage\":0,\"comments\":\"\",\"details\":\"\"}],\n");
        sb.append("  \"total_score\":0,\"total_full_score\":0,\"total_percentage\":0,\"passed\":true,\n");
        sb.append("  \"chain_of_thought\":\"\",\"summary\":\"\",\"strengths\":[],\"improvements\":[],\"suggestions\":\"\"\n}\n```\n");

        return sb.toString();
    }

    /** Aggressively strip basic conditions sections to prevent LLM from skipping scoring. */
    private static String stripBasicConditions(String raw) {
        if (raw == null || raw.isEmpty()) return "";
        StringBuilder sb = new StringBuilder();
        boolean inBasicSection = false;
        for (String line : raw.split("\n")) {
            String trimmed = line.trim();
            if (trimmed.startsWith("## 基本条件") || trimmed.startsWith("## 门槛")) {
                inBasicSection = true;
                continue;
            }
            if (inBasicSection && (trimmed.startsWith("## ") || trimmed.startsWith("# "))) {
                inBasicSection = false;
            }
            if (inBasicSection) continue;
            // Remove lines about 基本条件/组织回馈
            if (trimmed.contains("基本条件") && !trimmed.contains("##")) continue;
            sb.append(line).append("\n");
        }
        return sb.toString();
    }

    /** Strip responsibility content from raw standard text. */
    private static String stripResponsibilitySection(String raw) {
        if (raw == null || raw.isEmpty()) return "";
        StringBuilder sb = new StringBuilder();
        for (String line : raw.split("\n")) {
            if (!line.contains("责任贡献") && !line.contains("责任结果")) {
                sb.append(line).append("\n");
            }
        }
        return sb.toString();
    }

    public static Map<String, Double> defaultDims() {
        Map<String, Double> m = new LinkedHashMap<>();
        m.put("洞察规划能力", 5.0);
        m.put("工艺方案设计能力", 25.0);
        m.put("问题识别解决能力", 25.0);
        m.put("总结创新能力", 5.0);
        m.put("沟通协调能力", 10.0);
        return m;
    }

    public static int levelToNum(String s) {
        String[] map = {"", "一", "二", "三", "四", "五", "六"};
        for (int i = 1; i <= 6; i++) {
            if (s.contains(map[i])) return i;
        }
        return 3;
    }
}
