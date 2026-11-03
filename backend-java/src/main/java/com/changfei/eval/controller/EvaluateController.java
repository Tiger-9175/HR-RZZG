package com.changfei.eval.controller;

import com.changfei.eval.model.EvaluationResult;
import com.changfei.eval.service.EvaluationService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.Map;

@RestController
@RequestMapping("/api")
public class EvaluateController {
    private static final Logger log = LoggerFactory.getLogger(EvaluateController.class);
    private final EvaluationService evalService;

    public EvaluateController(EvaluationService evalService) {
        this.evalService = evalService;
    }

    @PostMapping("/evaluate/precheck")
    public Map<String, Object> precheck(
            @RequestParam("ppt_content") String pptContent,
            @RequestParam(value = "candidate_level", defaultValue = "三级") String candidateLevel,
            @RequestParam(value = "candidate_position", defaultValue = "") String candidatePosition,
            @RequestParam(value = "ppt_filename", defaultValue = "") String pptFilename) {
        try {
            return evalService.checkBasicConditions(pptContent, candidateLevel, candidatePosition, pptFilename);
        } catch (Exception e) {
            log.error("Precheck failed", e);
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR,
                    "基本条件核查失败: " + e.getMessage());
        }
    }

    @PostMapping("/evaluate")
    public EvaluationResult evaluate(
            @RequestParam("ppt_content") String pptContent,
            @RequestParam(value = "qualification_standard", defaultValue = "") String standardText,
            @RequestParam(value = "candidate_level", defaultValue = "三级") String candidateLevel,
            @RequestParam(value = "candidate_position", defaultValue = "") String candidatePosition,
            @RequestParam(value = "responsibility_score", defaultValue = "0") String respScore,
            @RequestParam(value = "ppt_filename", defaultValue = "") String pptFilename) {

        double score = 0;
        try { score = Double.parseDouble(respScore); } catch (NumberFormatException ignored) {}

        try {
            return evalService.evaluate(pptContent, candidateLevel, candidatePosition, pptFilename, score);
        } catch (Exception e) {
            log.error("Evaluation failed", e);
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR,
                    "评价失败: " + e.getMessage());
        }
    }
}
