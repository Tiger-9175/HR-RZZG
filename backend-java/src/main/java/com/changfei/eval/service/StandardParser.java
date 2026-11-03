package com.changfei.eval.service;

import org.apache.poi.openxml4j.util.ZipSecureFile;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.apache.poi.hssf.usermodel.HSSFWorkbook;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.util.*;
import java.util.regex.*;

public class StandardParser {
    private static final Logger log = LoggerFactory.getLogger(StandardParser.class);

    static {
        ZipSecureFile.setMinInflateRatio(0.001);
    }

    public String profession = "";
    public String industry = "";
    public String title = "";
    public String filename = "";
    public Map<Integer, Map<String, String>> basicConditions = new LinkedHashMap<>();
    public Map<Integer, Map<String, Double>> weights = new LinkedHashMap<>();
    public Map<Integer, List<Map<String, Object>>> scoringRules = new LinkedHashMap<>();
    public String rawText = "";

    private static final String[] LEVEL_CN = {"", "一", "二", "三", "四", "五", "六"};

    public void parse(String filePath) {
        this.filename = new File(filePath).getName();
        try {
            Map<String, List<List<String>>> sheets = readAllSheets(filePath);
            parseProfession(sheets);
            parseWeights(sheets);
            parseBasicConditions(sheets);
            parseLevelRules(sheets);
            buildRawText();
            log.info("Loaded standard: {} ({} levels, {} rules)",
                    profession, weights.size(),
                    scoringRules.values().stream().mapToInt(List::size).sum());
        } catch (Exception e) {
            log.error("Failed to parse standard {}: {}", filePath, e.getMessage(), e);
        }
    }

    private Map<String, List<List<String>>> readAllSheets(String filePath) throws Exception {
        Map<String, List<List<String>>> result = new LinkedHashMap<>();
        try (InputStream is = new FileInputStream(filePath);
             Workbook wb = filePath.endsWith(".xls") ?
                     new HSSFWorkbook(is) : new XSSFWorkbook(is)) {
            for (int i = 0; i < wb.getNumberOfSheets(); i++) {
                Sheet sheet = wb.getSheetAt(i);
                List<List<String>> rows = new ArrayList<>();
                for (Row row : sheet) {
                    List<String> cells = new ArrayList<>();
                    for (int c = 0; c < row.getLastCellNum(); c++) {
                        cells.add(getCellValue(row.getCell(c)));
                    }
                    if (cells.stream().anyMatch(s -> !s.isEmpty())) {
                        rows.add(cells);
                    }
                }
                result.put(sheet.getSheetName(), rows);
            }
        }
        return result;
    }

    private static String getCellValue(Cell cell) {
        if (cell == null) return "";
        try {
            switch (cell.getCellType()) {
                case STRING: return cell.getStringCellValue().trim();
                case NUMERIC: {
                    double v = cell.getNumericCellValue();
                    if (v == Math.floor(v) && !Double.isInfinite(v)) return String.valueOf((int) v);
                    return String.valueOf(v);
                }
                case BOOLEAN: return String.valueOf(cell.getBooleanCellValue());
                case FORMULA:
                    try { return String.valueOf(cell.getNumericCellValue()); }
                    catch (Exception e1) {
                        try { return cell.getStringCellValue().trim(); }
                        catch (Exception e2) { return cell.getCellFormula(); }
                    }
                default: return "";
            }
        } catch (Exception e) {
            // Return empty for any unreadable cell (e.g. ERROR type)
            return "";
        }
    }

    private void parseProfession(Map<String, List<List<String>>> sheets) {
        for (String sn : sheets.keySet()) {
            if (sn.contains("任职资格标准")) {
                List<List<String>> rows = sheets.get(sn);
                if (rows.size() > 1 && !rows.get(1).isEmpty()) {
                    String t = rows.get(1).get(0);
                    Matcher m = Pattern.compile("专业技术序列[—\\-](.+?)(?:专业|加工)?[—\\-]任职资格标准").matcher(t);
                    if (m.find()) {
                        this.profession = m.group(1).trim();
                    }
                }
            }
        }
        if (profession.isEmpty()) profession = "未知";
        this.industry = profession;
        this.title = profession + "专业";
    }

