package com.changfei.eval.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.io.File;

@Configuration
public class StaticResourceConfig implements WebMvcConfigurer {
    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        File dist = new File("frontend/dist");
        if (dist.exists() && dist.isDirectory()) {
            registry.addResourceHandler("/**")
                    .addResourceLocations("file:frontend/dist/")
                    .setCachePeriod(0);
        }
    }
}
