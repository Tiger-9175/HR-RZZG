package com.changfei.eval.controller;

import com.changfei.eval.model.CandidateInfo;
import com.changfei.eval.service.PptParser;
import com.changfei.eval.service.StandardParser;
import com.changfei.eval.service.StandardService;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.io.File;
import java.util.*;

@RestController
@RequestMapping("/api/demo")
public class DemoController {
    private final StandardService standardService;

    public DemoController(StandardService standardService) {
        this.standardService = standardService;
    }

    @GetMapping("/files")
    public Map<String, Object> listFiles() {
        Map<String, List<Map<String, Object>>> grouped = new LinkedHashMap<>();
        grouped.put("ppt", new ArrayList<>());
        grouped.put("standard", new ArrayList<>());
        grouped.put("job_desc", new ArrayList<>());

        File demoDir = new File("demo");
        if (!demoDir.exists() || !demoDir.isDirectory()) {
            Map<String, Object> resp = new LinkedHashMap<>();
            resp.put("files", grouped);
            return resp;
        }

        File[] files = demoDir.listFiles((d, name) ->
                name.endsWith(".pptx") || name.endsWith(".ppt") ||
                name.endsWith(".xlsx") || name.endsWith(".xls"));
        if (files == null) {
            Map<String, Object> resp = new LinkedHashMap<>();
            resp.put("files", grouped);
            return resp;
        }

        for (File f : files) {
            Map<String, Object> entry = new LinkedHashMap<>();
            entry.put("name", f.getName());
            entry.put("size", f.length());

            String name = f.getName().toLowerCase();
            if (name.endsWith(".pptx") || name.endsWith(".ppt")) {
                entry.put("type", "ppt");
                grouped.get("ppt").add(entry);
            } else if (name.contains("职位说明书") || name.contains("说明")) {
                entry.put("type", "job_desc");
                grouped.get("job_desc").add(entry);
            } else {
                entry.put("type", "standard");
                grouped.get("standard").add(entry);
            }
        }

        // Sort by name
        for (List<Map<String, Object>> list : grouped.values()) {
            list.sort(Comparator.comparing(m -> (String) m.get("name")));
        }

        Map<String, Object> resp = new LinkedHashMap<>();
        resp.put("files", grouped);
        return resp;
    }

    @GetMapping("/load")
    public Map<String, Object> loadFile(@RequestParam("filename") String filename) {
        File file = new File("demo", filename);
        if (!file.exists()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Demo file not found: " + filename);

        try {
            String name = file.getName().toLowerCase();
            Map<String, Object> resp = new LinkedHashMap<>();
            resp.put("filename", filename);

            if (name.endsWith(".pptx") || name.endsWith(".ppt")) {
                PptParser.ParseResult pr = PptParser.parse(file.getAbsolutePath());
                resp.put("file_type", "ppt");
                resp.put("candidate", pr.candidate);
                resp.put("content", pr.markdown);
            } else {
                StandardParser sp = new StandardParser();
                sp.parse(file.getAbsolutePath());
                resp.put("file_type", "standard");
                resp.put("content", sp.rawText);
            }
            return resp;
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "解析失败: " + e.getMessage());
        }
    }

    @GetMapping("/standards")
    public Map<String, Object> listStandards() {
        List<Map<String, Object>> infos = standardService.getStandardInfo();
        Map<String, Object> resp = new LinkedHashMap<>();
        resp.put("standards", infos);
        resp.put("count", infos.size());
        return resp;
    }
}
