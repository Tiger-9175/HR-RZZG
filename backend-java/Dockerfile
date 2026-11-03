# ---- Stage 1: Build frontend ----
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci && npm cache clean --force
COPY frontend/ .
RUN npm run build

# ---- Stage 2: Build backend ----
FROM maven:3.8-eclipse-temurin-8 AS backend-builder
WORKDIR /build
COPY backend-java/pom.xml .
RUN mvn dependency:go-offline -B
COPY backend-java/src ./src
# Copy frontend dist into static resources so Spring Boot serves them natively
COPY --from=frontend-builder /app/frontend/dist ./src/main/resources/static
RUN mvn package -DskipTests -B

# ---- Stage 3: Run ----
# Use non-alpine for proper TLS support (DeepSeek requires modern TLS 1.2+ cipher suites)
FROM eclipse-temurin:8-jre
WORKDIR /app
COPY --from=backend-builder /build/target/hr-rzzg.jar app.jar
COPY demo/ ./demo/
RUN mkdir -p uploads data

EXPOSE 8000
CMD ["java", "-jar", "app.jar"]
