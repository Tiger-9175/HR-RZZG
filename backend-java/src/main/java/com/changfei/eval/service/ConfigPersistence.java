package com.changfei.eval.service;

import com.changfei.eval.config.AppConfig;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.LinkedHashMap;
import java.util.Map;

public class ConfigPersistence {
    private static final Logger log = LoggerFactory.getLogger(ConfigPersistence.class);
    private static final ObjectMapper mapper = new ObjectMapper();
    static final String CONFIG_FILE = "data/llm_config.json";

    public static void load(AppConfig config) {
        File f = new File(CONFIG_FILE);
        if (!f.exists()) return;
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> data = mapper.readValue(f, Map.class);
            String key = (String) data.get("llm_api_key");
            String url = (String) data.get("llm_base_url");
            String model = (String) data.get("llm_model");
            if (key != null) config.setLlmApiKey(key);
            if (url != null) config.setLlmBaseUrl(url);
            if (model != null) config.setLlmModel(model);
            log.info("Loaded LLM config from {}: model={}, url={}", CONFIG_FILE, config.getLlmModel(), config.getLlmBaseUrl());
        } catch (Exception e) {
            log.warn("Failed to load config file: {}", e.getMessage());
        }
    }

    public static void save(AppConfig config) {
        try {
            new File("data").mkdirs();
            Map<String, String> data = new LinkedHashMap<>();
            data.put("llm_api_key", config.getLlmApiKey());
            data.put("llm_base_url", config.getLlmBaseUrl());
            data.put("llm_model", config.getLlmModel());
            mapper.writerWithDefaultPrettyPrinter().writeValue(new File(CONFIG_FILE), data);
            log.info("Saved LLM config to {}", CONFIG_FILE);
        } catch (Exception e) {
            log.warn("Failed to save config file: {}", e.getMessage());
        }
    }

    public static boolean exists() {
        return new File(CONFIG_FILE).exists();
    }
}
