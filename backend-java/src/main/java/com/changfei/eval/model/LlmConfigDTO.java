package com.changfei.eval.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public class LlmConfigDTO {
    @JsonProperty("api_key")
    private String apiKey;
    @JsonProperty("base_url")
    private String baseUrl;
    private String model;

    public String getApiKey() { return apiKey; }
    public void setApiKey(String apiKey) { this.apiKey = apiKey; }
    public String getBaseUrl() { return baseUrl; }
    public void setBaseUrl(String baseUrl) { this.baseUrl = baseUrl; }
    public String getModel() { return model; }
    public void setModel(String model) { this.model = model; }
}
