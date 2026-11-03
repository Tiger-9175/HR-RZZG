package com.changfei.eval.service;

import com.changfei.eval.model.CandidateInfo;
import org.apache.poi.openxml4j.util.ZipSecureFile;
import org.apache.poi.xslf.usermodel.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.FileInputStream;
import java.io.InputStream;
import java.util.*;

public class PptParser {
    private static final Logger log = LoggerFactory.getLogger(PptParser.class);

    static {
        // Allow PPTX files with embedded images (high compression ratio)
        // Default 0.01 is too strict for media-heavy PPTX, causing "Zip bomb" error
        ZipSecureFile.setMinInflateRatio(0.001);
    }

    public static class ParseResult {
        public List<String> slides;
        public CandidateInfo candidate;
        public String markdown;
    }

    /** Extract industry keyword from PPT filename e.g. "公开 冶金_..." → "冶金" */
    public static String extractIndustry(String filename) {
        if (filename == null) return "";
        // "公开 INDUSTRY_..." or "公开 INDUSTRY－..."
        java.util.regex.Matcher m = java.util.regex.Pattern.compile(
            "\\u516c\\u5f00[\\s_]*(.+?)[_\\uff0d]").matcher(filename);
        // 公开 = 公开, － = fullwidth dash
        if (m.find()) return m.group(1);
        return "";
    }

    public static ParseResult parse(String filePath) {
        ParseResult result = new ParseResult();
        result.slides = new ArrayList<>();
        result.candidate = new CandidateInfo();

        StringBuilder md = new StringBuilder();
        // Collect all text from first 5 slides for candidate info extraction
        StringBuilder combinedEarlyText = new StringBuilder();

        try (InputStream is = new FileInputStream(filePath);
             XMLSlideShow ppt = new XMLSlideShow(is)) {

            List<XSLFSlide> slideList = ppt.getSlides();

            for (int i = 0; i < slideList.size(); i++) {
                XSLFSlide slide = slideList.get(i);
                StringBuilder slideText = new StringBuilder();

                for (XSLFShape shape : slide.getShapes()) {
                    if (shape instanceof XSLFTextShape) {
                        XSLFTextShape textShape = (XSLFTextShape) shape;
                        String text = textShape.getText();
                        if (text != null && !text.trim().isEmpty()) {
                            slideText.append(text.trim()).append("\n");
                            if (i < 5) {
                                combinedEarlyText.append(text.trim()).append("\n");
                            }
                        }
                    }

                    if (shape instanceof XSLFTable) {
                        XSLFTable table = (XSLFTable) shape;
                        for (XSLFTableRow row : table.getRows()) {
                            for (XSLFTableCell cell : row.getCells()) {
                                String cellText = cell.getText();
                                if (cellText != null && !cellText.trim().isEmpty()) {
                                    slideText.append(cellText.trim()).append(" | ");
                                    if (i < 5) {
                                        combinedEarlyText.append(cellText.trim()).append(" | ");
                                    }
                                }
                            }
                            slideText.append("\n");
                            if (i < 5) combinedEarlyText.append("\n");
                        }
                    }
                }

                String slideContent = slideText.toString().trim();
                if (!slideContent.isEmpty()) {
                    result.slides.add(slideContent);
                    md.append("## Slide ").append(i + 1).append("\n\n");
                    md.append(slideContent).append("\n\n");
                }
            }

            // Extract candidate info from combined text of first 5 slides (like Python version)
            extractCandidateInfo(combinedEarlyText.toString(), result.candidate);

        } catch (Exception e) {
            log.error("Failed to parse PPT: {}", filePath, e);
        }

        result.markdown = md.toString();
        return result;
    }

    private static void extractCandidateInfo(String fullText, CandidateInfo info) {
        // Normalize: collapse whitespace, keep single space separators
        String t = fullText.replaceAll("[\\r\\n]+", " ").replaceAll("\\s{2,}", " ").trim();

        java.util.regex.Matcher m;
        String COLON = "[\\uff1a:]"; // fullwidth + halfwidth colon

        // Name
        m = java.util.regex.Pattern.compile("[姓]名" + COLON + "\\s*(\\S+)").matcher(t);
        if (m.find() && info.getName().isEmpty()) info.setName(m.group(1).trim());

        // Department (所在部门 / 部门 / 单位)
        m = java.util.regex.Pattern.compile("(?:所在部门|部门|单位)" + COLON + "\\s*(\\S+)").matcher(t);
        if (m.find() && info.getDepartment().isEmpty()) info.setDepartment(m.group(1).trim());

        // Applied level (申请认证等级 / 申请等级 / 申请)
        m = java.util.regex.Pattern.compile("(?:申请认证等级|申请等级|申报等级|申请)" + COLON + "\\s*(\\S+)").matcher(t);
        if (m.find() && info.getAppliedLevel().isEmpty()) info.setAppliedLevel(m.group(1).trim());

        // Current level
        m = java.util.regex.Pattern.compile("(?:现有等级|当前等级|现任)" + COLON + "\\s*(\\S+)").matcher(t);
        if (m.find() && info.getCurrentLevel().isEmpty()) info.setCurrentLevel(m.group(1).trim());

        // Years of experience
        m = java.util.regex.Pattern.compile("(?:工作年限|年限|从事专业技术工作)" + COLON + "\\s*(\\S+)").matcher(t);
        if (m.find() && info.getYearsOfExperience().isEmpty()) info.setYearsOfExperience(m.group(1).trim());

        // Performance (近两年度考核结果 / 考核结果 / 近两年绩效)
        m = java.util.regex.Pattern.compile("(?:近两年度考核结果|考核结果|近两年绩效|绩效)" + COLON + "\\s*(\\S+)").matcher(t);
        if (m.find() && info.getPerformanceLastTwoYears().isEmpty()) info.setPerformanceLastTwoYears(m.group(1).trim());

        // Professional title (职称 / 职业资格)
        m = java.util.regex.Pattern.compile("(?:职称|职业资格)" + COLON + "\\s*(\\S+)").matcher(t);
        if (m.find() && info.getProfessionalTitle().isEmpty()) info.setProfessionalTitle(m.group(1).trim());

        // Fallback: try to find name from PPT filename pattern embedded in title
        if (info.getName().isEmpty()) {
            m = java.util.regex.Pattern.compile("[—\\-–]\\s*(\\S{2,4})\\s*$", java.util.regex.Pattern.MULTILINE).matcher(fullText);
            if (m.find()) {
                info.setName(m.group(1).trim());
            }
        }
    }
}