    private void parseBasicConditions(Map<String, List<List<String>>> sheets) {
        for (String sn : sheets.keySet()) {
            if (!sn.contains("任职资格标准")) continue;
            List<List<String>> rows = sheets.get(sn);
            // Find header row with 级
            int hr = -1;
            Map<Integer, Integer> colLevel = new LinkedHashMap<>();
            for (int r = 0; r < rows.size(); r++) {
                List<String> row = rows.get(r);
                for (int c = 0; c < row.size(); c++) {
                    for (int lv = 1; lv <= 6; lv++) {
                        if (row.get(c).contains(LEVEL_CN[lv] + "级")) {
                            colLevel.put(c, lv);
                        }
                    }
                }
                if (!colLevel.isEmpty()) { hr = r; break; }
            }
            if (hr < 0) continue;

            for (int r = hr + 1; r < rows.size(); r++) {
                List<String> row = rows.get(r);
                if (row.size() < 3) continue;
                String field = findField(row.get(2));
                if (field.isEmpty()) continue;
                for (Map.Entry<Integer, Integer> e : colLevel.entrySet()) {
                    if (e.getKey() < row.size()) {
                        String val = row.get(e.getKey()).trim();
                        if (!val.isEmpty() && !val.equals("—") && !val.equals("/")) {
                            basicConditions.computeIfAbsent(e.getValue(), k -> new LinkedHashMap<>())
                                    .put(field, val);
                        }
                    }
                }
            }
        }
    }

    private String findField(String s) {
        if (s.contains("绩效")) return "performance";
        if (s.contains("职业资格")) return "certification";
        if (s.contains("工作年限")) return "work_years";
        if (s.contains("回馈")) return "feedback";
        return "";
    }

    private void parseWeights(Map<String, List<List<String>>> sheets) {
        for (String sn : sheets.keySet()) {
            if (!sn.contains("分值权重")) continue;
            List<List<String>> rows = sheets.get(sn);
            int hr = -1;
            Map<Integer, Integer> colLevel = new LinkedHashMap<>();
            for (int r = 0; r < rows.size(); r++) {
                List<String> row = rows.get(r);
                for (int c = 0; c < row.size(); c++) {
                    for (int lv = 1; lv <= 6; lv++) {
                        if (row.get(c).contains(LEVEL_CN[lv] + "级")) {
                            colLevel.put(c, lv);
                        }
                    }
                }
                if (!colLevel.isEmpty()) { hr = r; break; }
            }
            if (hr < 0) continue;

            for (int r = hr + 1; r < rows.size(); r++) {
                List<String> row = rows.get(r);
                String dim = findDimName(row);
                if (dim.isEmpty()) continue;
                for (Map.Entry<Integer, Integer> e : colLevel.entrySet()) {
                    if (e.getKey() < row.size()) {
                        Double w = parseNum(row.get(e.getKey()));
                        if (w != null && w > 0) {
                            weights.computeIfAbsent(e.getValue(), k -> new LinkedHashMap<>())
                                    .put(dim, w);
                        }
                    }
                }
            }
        }
    }

    private String findDimName(List<String> row) {
        for (String v : row) {
            if (v.contains("能力") || v.contains("贡献") || v.contains("结果"))
                return v.replaceAll("\\s+", "");
        }
        return "";
    }

    private void parseLevelRules(Map<String, List<List<String>>> sheets) {
        for (int lv = 1; lv <= 6; lv++) {
            for (String sn : sheets.keySet()) {
                if (!sn.contains(LEVEL_CN[lv] + "级")) continue;
                List<List<String>> rows = sheets.get(sn);
                parseOneLevelRules(rows, lv);
                break;
            }
        }
    }

