package com.changfei.eval.config;

import com.changfei.eval.service.ConfigPersistence;
import com.changfei.eval.service.LlmClient;
import com.changfei.eval.service.StandardService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.io.File;

@Component
public class StartupInitializer implements CommandLineRunner {
    private static final Logger log = LoggerFactory.getLogger(StartupInitializer.class);

    private final AppConfig config;
    private final LlmClient llm;
    private final StandardService standardService;

    public StartupInitializer(AppConfig config, LlmClient llm, StandardService standardService) {
        this.config = config;
        this.llm = llm;
        this.standardService = standardService;
    }

    @Override
    public void run(String... args) {
        // Load persisted config
        if (ConfigPersistence.exists()) {
            ConfigPersistence.load(config);
            llm.markConfigured();
        }

        // Create dirs
        new File(config.getUploadDir()).mkdirs();
        new File(config.getDataDir()).mkdirs();

        // Load standards
        standardService.loadAll(config.getDemoDir());

        log.info("昌飞任职资格智能评价系统 v1.0.0 started");
        log.info("LLM configured: {}, endpoint: {}", llm.isConfigured(), config.getLlmBaseUrl());
    }
}
