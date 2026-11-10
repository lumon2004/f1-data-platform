package com.f1dataplatform.backend;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import org.flywaydb.core.Flyway;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.Network;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.containers.startupcheck.OneShotStartupCheckStrategy;
import org.testcontainers.images.builder.ImageFromDockerfile;

/**
 * Base dei test di integrazione: avvia l'applicazione contro un PostgreSQL reale (Testcontainers)
 * caricato con il dataset di esempio dalla pipeline vera.
 *
 * <p>Una volta per tutta la JVM dei test:
 * <ol>
 *   <li>parte PostgreSQL (stessa immagine del Compose);</li>
 *   <li>Flyway applica le migrazioni di {@code database/migrations} (le stesse impacchettate nel jar);</li>
 *   <li>l'immagine della pipeline viene costruita da {@code ../data-pipeline} ed eseguita con
 *       {@code run --source sample} sulla stessa rete Docker del database: i dati dei test sono
 *       quelli che la pipeline carica davvero, non una copia scritta a mano.</li>
 * </ol>
 *
 * <p>Il database viene passato all'applicazione con gli stessi nomi delle variabili d'ambiente usate
 * in produzione, così i test coprono anche la configurazione. All'avvio dell'applicazione Flyway
 * trova lo schema già migrato e si limita a convalidarlo.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public abstract class PostgresIntegrationTest {

    /** Cartella della pipeline; sovrascrivibile con {@code -Dpipeline.dir=...} per layout diversi. */
    protected static final Path PIPELINE_DIR =
            Path.of(System.getProperty("pipeline.dir", "../data-pipeline")).toAbsolutePath().normalize();

    /** CSV del dataset di esempio: gli stessi che la pipeline carica. */
    protected static final Path SAMPLE_DIR = PIPELINE_DIR.resolve("sample");

    private static final String DB_ALIAS = "db";
    private static final Network RETE = Network.newNetwork();

    protected static final PostgreSQLContainer<?> POSTGRES = new PostgreSQLContainer<>("postgres:17-alpine")
            .withNetwork(RETE)
            .withNetworkAliases(DB_ALIAS);

    static {
        POSTGRES.start();
        applicaMigrazioni();
        caricaDatasetDiEsempio();
    }

    private static void applicaMigrazioni() {
        Flyway.configure()
                .dataSource(POSTGRES.getJdbcUrl(), POSTGRES.getUsername(), POSTGRES.getPassword())
                .locations("classpath:db/migration")
                .load()
                .migrate();
    }

    /** Costruisce l'immagine della pipeline e la esegue fino al termine: un'uscita diversa da 0 fa fallire i test. */
    private static void caricaDatasetDiEsempio() {
        if (!Files.isDirectory(SAMPLE_DIR)) {
            throw new IllegalStateException("Dataset di esempio non trovato in " + SAMPLE_DIR);
        }
        // Il contesto di build contiene solo ciò che il Dockerfile copia: mai raw/ né processed/.
        ImageFromDockerfile immagine = new ImageFromDockerfile("f1-pipeline-test-backend", false)
                .withFileFromPath("Dockerfile", PIPELINE_DIR.resolve("Dockerfile"))
                .withFileFromPath("pyproject.toml", PIPELINE_DIR.resolve("pyproject.toml"))
                .withFileFromPath("src", PIPELINE_DIR.resolve("src"))
                .withFileFromPath("sample", SAMPLE_DIR);

        try (GenericContainer<?> pipeline = new GenericContainer<>(immagine)) {
            pipeline.withNetwork(RETE)
                    .withEnv("POSTGRES_HOST", DB_ALIAS)
                    .withEnv("POSTGRES_PORT", String.valueOf(PostgreSQLContainer.POSTGRESQL_PORT))
                    .withEnv("POSTGRES_DB", POSTGRES.getDatabaseName())
                    .withEnv("POSTGRES_USER", POSTGRES.getUsername())
                    .withEnv("POSTGRES_PASSWORD", POSTGRES.getPassword())
                    .withEnv("F1_PROCESSED_DIR", "/tmp/processed")
                    .withCommand("run", "--source", "sample")
                    .withStartupCheckStrategy(new OneShotStartupCheckStrategy().withTimeout(Duration.ofMinutes(5)))
                    .start();
        }
    }

    @DynamicPropertySource
    static void databaseDaVariabili(DynamicPropertyRegistry registry) {
        registry.add("POSTGRES_HOST", POSTGRES::getHost);
        registry.add("POSTGRES_PORT", () -> POSTGRES.getMappedPort(PostgreSQLContainer.POSTGRESQL_PORT));
        registry.add("POSTGRES_DB", POSTGRES::getDatabaseName);
        registry.add("POSTGRES_USER", POSTGRES::getUsername);
        registry.add("POSTGRES_PASSWORD", POSTGRES::getPassword);
    }

    @Autowired
    protected TestRestTemplate rest;

    /** GET che deve rispondere 200 con un corpo JSON. */
    protected JsonNode getJson(String percorso) {
        ResponseEntity<JsonNode> risposta = rest.getForEntity(percorso, JsonNode.class);
        assertThat(risposta.getStatusCode()).as("GET %s", percorso).isEqualTo(HttpStatus.OK);
        assertThat(risposta.getBody()).as("corpo di GET %s", percorso).isNotNull();
        return risposta.getBody();
    }

    /** GET senza attese sullo stato: per i test sugli errori. */
    protected ResponseEntity<JsonNode> get(String percorso) {
        return rest.getForEntity(percorso, JsonNode.class);
    }
}
