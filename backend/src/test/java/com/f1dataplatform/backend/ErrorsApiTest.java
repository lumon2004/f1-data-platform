package com.f1dataplatform.backend;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;

/** Errori: 404 e 400 con lo stesso corpo JSON, senza dettagli interni. */
class ErrorsApiTest extends PostgresIntegrationTest {

    private static final String INESISTENTE = "999999999";

    @ParameterizedTest
    @ValueSource(strings = {
            "/api/seasons/1800/races",
            "/api/seasons/2021/races",
            "/api/races/" + INESISTENTE,
            "/api/races/" + INESISTENTE + "/results",
            "/api/races/" + INESISTENTE + "/laps/830",
            "/api/races/1098/laps/" + INESISTENTE,
            "/api/races/0",
            "/api/races/-1/results",
            "/api/drivers/" + INESISTENTE + "/statistics",
            "/api/drivers/" + INESISTENTE + "/statistics?season=2023",
            "/api/teams/" + INESISTENTE + "/statistics",
            // Il Bahrain 2023 non ha una sprint.
            "/api/races/1098/results?session=sprint",
            // Percorsi sconosciuti sotto /api.
            "/api/inesistente",
            "/api/drivers",
            "/api/races/1098/laps",
    })
    void risorsaInesistente404(String percorso) {
        assertErrore(get(percorso), 404, "Not Found", percorso);
    }

    @ParameterizedTest
    @ValueSource(strings = {
            "/api/seasons/abc/races",
            "/api/races/abc",
            "/api/races/abc/results",
            "/api/races/1.5",
            "/api/races/abc/laps/830",
            "/api/races/1098/laps/abc",
            // Oltre il massimo di un intero a 32 bit.
            "/api/races/99999999999",
            "/api/drivers/abc/statistics",
            "/api/drivers/830/statistics?season=abc",
            "/api/drivers/830/statistics?season=20x3",
            "/api/teams/abc/statistics",
            "/api/teams/9/statistics?season=abc",
            "/api/races/1098/results?session=qualifying",
            "/api/races/1098/results?session=abc",
    })
    void parametroNonValido400(String percorso) {
        assertErrore(get(percorso), 400, "Bad Request", percorso);
    }

    @Test
    void ilMessaggioDiceQualeRisorsaOParametro() {
        assertThat(get("/api/races/" + INESISTENTE).getBody().get("message").asText())
                .isEqualTo("Gara " + INESISTENTE + " inesistente");
        assertThat(get("/api/races/1098/laps/" + INESISTENTE).getBody().get("message").asText())
                .isEqualTo("Pilota " + INESISTENTE + " inesistente");
        assertThat(get("/api/teams/" + INESISTENTE + "/statistics").getBody().get("message").asText())
                .isEqualTo("Scuderia " + INESISTENTE + " inesistente");
        assertThat(get("/api/drivers/830/statistics?season=abc").getBody().get("message").asText())
                .contains("season").contains("abc");
        assertThat(get("/api/races/abc").getBody().get("message").asText())
                .contains("raceId").doesNotContain("Exception").doesNotContain("java.");
    }

    @Test
    void metodoNonConsentito405ConLoStessoCorpo() {
        ResponseEntity<JsonNode> risposta =
                rest.exchange("/api/seasons", HttpMethod.POST, HttpEntity.EMPTY, JsonNode.class);

        assertErrore(risposta, 405, "Method Not Allowed", "/api/seasons");
    }

    private static void assertErrore(ResponseEntity<JsonNode> risposta, int stato, String nome, String percorso) {
        assertThat(risposta.getStatusCode().value()).as("GET %s", percorso).isEqualTo(stato);
        assertThat(risposta.getHeaders().getContentType()).isNotNull();
        assertThat(risposta.getHeaders().getContentType().isCompatibleWith(MediaType.APPLICATION_JSON)).isTrue();
        JsonNode corpo = risposta.getBody();
        assertThat(corpo).isNotNull();
        assertThat(corpo.fieldNames()).toIterable()
                .containsExactlyInAnyOrder("status", "error", "message", "path", "timestamp");
        assertThat(corpo.get("status").asInt()).isEqualTo(stato);
        assertThat(corpo.get("error").asText()).isEqualTo(nome);
        assertThat(corpo.get("message").asText()).isNotBlank();
        assertThat(corpo.get("path").asText()).isEqualTo(percorso.replaceAll("\\?.*", ""));
    }
}
