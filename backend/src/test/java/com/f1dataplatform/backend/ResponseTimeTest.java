package com.f1dataplatform.backend;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.http.HttpStatus;

/**
 * Tempi di risposta sul dataset di esempio: la mediana deve stare sotto la soglia dei criteri di
 * accettazione, letta da {@code config/accettazione.json} ({@code api.max_response_ms}) come fanno
 * i test di accettazione, con lo stesso numero di misure ({@code api.ripetizioni_misura}).
 */
class ResponseTimeTest extends PostgresIntegrationTest {

    /** Radice del repository rispetto a backend/; sovrascrivibile con {@code -Dacceptance.config=...}. */
    private static final Path CONFIG = Path.of(
            System.getProperty("acceptance.config", "../config/accettazione.json")).toAbsolutePath().normalize();

    private static long sogliaMs;
    private static int ripetizioni;

    @BeforeAll
    static void leggiSoglia() throws IOException {
        JsonNode api = new ObjectMapper().readTree(CONFIG.toFile()).get("api");
        sogliaMs = api.get("max_response_ms").asLong();
        ripetizioni = api.get("ripetizioni_misura").asInt();
        assertThat(sogliaMs).as("api.max_response_ms in %s", CONFIG).isPositive();
        assertThat(ripetizioni).as("api.ripetizioni_misura in %s", CONFIG).isPositive();
    }

    @ParameterizedTest
    @ValueSource(strings = {
            "/api/seasons",
            "/api/seasons/2023/races",
            "/api/races/1098",
            "/api/races/1098/results",
            "/api/races/1098/laps/830",
            "/api/drivers/830/statistics",
            "/api/drivers/830/statistics?season=2023",
            "/api/teams/9/statistics",
            "/api/teams/9/statistics?season=2023",
            // Endpoint aggiuntivi: i più pesanti sono i giri dell'intera gara e le classifiche.
            "/api/seasons/2023/drivers",
            "/api/seasons/2023/teams",
            "/api/seasons/2023/standings/drivers",
            "/api/seasons/2023/standings/teams",
            "/api/races/1098/laps",
            "/api/races/1098/pit-stops",
            "/api/races/1098/stints",
            "/api/races/1098/qualifying",
    })
    void medianaSottoLaSoglia(String percorso) {
        get(percorso); // riscaldamento
        List<Long> tempi = new ArrayList<>();
        for (int i = 0; i < ripetizioni; i++) {
            long inizio = System.nanoTime();
            assertThat(get(percorso).getStatusCode()).isEqualTo(HttpStatus.OK);
            tempi.add((System.nanoTime() - inizio) / 1_000_000);
        }
        Collections.sort(tempi);
        assertThat(tempi.get(ripetizioni / 2)).as("mediana di %s in ms (misure: %s)", percorso, tempi)
                .isLessThan(sogliaMs);
    }
}
