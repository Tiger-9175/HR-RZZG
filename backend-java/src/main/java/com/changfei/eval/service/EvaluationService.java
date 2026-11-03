package com.changfei.eval.service;

import com.changfei.eval.model.CandidateInfo;
import com.changfei.eval.model.EvaluationDimension;
import com.changfei.eval.model.EvaluationResult;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.*;
import java.util.regex.*;

@Service
public class EvaluationService {
    private static final Logger log = LoggerFactory.getLogger(EvaluationService.class);
    private final LlmClient llm;
    private final StandardService standardService;
    private final ObjectMapper mapper = new ObjectMapper();

    public EvaluationService(LlmClient llm, StandardService standardService) {
        this.llm = llm;
        this.standardService = standardService;
    }

    /** Run a quick basic-conditions check before full evaluation. */
    public Map<String, Object> checkBasicConditions(String pptContent, String candidateLevel,
                                                    String candidatePosition, String pptFilename) throws IOException {
        StandardParser standard = standardService.findBest(pptContent, candidatePosition, pptFilename);
        int levelNum = PromptBuilder.levelToNum(candidateLevel);

        // Extract basic conditions for this level
        Map<String, String> conditions = standard != null
                ? standard.basicConditions.get(levelNum) : null;

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("profession", standard != null ? standard.profession : "未知专业");
        result.put("level", levelNum);

        if (conditions == null || conditions.isEmpty()) {
            result.put("has_conditions", false);
            result.put("message", "该专业未定义基本条件，跳过核查");
            return result;
        }

        result.put("has_conditions", true);

        // Build conditions text
        StringBuilder condText = new StringBuilder();
        for (Map.Entry<String, String> e : conditions.entrySet()) {
            String label = fieldLabel(e.getKey());
            condText.append("- ").append(label).append(": ").append(e.getValue()).append("\n");
        }

        // Quick LLM check
        String prompt = "你是任职资格评价专家。请检查以下候选人是否满足申报等级的基本条件。\n\n"
                + "## 基本条件要求（申报" + candidateLevel + "级）\n" + condText + "\n"
                + "## 候选人材料\n" + pptContent + "\n\n"
                + "请逐条检查每个条件，给出满足/不满足/部分满足的判定和依据。\n"
                + "输出JSON：{\"items\":[{\"field\":\"字段\",\"label\":\"中文名\",\"required\":\"要求\",\"status\":\"✅/❌/⚠️\",\"detail\":\"依据\"}],\"summary\":\"总结\"}。";
        // Only output JSON, no markdown fences

        List<Map<String, String>> messages = new ArrayList<>();
        Map<String, String> sys = new LinkedHashMap<>();
        sys.put("role", "system");
        sys.put("content", "你是一位严格的任职资格评价专家。请基于候选人材料与基本条件逐条比对，给出客观判定。只输出JSON。");
        messages.add(sys);
        Map<String, String> user = new LinkedHashMap<>();
        user.put("role", "user");
        user.put("content", prompt);
        messages.add(user);

        String resp = llm.chat(messages, 0.1, 1024);
        try {
            // Try to extract JSON
            String json = resp;
            Matcher jm = Pattern.compile("```json\\s*\\n?(.+?)\\n?```", Pattern.DOTALL).matcher(resp);
            if (jm.find()) json = jm.group(1);
            @SuppressWarnings("unchecked")
            Map<String, Object> data = mapper.readValue(json, Map.class);
            result.put("items", data.getOrDefault("items", new ArrayList<>()));
            result.put("summary", data.getOrDefault("summary", ""));
        } catch (Exception e) {
            log.warn("Could not parse basic condition check JSON: {}", e.getMessage());
            result.put("items", new ArrayList<>());
            result.put("summary", resp.substring(0, Math.min(500, resp.length())));
        }
        return result;
    }

    /** Full evaluation with CoT reasoning. */
    public EvaluationResult evaluate(String pptContent, String candidateLevel,
                                     String candidatePosition, String pptFilename,
                                     double responsibilityScore) throws IOException {
        StandardParser standard = standardService.findBest(pptContent, candidatePosition, pptFilename);
        String prompt = PromptBuilder.build(standard, pptContent, candidateLevel, responsibilityScore);

        List<Map<String, String>> messages = new ArrayList<>();
        Map<String, String> sys = new LinkedHashMap<>();
        sys.put("role", "system");
        sys.put("content", PromptBuilder.SYSTEM_PROMPT);
        messages.add(sys);

        Map<String, String> user = new LinkedHashMap<>();
        user.put("role", "user");
        user.put("content", prompt);
        messages.add(user);

        String response = llm.chat(messages, 0.3, 8192);
        log.info("LLM raw response length: {} chars, first 300: {}", response != null ? response.length() : 0,
                response != null ? response.substring(0, Math.min(300, response.length())) : "NULL");
        return parseResponse(response, responsibilityScore, standard, PromptBuilder.levelToNum(candidateLevel));
    }

