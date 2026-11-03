package com.changfei.eval.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.HashMap;

public class EvaluationResult {
    private CandidateInfo candidate = new CandidateInfo();
    @JsonProperty("total_score")
    private double totalScore;
    @JsonProperty("total_full_score")
    private double totalFullScore = 100;
    @JsonProperty("total_percentage")
    private double totalPercentage;
    private boolean passed;
    private List<EvaluationDimension> dimensions = new ArrayList<>();
    @JsonProperty("chain_of_thought")
    private String chainOfThought = "";
    private String summary = "";
    private List<String> strengths = new ArrayList<>();
    private List<String> improvements = new ArrayList<>();
    private String suggestions = "";
    @JsonProperty("threshold_check")
    private Map<String, Object> thresholdCheck = new HashMap<>();

    // getters & setters
    public CandidateInfo getCandidate() { return candidate; }
    public void setCandidate(CandidateInfo candidate) { this.candidate = candidate; }
    public double getTotalScore() { return totalScore; }
    public void setTotalScore(double totalScore) { this.totalScore = totalScore; }
    public double getTotalFullScore() { return totalFullScore; }
    public void setTotalFullScore(double totalFullScore) { this.totalFullScore = totalFullScore; }
    public double getTotalPercentage() { return totalPercentage; }
    public void setTotalPercentage(double totalPercentage) { this.totalPercentage = totalPercentage; }
    public boolean isPassed() { return passed; }
    public void setPassed(boolean passed) { this.passed = passed; }
    public List<EvaluationDimension> getDimensions() { return dimensions; }
    public void setDimensions(List<EvaluationDimension> dimensions) { this.dimensions = dimensions; }
    public String getChainOfThought() { return chainOfThought; }
    public void setChainOfThought(String chainOfThought) { this.chainOfThought = chainOfThought; }
    public String getSummary() { return summary; }
    public void setSummary(String summary) { this.summary = summary; }
    public List<String> getStrengths() { return strengths; }
    public void setStrengths(List<String> strengths) { this.strengths = strengths; }
    public List<String> getImprovements() { return improvements; }
    public void setImprovements(List<String> improvements) { this.improvements = improvements; }
    public String getSuggestions() { return suggestions; }
    public void setSuggestions(String suggestions) { this.suggestions = suggestions; }
    public Map<String, Object> getThresholdCheck() { return thresholdCheck; }
    public void setThresholdCheck(Map<String, Object> thresholdCheck) { this.thresholdCheck = thresholdCheck; }
}
