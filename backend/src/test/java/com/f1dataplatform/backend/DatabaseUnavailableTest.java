package com.f1dataplatform.backend;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.ResponseEntity;

/**
 * Database irraggiungibile: le richieste falliscono in pochi secondi con 503 e il corpo d'errore
 * comune, invece di restare appese per il timeout predefinito del pool (30 s).
 *
 * <p>L'applicazione parte senza database (porta chiusa, Flyway disattivato, pool che non pretende
 * una connessione all'avvio): è lo stato in cui si trova quando il database cade dopo l'avvio.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
        "POSTGRES_HOST=127.0.0.1",
        "POSTGRES_PORT=1",
        "POSTGRES_DB=assente",
        "POSTGRES_USER=nessuno",
        "POSTGRES_PASSWORD=x",
        "spring.flyway.enabled=false",
        "spring.datasource.hikari.initialization-fail-timeout=-1",
})
class DatabaseUnavailableTest {

    /** Timeout di connessione configurato (3 s) più margine. */
    private static final Duration LIMITE = Duration.ofSeconds(8);

    @Autowired
    private TestRestTemplate rest;

    @Test
    void leRichiesteFallisconoInFrettaCon503() {
        for (String percorso : new String[] {"/api/seasons", "/api/races/1098/results",
                "/api/drivers/830/statistics?season=2023"}) {
            long inizio = System.nanoTime();
            ResponseEntity<JsonNode> risposta = rest.getForEntity(percorso, JsonNode.class);
            Duration durata = Duration.ofNanos(System.nanoTime() - inizio);

            assertThat(risposta.getStatusCode().value()).as("GET %s", percorso).isEqualTo(503);
            assertThat(durata).as("durata di GET %s", percorso).isLessThan(LIMITE);
            JsonNode corpo = risposta.getBody();
            assertThat(corpo).isNotNull();
            assertThat(corpo.fieldNames()).toIterable()
                    .containsExactlyInAnyOrder("status", "error", "message", "path", "timestamp");
            assertThat(corpo.get("status").asInt()).isEqualTo(503);
            assertThat(corpo.get("error").asText()).isEqualTo("Service Unavailable");
            assertThat(corpo.get("message").asText()).isEqualTo("Database non disponibile, riprova tra poco")
                    .doesNotContain("127.0.0.1").doesNotContain("Connection");
        }
    }

    @Test
    void healthRispondeDownInFretta() {
        long inizio = System.nanoTime();
        ResponseEntity<JsonNode> risposta = rest.getForEntity("/actuator/health", JsonNode.class);
        Duration durata = Duration.ofNanos(System.nanoTime() - inizio);

        assertThat(risposta.getStatusCode().value()).isEqualTo(503);
        assertThat(risposta.getBody().get("status").asText()).isEqualTo("DOWN");
        assertThat(durata).isLessThan(LIMITE);
    }

    @Test
    void laDocumentazioneNonDipendeDalDatabase() {
        assertThat(rest.getForEntity("/v3/api-docs", JsonNode.class).getStatusCode().value()).isEqualTo(200);
    }
}
