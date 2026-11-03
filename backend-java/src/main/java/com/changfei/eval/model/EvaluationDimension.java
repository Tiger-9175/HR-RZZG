package com.changfei.eval.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.ArrayList;
import java.util.List;

public class EvaluationDimension {
    private String name = "";
    @JsonProperty("full_score")
    private double fullScore;
    private double threshold;
    private Double score;
    @JsonProperty("score_percentage")
    private Double scorePercentage;
    private String comments = "";
    private String details = "";
    @JsonProperty("sub_dimensions")
    private List<Object> subDimensions = new ArrayList<>();

    // getters & setters
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public double getFullScore() { return fullScore; }
    public void setFullScore(double fullScore) { this.fullScore = fullScore; }
    public double getThreshold() { return threshold; }
    public void setThreshold(double threshold) { this.threshold = threshold; }
    public Double getScore() { return score; }
    public void setScore(Double score) { this.score = score; }
    public Double getScorePercentage() { return scorePercentage; }
    public void setScorePercentage(Double scorePercentage) { this.scorePercentage = scorePercentage; }
    public String getComments() { return comments; }
    public void setComments(String comments) { this.comments = comments; }
    public String getDetails() { return details; }
    public void setDetails(String details) { this.details = details; }
    public List<Object> getSubDimensions() { return subDimensions; }
    public void setSubDimensions(List<Object> subDimensions) { this.subDimensions = subDimensions; }
}
