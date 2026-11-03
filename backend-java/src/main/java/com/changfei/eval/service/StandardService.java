package com.changfei.eval.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.io.File;
import java.util.*;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

@Service
public class StandardService {
    private static final Logger log = LoggerFactory.getLogger(StandardService.class);
    private final List<StandardParser> standards = new ArrayList<>();
    private final Map<String, StandardParser> kwMap = new LinkedHashMap<>();

    @PostConstruct
    public void init() { loadAll("demo"); }

    public void loadAll(String demoDir) {
        standards.clear();
        kwMap.clear();
        File dir = new File(demoDir);
        if (!dir.exists() || !dir.isDirectory()) { log.warn("Demo dir not found: {}", demoDir); return; }
        File[] files = dir.listFiles((d, name) ->
                name.contains("任职资格标准") && (name.endsWith(".xlsx") || name.endsWith(".xls")));
        if (files == null) return;
        for (File f : files) {
            StandardParser sp = new StandardParser();
            sp.parse(f.getAbsolutePath());
            standards.add(sp);
            // Register keyword → standard from filename parens AND profession name
            java.util.regex.Matcher m = Pattern.compile("[（(](.+?)[）)]").matcher(f.getName());
            if (m.find()) kwMap.put(m.group(1), sp);
            if (sp.profession != null && !sp.profession.isEmpty()) kwMap.put(sp.profession, sp);
        }
        // Cross-reference aliases for PPTs using different terminology
        addAlias("总装", "系统集成");
        addAlias("铸造", "钣金");
        addAlias("塑形", "钣金");
        addAlias("部装", "部装");  // self-map if already registered

        int total = standards.stream().mapToInt(s -> s.scoringRules.values().stream().mapToInt(List::size).sum()).sum();
        log.info("Loaded {} qualification standards ({} rules, {} keywords)", standards.size(), total, kwMap.size());
    }

    private void addAlias(String from, String to) {
        StandardParser s = kwMap.get(to);
        if (s != null) kwMap.put(from, s);
    }

    public List<StandardParser> getAll() { return standards; }

    public StandardParser findBest(String pptContent, String position, String pptFilename) {
        if (standards.isEmpty()) return null;
        StringBuilder sb = new StringBuilder();
        if (pptContent != null) sb.append(" ").append(pptContent);
        if (pptFilename != null) sb.append(" ").append(pptFilename);
        if (position != null) sb.append(" ").append(position);
        String txt = sb.toString();
        for (Map.Entry<String, StandardParser> e : kwMap.entrySet()) {
            if (!e.getKey().isEmpty() && txt.contains(e.getKey())) {
                log.info("findBest: '{}' => {}", e.getKey(), e.getValue().profession);
                return e.getValue();
            }
        }
        log.info("findBest: fallback to {}", standards.get(0).profession);
        return standards.get(0);
    }

    public List<Map<String, Object>> getStandardInfo() {
        return standards.stream().map(s -> {
            Map<String, Object> info = new LinkedHashMap<>();
            info.put("profession", s.profession);
            info.put("industry", s.industry);
            info.put("title", s.title);
            info.put("filename", s.filename);
            info.put("levels", new ArrayList<>(s.weights.keySet()));
            Map<String, Double> first = s.weights.values().stream().findFirst().orElse(null);
            info.put("dimensions", first != null ? new ArrayList<>(first.keySet()) : new ArrayList<>());
            return info;
        }).collect(Collectors.toList());
    }
}
