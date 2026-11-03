package com.changfei.eval.service;

import com.changfei.eval.config.AppConfig;
import com.fasterxml.jackson.databind.ObjectMapper;
import okhttp3.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.*;
import java.util.concurrent.TimeUnit;

@Service
public class LlmClient {
    private static final Logger log = LoggerFactory.getLogger(LlmClient.class);

    private final AppConfig config;
    private final ObjectMapper mapper = new ObjectMapper();
    private OkHttpClient httpClient;

    private volatile boolean configured = false;

    public LlmClient(AppConfig config) {
        this.config = config;
        this.httpClient = buildClient();
    }

    private OkHttpClient buildClient() {
        return new OkHttpClient.Builder()
                .connectTimeout(30, TimeUnit.SECONDS)
                .readTimeout(300, TimeUnit.SECONDS)
                .writeTimeout(30, TimeUnit.SECONDS)
                .build();
    }

    public boolean isConfigured() {
        return configured;
    }

    public void markConfigured() {
        this.configured = true;
    }

    public void updateConfig(String apiKey, String baseUrl, String model) {
        config.setLlmApiKey(apiKey);
        config.setLlmBaseUrl(baseUrl);
        config.setLlmModel(model);
        this.configured = true;
        // Persist config
        ConfigPersistence.save(config);
    }

    public Map<String, Object> testConnection(String apiKey, String baseUrl, String model) {
        Map<String, Object> result = new LinkedHashMap<>();
        try {
            String url = (baseUrl != null ? baseUrl : "").trim();
            if (!url.endsWith("/")) url += "/";
            url += "chat/completions";

            Map<String, Object> body = new LinkedHashMap<>();
            body.put("model", model != null ? model : "deepseek-chat");
            body.put("max_tokens", 1);
            body.put("temperature", 0);
            List<Map<String, String>> msgs = new ArrayList<>();
            Map<String, String> msg = new LinkedHashMap<>();
            msg.put("role", "user");
            msg.put("content", "Hi");
            msgs.add(msg);
            body.put("messages", msgs);

            String json = mapper.writeValueAsString(body);
            Request request = new Request.Builder()
                    .url(url)
                    .header("Authorization", "Bearer " + (apiKey != null ? apiKey : ""))
                    .header("Content-Type", "application/json")
                    .post(RequestBody.create(json, okhttp3.MediaType.get("application/json")))
                    .build();

            try (Response response = httpClient.newCall(request).execute()) {
                if (response.isSuccessful()) {
                    result.put("ok", true);
                    result.put("message", "连接成功，模型响应正常");
                    result.put("model", model);
                } else {
                    String err = "";
                    try {
                        okhttp3.ResponseBody rb = response.body();
                        if (rb != null) err = rb.string();
                    } catch (Exception ignored) {}
                    result.put("ok", false);
                    result.put("message", parseError(response.code(), err != null ? err : ""));
                }
            }
        } catch (Exception e) {
            result.put("ok", false);
            result.put("message", classifyException(e));
        }
        return result;
    }

    public String chat(List<Map<String, String>> messages, double temperature, int maxTokens) throws IOException {
        if (!configured) {
            throw new RuntimeException("LLM 未配置");
        }

        String url = config.getLlmBaseUrl();
        if (!url.endsWith("/")) url += "/";
        url += "chat/completions";

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("model", config.getLlmModel());
        body.put("messages", messages);
        body.put("temperature", temperature);
        body.put("max_tokens", maxTokens);

        String json = mapper.writeValueAsString(body);
        Request request = new Request.Builder()
                .url(url)
                .header("Authorization", "Bearer " + config.getLlmApiKey())
                .header("Content-Type", "application/json")
                .post(RequestBody.create(json, MediaType.get("application/json")))
                .build();

        try (Response response = httpClient.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                String err = response.body() != null ? response.body().string() : "";
                throw new RuntimeException("LLM API error " + response.code() + ": " + err);
            }
            String respBody = response.body().string();
            return extractContent(respBody);
        }
    }

    @SuppressWarnings("unchecked")
    private String extractContent(String respBody) throws IOException {
        Map<String, Object> resp = mapper.readValue(respBody, Map.class);
        List<Map<String, Object>> choices = (List<Map<String, Object>>) resp.get("choices");
        if (choices != null && !choices.isEmpty()) {
            Map<String, Object> message = (Map<String, Object>) choices.get(0).get("message");
            if (message != null) {
                return (String) message.getOrDefault("content", "");
            }
        }
        return "";
    }

    private String parseError(int code, String body) {
        if (code == 401) return "API Key 无效或未授权，请检查 Key";
        if (code == 404) return "接口地址不存在 (404)，请检查 Base URL 是否正确";
        if (code == 429) return "请求频率过高或余额不足，请稍后再试";
        String detail = body != null ? body.substring(0, Math.min(200, body.length())) : "";
        return "API 返回 " + code + " 错误: " + detail;
    }

    private String classifyException(Exception e) {
        String msg = e.getMessage();
        if (msg == null) msg = "";
        if (msg.contains("401") || msg.contains("Unauthorized") || msg.contains("Invalid API Key"))
            return "API Key 无效或未授权，请检查 Key";
        if (msg.contains("404") || msg.contains("not found"))
            return "接口地址不存在 (404)，请检查 Base URL 是否正确";
        if (msg.contains("429"))
            return "请求频率过高或余额不足，请稍后再试";
        if (msg.contains("resolve") || msg.contains("Name or service not known") || msg.contains("UnknownHost") || msg.contains("not known"))
            return "无法解析服务器地址，请检查 Base URL 是否正确";
        if (msg.contains("connect") || msg.contains("timeout") || msg.contains("handshake"))
            return "无法连接到服务器，请检查 URL 地址是否可访问";
        return "连接失败: " + msg.substring(0, Math.min(200, msg.length()));
    }
}