    @SuppressWarnings("unchecked")
    private EvaluationResult parseResponse(String response, double responsibilityScore,
                                           StandardParser standard, int levelNum) {
        EvaluationResult result = new EvaluationResult();
        String jsonStr = response;
        // Flexible JSON extraction: handle ```json ... ```, ```json\n...\n```, or direct { ... }
        Matcher m = Pattern.compile("```json\\s*\\n?(.+?)\\n?```", Pattern.DOTALL).matcher(response);
        if (m.find()) {
            jsonStr = m.group(1);
        } else if (response.trim().startsWith("{")) {
            jsonStr = response.trim();
        }
        log.info("Parsing JSON, length: {} chars.\n---JSON START---\n{}\n---JSON END---", jsonStr.length(), jsonStr.substring(0, Math.min(2000, jsonStr.length())));

        try {
            Map<String, Object> data = mapper.readValue(jsonStr, new TypeReference<Map<String, Object>>() {});
            log.info("JSON parsed successfully. Keys: {}", data.keySet());
            Object dimObj = data.get("dimensions");
            log.info("dimensions field type={}, value={}", dimObj != null ? dimObj.getClass().getSimpleName() : "NULL", dimObj);

            Map<String, Object> candData = (Map<String, Object>) data.getOrDefault("candidate", new LinkedHashMap<>());
            CandidateInfo ci = new CandidateInfo();
            ci.setName(str(candData.get("name")));
            ci.setDepartment(str(candData.get("department")));
            ci.setAppliedLevel(str(candData.get("applied_level")));
            ci.setYearsOfExperience(str(candData.get("years_of_experience")));
            ci.setPerformanceLastTwoYears(str(candData.get("performance_last_two_years")));
            ci.setProfessionalTitle(str(candData.get("professional_title")));
            result.setCandidate(ci);

            List<Map<String, Object>> dimData = (List<Map<String, Object>>) data.getOrDefault("dimensions", new ArrayList<>());
            List<EvaluationDimension> dims = new ArrayList<>();
            for (Map<String, Object> dd : dimData) {
                EvaluationDimension dim = new EvaluationDimension();
                dim.setName(str(dd.get("name")));
                dim.setFullScore(toDouble(dd.get("full_score"), 0));
                dim.setThreshold(toDouble(dd.get("threshold"), 0));
                dim.setScore(toNullableDouble(dd.get("score")));
                dim.setScorePercentage(toNullableDouble(dd.get("score_percentage")));
                dim.setComments(str(dd.get("comments")));
                dim.setDetails(str(dd.get("details")));
                if (dd.get("sub_dimensions") instanceof List)
                    dim.setSubDimensions((List<Object>) dd.get("sub_dimensions"));
                dims.add(dim);
            }

            // If LLM returned empty dimensions (skipped scoring due to threshold failure),
            // fill in default dimensions so user still sees a complete report
            if (dims.isEmpty()) {
                log.warn("LLM returned empty dimensions array! Filling in default dims.");
                dims = buildDefaultDimensions(standard, levelNum);
                log.warn("After fallback, dims size = {}", dims.size());
            }

            if (responsibilityScore > 0) {
                log.info("About to inject manual score {} into {} dimensions", responsibilityScore, dims.size());
                injectManualScore(dims, responsibilityScore);
            }

            Map<String, Object> tc = (Map<String, Object>) data.getOrDefault("threshold_check", new LinkedHashMap<>());
            result.setThresholdCheck(tc);
            boolean tcPass = tc.get("overall_pass") instanceof Boolean ? (Boolean) tc.get("overall_pass") : true;

            result.setDimensions(dims);
            result.setTotalScore(toDouble(data.get("total_score"), 0));
            result.setTotalFullScore(toDouble(data.get("total_full_score"), 100));
            result.setTotalPercentage(toDouble(data.get("total_percentage"), 0));
            result.setPassed(toBool(data.get("passed")) && tcPass);
            result.setChainOfThought(str(data.get("chain_of_thought")));
            result.setSummary(str(data.get("summary")));
            result.setStrengths(strList(data.get("strengths")));
            result.setImprovements(strList(data.get("improvements")));
            result.setSuggestions(str(data.get("suggestions")));
            recalcTotals(result);
        } catch (Exception e) {
            log.warn("Failed to parse JSON from LLM: {}", e.getMessage());
            result.setSummary("系统解析大模型返回结果时遇到问题，请查看原始输出");
            result.setChainOfThought(response.substring(0, Math.min(2000, response.length())));
        }
        return result;
    }

