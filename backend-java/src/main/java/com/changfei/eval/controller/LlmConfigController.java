package com.changfei.eval.controller;

import com.changfei.eval.config.AppConfig;
import com.changfei.eval.model.LlmConfigDTO;
import com.changfei.eval.service.LlmClient;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/config/llm")
public class LlmConfigController {
    private final LlmClient llm;
    private final AppConfig config;

    public LlmConfigController(LlmClient llm, AppConfig config) {
        this.llm = llm;
        this.config = config;
    }

    @GetMapping
    public Map<String, Object> getConfig() {
        Map<String, Object> resp = new LinkedHashMap<>();
        resp.put("base_url", config.getLlmBaseUrl());
        resp.put("model", config.getLlmModel());
        resp.put("has_api_key", config.getLlmApiKey() != null &&
                !config.getLlmApiKey().isEmpty() &&
                !config.getLlmApiKey().equals("sk-placeholder"));
        resp.put("configured", llm.isConfigured());
        return resp;
    }

    @PostMapping
    public Map<String, Object> updateConfig(@RequestBody LlmConfigDTO dto) {
        llm.updateConfig(dto.getApiKey(), dto.getBaseUrl(), dto.getModel());
        Map<String, Object> resp = new LinkedHashMap<>();
        resp.put("message", "LLM配置更新成功");
        return resp;
    }

    @PostMapping("/test")
    public Map<String, Object> testConnection(@RequestBody LlmConfigDTO dto) {
        llm.updateConfig(dto.getApiKey(), dto.getBaseUrl(), dto.getModel());
        return llm.testConnection(dto.getApiKey(), dto.getBaseUrl(), dto.getModel());
    }
}
