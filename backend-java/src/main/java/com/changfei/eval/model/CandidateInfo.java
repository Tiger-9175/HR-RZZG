package com.changfei.eval.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public class CandidateInfo {
    private String name = "";
    private String department = "";
    private String position = "";
    @JsonProperty("current_level")
    private String currentLevel = "";
    @JsonProperty("applied_level")
    private String appliedLevel = "";
    @JsonProperty("years_of_experience")
    private String yearsOfExperience = "";
    @JsonProperty("performance_last_two_years")
    private String performanceLastTwoYears = "";
    @JsonProperty("professional_title")
    private String professionalTitle = "";

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getDepartment() { return department; }
    public void setDepartment(String department) { this.department = department; }
    public String getPosition() { return position; }
    public void setPosition(String position) { this.position = position; }
    public String getCurrentLevel() { return currentLevel; }
    public void setCurrentLevel(String currentLevel) { this.currentLevel = currentLevel; }
    public String getAppliedLevel() { return appliedLevel; }
    public void setAppliedLevel(String appliedLevel) { this.appliedLevel = appliedLevel; }
    public String getYearsOfExperience() { return yearsOfExperience; }
    public void setYearsOfExperience(String yearsOfExperience) { this.yearsOfExperience = yearsOfExperience; }
    public String getPerformanceLastTwoYears() { return performanceLastTwoYears; }
    public void setPerformanceLastTwoYears(String performanceLastTwoYears) { this.performanceLastTwoYears = performanceLastTwoYears; }
    public String getProfessionalTitle() { return professionalTitle; }
    public void setProfessionalTitle(String professionalTitle) { this.professionalTitle = professionalTitle; }
}
