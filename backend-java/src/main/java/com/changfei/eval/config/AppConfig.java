package com.changfei.eval.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class AppConfig {
    @Value("${llm.api-key:sk-placeholder}")
    private volatile String llmApiKey;

    @Value("${llm.base-url:http://localhost:8000/v1}")
    private volatile String llmBaseUrl;

    @Value("${llm.model:deepseek-chat}")
    private volatile String llmModel;

    @Value("${llm.max-tokens:8192}")
    private int llmMaxTokens;

    @Value("${llm.temperature:0.3}")
    private double llmTemperature;

    @Value("${app.upload-dir:uploads}")
    private String uploadDir;

    @Value("${app.data-dir:data}")
    private String dataDir;

    @Value("${app.demo-dir:demo}")
    private String demoDir;

    // getters & setters
    public String getLlmApiKey() { return llmApiKey; }
    public void setLlmApiKey(String llmApiKey) { this.llmApiKey = llmApiKey; }
    public String getLlmBaseUrl() { return llmBaseUrl; }
    public void setLlmBaseUrl(String llmBaseUrl) { this.llmBaseUrl = llmBaseUrl; }
    public String getLlmModel() { return llmModel; }
    public void setLlmModel(String llmModel) { this.llmModel = llmModel; }
    public int getLlmMaxTokens() { return llmMaxTokens; }
    public void setLlmMaxTokens(int llmMaxTokens) { this.llmMaxTokens = llmMaxTokens; }
    public double getLlmTemperature() { return llmTemperature; }
    public void setLlmTemperature(double llmTemperature) { this.llmTemperature = llmTemperature; }
    public String getUploadDir() { return uploadDir; }
    public String getDataDir() { return dataDir; }
    public String getDemoDir() { return demoDir; }
}
