package com.changfei.eval.controller;

import com.changfei.eval.config.AppConfig;
import com.changfei.eval.service.LlmClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
public class HealthController {
    private final LlmClient llm;
    private final AppConfig config;

    public HealthController(LlmClient llm, AppConfig config) {
        this.llm = llm;
        this.config = config;
    }

    @GetMapping("/api/health")
    public Map<String, Object> health() {
        Map<String, Object> resp = new LinkedHashMap<>();
        resp.put("status", "ok");
        resp.put("app", "昌飞任职资格智能评价系统");
        resp.put("version", "1.0.0");
        resp.put("llm_configured", llm.isConfigured());
        resp.put("llm_base_url", config.getLlmBaseUrl());
        resp.put("llm_model", config.getLlmModel());
        return resp;
    }
}
