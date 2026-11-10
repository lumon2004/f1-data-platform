package com.f1dataplatform.backend;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;

/** Errori: 404 e 400 con lo stesso corpo JSON, senza dettagli interni. */
class ErrorsApiTest extends PostgresIntegrationTest {

    private static final String INESISTENTE = "999999999";
    private static final ObjectMapper JSON = new ObjectMapper();

    @LocalServerPort
    private int porta;

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
            "/api/races/1098/sessions",
            // Endpoint aggiuntivi: stagione senza gare e gara inesistente.
            "/api/seasons/1800/drivers",
            "/api/seasons/2021/teams",
            "/api/seasons/2021/standings/drivers",
            "/api/seasons/0/standings/teams",
            "/api/seasons/2023/standings",
            "/api/seasons/2023/standings/altro",
            "/api/races/" + INESISTENTE + "/laps",
            "/api/races/" + INESISTENTE + "/pit-stops",
            "/api/races/" + INESISTENTE + "/stints",
            "/api/races/" + INESISTENTE + "/qualifying",
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
            // Un anno non positivo non è una stagione.
            "/api/drivers/830/statistics?season=0",
            "/api/drivers/830/statistics?season=-2023",
            "/api/teams/9/statistics?season=0",
            "/api/teams/9/statistics?season=-1",
            // Endpoint aggiuntivi.
            "/api/seasons/abc/drivers",
            "/api/seasons/abc/teams",
            "/api/seasons/20x3/standings/drivers",
            "/api/seasons/abc/standings/teams",
            "/api/races/abc/laps",
            "/api/races/abc/pit-stops",
            "/api/races/1.5/stints",
            "/api/races/abc/qualifying",
    })
    void parametroNonValido400(String percorso) {
        assertErrore(get(percorso), 400, "Bad Request", percorso);
    }

    @Test
    void stagionePlausibileSenzaDatiNonEUnErrore() {
        assertThat(getJson("/api/drivers/830/statistics?season=1990").get("races").asInt()).isZero();
        assertThat(getJson("/api/teams/9/statistics?season=2050").get("races").asInt()).isZero();
    }

    /**
     * Richieste che Tomcat respinge prima di passarle a Spring: stesso corpo JSON. Si inviano su un
     * socket perché un client HTTP normalizzerebbe o rifiuterebbe questi indirizzi.
     */
    @ParameterizedTest
    @ValueSource(strings = {
            "/api/races/%00",
            "/api/races/a%2Fb",
            "/api/races/1098%2Fresults",
            "/api/races/[1098]",
            "/api/races/{1098}",
            "/api/races/1098|results",
            "/api/races/%zz",
    })
    void richiestaRespintaDaTomcat400ConLoStessoCorpo(String percorso) throws IOException {
        RispostaGrezza risposta = richiestaGrezza(percorso);

        assertThat(risposta.stato()).as("GET %s", percorso).isEqualTo(400);
        assertThat(risposta.contentType()).startsWith("application/json");
        JsonNode corpo = JSON.readTree(risposta.corpo());
        assertThat(corpo.fieldNames()).toIterable()
                .containsExactlyInAnyOrder("status", "error", "message", "path", "timestamp");
        assertThat(corpo.get("status").asInt()).isEqualTo(400);
        assertThat(corpo.get("error").asText()).isEqualTo("Bad Request");
        assertThat(corpo.get("message").asText()).isEqualTo("Richiesta non valida");
        assertThat(risposta.corpo()).doesNotContain("<html").doesNotContain("Tomcat");
    }

    @Test
    void indirizzoLunghissimo400ConLoStessoCorpo() throws IOException {
        RispostaGrezza risposta = richiestaGrezza("/api/races/" + "9".repeat(20_000));

        assertThat(risposta.stato()).isEqualTo(400);
        assertThat(risposta.contentType()).startsWith("application/json");
        JsonNode corpo = JSON.readTree(risposta.corpo());
        assertThat(corpo.fieldNames()).toIterable()
                .containsExactlyInAnyOrder("status", "error", "message", "path", "timestamp");
        assertThat(corpo.get("status").asInt()).isEqualTo(400);
        assertThat(corpo.get("message").asText()).isNotBlank();
        assertThat(risposta.corpo()).doesNotContain("<html");
    }

    private record RispostaGrezza(int stato, String contentType, String corpo) {
    }

    /** GET HTTP/1.1 scritto a mano, con il percorso inviato così com'è. */
    private RispostaGrezza richiestaGrezza(String percorso) throws IOException {
        try (Socket socket = new Socket("localhost", porta)) {
            socket.setSoTimeout(10_000);
            socket.getOutputStream().write(("GET " + percorso + " HTTP/1.1\r\nHost: localhost\r\n"
                    + "Accept: */*\r\nConnection: close\r\n\r\n").getBytes(StandardCharsets.ISO_8859_1));
            socket.getOutputStream().flush();
            String risposta = new String(socket.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
            int fineIntestazioni = risposta.indexOf("\r\n\r\n");
            String intestazioni = risposta.substring(0, fineIntestazioni);
            String corpo = risposta.substring(fineIntestazioni + 4);
            int stato = Integer.parseInt(intestazioni.split(" ")[1]);
            String contentType = intestazioni.lines()
                    .filter(r -> r.toLowerCase().startsWith("content-type:"))
                    .map(r -> r.substring(r.indexOf(':') + 1).trim())
                    .findFirst().orElse("");
            if (intestazioni.toLowerCase().contains("transfer-encoding: chunked")) {
                corpo = corpo.substring(corpo.indexOf('{'), corpo.lastIndexOf('}') + 1);
            }
            return new RispostaGrezza(stato, contentType, corpo);
        }
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
