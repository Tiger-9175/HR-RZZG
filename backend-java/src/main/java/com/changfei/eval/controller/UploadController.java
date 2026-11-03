package com.changfei.eval.controller;

import com.changfei.eval.config.AppConfig;
import com.changfei.eval.model.CandidateInfo;
import com.changfei.eval.service.PptParser;
import com.changfei.eval.service.StandardParser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.io.File;
import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class UploadController {
    private static final Logger log = LoggerFactory.getLogger(UploadController.class);
    private final AppConfig config;

    public UploadController(AppConfig config) {
        this.config = config;
    }

    @PostMapping("/upload")
    public Map<String, Object> upload(@RequestParam("file") MultipartFile file) {
        if (file.isEmpty()) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "No file provided");

        String origName = file.getOriginalFilename();
        String ext = "";
        if (origName != null) {
            ext = origName.substring(origName.lastIndexOf('.')).toLowerCase();
        }
        if (!ext.equals(".pptx") && !ext.equals(".ppt") && !ext.equals(".xlsx") && !ext.equals(".xls")) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "不支持的格式: " + ext);
        }

        try {
            File uploadDir = new File("/app", config.getUploadDir());
            uploadDir.mkdirs();
            File dest = new File(uploadDir, origName != null ? origName : "upload" + ext);
            file.transferTo(dest);

            boolean isPpt = ext.equals(".pptx") || ext.equals(".ppt");
            Map<String, Object> resp = new LinkedHashMap<>();
            resp.put("filename", origName);
            resp.put("file_type", isPpt ? "ppt" : "standard");

            if (isPpt) {
                PptParser.ParseResult pr = PptParser.parse(dest.getAbsolutePath());
                // Extract industry from the saved file name (not origName, which
                // may have encoding issues from curl).  公开 冶金_... → 冶金
                String industry = PptParser.extractIndustry(dest.getName());
                pr.candidate.setPosition(industry);
                resp.put("candidate", pr.candidate);
                resp.put("content", pr.markdown);
                resp.put("industry", industry);
                resp.put("message", "PPT解析成功");
            } else {
                StandardParser sp = new StandardParser();
                sp.parse(dest.getAbsolutePath());
                resp.put("content", sp.rawText);
                resp.put("message", "任职资格标准解析成功");
            }
            return resp;
        } catch (Exception e) {
            log.error("Upload/parse error for file: {}", origName, e);
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR,
                    "文件解析失败: " + e.getClass().getSimpleName() + " - " + e.getMessage());
        }
    }
}