    private void parseOneLevelRules(List<List<String>> rows, int level) {
        int hr = -1;
        for (int r = 0; r < rows.size(); r++) {
            List<String> row = rows.get(r);
            for (String c : row) {
                if (c.contains("标准") || c.contains("考察点")) { hr = r; break; }
            }
            if (hr >= 0) break;
        }
        if (hr < 0) return;

        // Column mapping
        Map<String, Integer> cols = new LinkedHashMap<>();
        List<String> header = rows.get(hr);
        for (int c = 0; c < header.size(); c++) {
            String v = header.get(c);
            if (v.contains("标准")) cols.put("standard", c);
            if (v.contains("考察点")) cols.put("criteria", c);
            if (v.contains("举证")) cols.put("evidence", c);
            if (v.contains("分值")) cols.put("score", c);
            if (v.contains("达标")) cols.put("threshold", c);
            if (v.contains("打分")) cols.put("rules", c);
        }

        List<Map<String, Object>> rules = new ArrayList<>();
        String currentDim = "";
        for (int r = hr + 1; r < rows.size(); r++) {
            List<String> row = rows.get(r);
            if (row.stream().allMatch(String::isEmpty)) continue;

            // Track dimension from first columns
            for (int c = 0; c < Math.min(3, row.size()); c++) {
                String v = row.get(c);
                if (v.contains("基本条件") || v.contains("责任贡献") || v.contains("关键能力")) {
                    currentDim = v;
                }
            }

            Map<String, Object> entry = new LinkedHashMap<>();
            entry.put("dimension", currentDim);
            entry.put("standard", getCol(row, cols, "standard"));
            entry.put("criteria", getCol(row, cols, "criteria"));
            entry.put("evidence", getCol(row, cols, "evidence"));

            Double score = parseNum(getCol(row, cols, "score"));
            entry.put("max_score", score != null ? score : 0);
            Double threshold = parseNum(getCol(row, cols, "threshold"));
            entry.put("threshold", threshold != null ? threshold : 0);
            entry.put("scoring_rules", getCol(row, cols, "rules"));

            String std = (String) entry.get("standard");
            String crit = (String) entry.get("criteria");
            if (!std.isEmpty() || !crit.isEmpty()) {
                rules.add(entry);
            }
        }
        if (!rules.isEmpty()) scoringRules.put(level, rules);
    }

    private String getCol(List<String> row, Map<String, Integer> cols, String key) {
        Integer idx = cols.get(key);
        return idx != null && idx < row.size() ? row.get(idx) : "";
    }

    static Double parseNum(String s) {
        if (s == null || s.isEmpty()) return null;
        s = s.replaceAll("[—\\s]", "").trim();
        if (s.isEmpty()) return null;
        try { return Double.parseDouble(s); }
        catch (NumberFormatException e) { return null; }
    }

    private void buildRawText() {
        StringBuilder sb = new StringBuilder();
        sb.append("专业: ").append(profession).append("\n");

        if (!basicConditions.isEmpty()) {
            sb.append("\n## 基本条件（门槛）\n");
            for (Map.Entry<Integer, Map<String, String>> e : basicConditions.entrySet()) {
                sb.append("  ").append(e.getKey()).append("级: ");
                for (Map.Entry<String, String> f : e.getValue().entrySet()) {
                    sb.append(f.getKey()).append(": ").append(f.getValue()).append(" | ");
                }
                sb.append("\n");
            }
        }

        if (!weights.isEmpty()) {
            sb.append("\n## 分值权重分配\n");
            for (Map.Entry<Integer, Map<String, Double>> e : weights.entrySet()) {
                sb.append(e.getKey()).append("级: ");
                for (Map.Entry<String, Double> w : e.getValue().entrySet()) {
                    sb.append(w.getKey()).append("=").append(w.getValue().intValue()).append("分 ");
                }
                sb.append("\n");
            }
        }

        for (int lv = 1; lv <= 6; lv++) {
            List<Map<String, Object>> rules = scoringRules.get(lv);
            if (rules == null) continue;
            sb.append("\n## ").append(lv).append("级评分细则\n");
            for (Map<String, Object> r : rules) {
                sb.append("- ").append(r.get("dimension")).append(": max=")
                        .append(r.get("max_score")).append(" threshold=").append(r.get("threshold")).append("\n");
                String std = (String) r.get("standard");
                if (std != null && !std.isEmpty()) sb.append("  标准: ").append(std.substring(0, Math.min(300, std.length()))).append("\n");
            }
        }
        this.rawText = sb.toString();
    }
}