    private List<EvaluationDimension> buildDefaultDimensions(StandardParser standard, int levelNum) {
        // Hardcoded fallback — LLM refused to score (usually because it thinks
        // threshold conditions weren't met). This is a bug in the LLM, not the data.
        log.warn("BUILDING FALLBACK DIMENSIONS — LLM returned empty array. Level={}", levelNum);
        String[][] defaultDefs = {
            {"洞察规划能力", "5", "3"},
            {"工艺方案设计能力", "25", "15"},
            {"问题识别解决能力", "25", "15"},
            {"总结创新能力", "5", "3"},
            {"沟通协调能力", "10", "6"},
        };
        List<EvaluationDimension> dims = new ArrayList<>();
        for (String[] def : defaultDefs) {
            EvaluationDimension d = new EvaluationDimension();
            d.setName(def[0]);
            d.setFullScore(Double.parseDouble(def[1]));
            d.setThreshold(Double.parseDouble(def[2]));
            d.setScore(0.0);
            d.setScorePercentage(0.0);
            d.setComments("模型未返回有效评分，请联系管理员");
            d.setDetails("系统提示：LLM因门槛条件未满足而跳过评分，此为兜底填充。请结合PPT材料人工复核每个维度并给出合理分数。");
            dims.add(d);
        }
        return dims;
    }

    private void injectManualScore(List<EvaluationDimension> dims, double score) {
        log.info("=== Dimensions from LLM ({} total, score injection={}) ===", dims.size(), score);
        for (int i = 0; i < dims.size(); i++) {
            EvaluationDimension d = dims.get(i);
            log.info("  [{}] name='{}', full={}, score={}, threshold={}",
                    i, d.getName(), d.getFullScore(), d.getScore(), d.getThreshold());
        }

        // Remove responsibility-like dims — EXACT match only, no fuzzy rules
        dims.removeIf(d -> {
            String n = d.getName();
            if (n == null) return false;
            String clean = n.replaceAll("\\s+", "").replaceAll("[（）\\(\\)]", "");
            // Only exact matches: 责任贡献, 责任结果, or 绩效贡献 (all mean the same concept)
            boolean isResp = clean.equals("责任贡献") || clean.equals("责任结果")
                    || clean.equals("绩效贡献");
            if (isResp)
                log.info("  -> Removing LLM responsibility dim: '{}' (full={}, score={})", n, d.getFullScore(), d.getScore());
            return isResp;
        });

        // Inject official manual score
        EvaluationDimension d = new EvaluationDimension();
        d.setName("责任贡献");
        d.setFullScore(30);
        d.setThreshold(18);
        d.setScore(score);
        d.setScorePercentage(score > 0 ? Math.round(score / 30 * 1000.0) / 10.0 : 0);
        d.setComments("此项由人工评委打分（手动评分）");
        d.setDetails("[人工评分]");
        dims.add(0, d);

        log.info("=== After dedup + inject: {} dimensions ===", dims.size());
        for (int i = 0; i < dims.size(); i++) {
            EvaluationDimension dd = dims.get(i);
            log.info("  [{}] name='{}', full={}, score={}", i, dd.getName(), dd.getFullScore(), dd.getScore());
        }
    }

    private void recalcTotals(EvaluationResult r) {
        double totalFull = r.getDimensions().stream().mapToDouble(EvaluationDimension::getFullScore).sum();
        double totalScore = r.getDimensions().stream().mapToDouble(dim -> dim.getScore() != null ? dim.getScore() : 0).sum();
        r.setTotalFullScore(totalFull);
        r.setTotalScore(Math.round(totalScore * 10.0) / 10.0);
        r.setTotalPercentage(totalFull > 0 ? Math.round(totalScore / totalFull * 1000.0) / 10.0 : 0);
        boolean allMet = r.getDimensions().stream()
                .filter(dim -> dim.getThreshold() > 0 && dim.getScore() != null)
                .allMatch(dim -> dim.getScore() >= dim.getThreshold());
        r.setPassed(r.isPassed() && allMet);
    }

    // ---- helpers ----
    static String fieldLabel(String key) {
        switch (key) {
            case "performance": return "绩效要求";
            case "certification": return "职业资格";
            case "work_years": return "技术工作年限";
            case "feedback": return "组织回馈";
            default: return key;
        }
    }
    private static String str(Object o) { return o != null ? o.toString() : ""; }
    private static double toDouble(Object o, double def) {
        if (o instanceof Number) return ((Number) o).doubleValue();
        if (o instanceof String) try { return Double.parseDouble((String) o); } catch (Exception e) {}
        return def;
    }
    private static Double toNullableDouble(Object o) {
        if (o == null) return null;
        if (o instanceof Number) return ((Number) o).doubleValue();
        if (o instanceof String && !((String) o).isEmpty()) try { return Double.parseDouble((String) o); } catch (Exception e) {}
        return null;
    }
    private static boolean toBool(Object o) { return o instanceof Boolean ? (Boolean) o : false; }
    @SuppressWarnings("unchecked")
    private static List<String> strList(Object o) {
        if (o instanceof List) {
            List<String> res = new ArrayList<>();
            for (Object item : (List<Object>) o) res.add(item != null ? item.toString() : "");
            return res;
        }
        return new ArrayList<>();
    }
}
