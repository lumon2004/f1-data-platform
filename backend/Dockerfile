# Immagine del backend di F1 Data Platform.
#
# Il contesto di build è la RADICE del repository, perché il jar impacchetta le
# migrazioni di database/migrations (vedi pom.xml):
#
#   docker build -f backend/Dockerfile -t f1-backend .
#
# I test non girano qui (-DskipTests): usano Testcontainers e hanno bisogno di
# Docker, quindi si eseguono fuori dall'immagine con ./mvnw verify.

# ---- Build: JDK 21 + Maven Wrapper ----
FROM eclipse-temurin:21-jdk AS build

# Stessa disposizione del repository: il pom cerca le migrazioni in ../database/migrations.
WORKDIR /workspace/backend

# Prima wrapper e pom: il layer delle dipendenze si rifà solo se cambiano loro.
COPY backend/mvnw ./
COPY backend/.mvn ./.mvn
COPY backend/pom.xml ./
RUN ./mvnw -B -q dependency:go-offline

COPY database/migrations /workspace/database/migrations
COPY backend/src ./src
RUN ./mvnw -B -q -DskipTests package \
    && cp target/backend-*.jar /workspace/app.jar

# ---- Esecuzione: JRE 21 su Alpine, utente non root ----
FROM eclipse-temurin:21-jre-alpine

RUN addgroup -S app && adduser -S -G app app
WORKDIR /app
COPY --from=build /workspace/app.jar ./app.jar

USER app
EXPOSE 8080

# Healthcheck (definito nel Compose): wget di BusyBox è già nell'immagine.
#   wget -q -O /dev/null http://localhost:8080/actuator/health
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
