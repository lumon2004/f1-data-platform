package com.f1dataplatform.backend;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.http.HttpStatus;

/** Tempi di risposta sul dataset di esempio: mediana sotto la soglia dei criteri di accettazione (500 ms). */
class ResponseTimeTest extends PostgresIntegrationTest {

    private static final long SOGLIA_MS = 500;
    private static final int RIPETIZIONI = 5;

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
    })
    void medianaSottoLaSoglia(String percorso) {
        get(percorso); // riscaldamento
        List<Long> tempi = new ArrayList<>();
        for (int i = 0; i < RIPETIZIONI; i++) {
            long inizio = System.nanoTime();
            assertThat(get(percorso).getStatusCode()).isEqualTo(HttpStatus.OK);
            tempi.add((System.nanoTime() - inizio) / 1_000_000);
        }
        Collections.sort(tempi);
        assertThat(tempi.get(RIPETIZIONI / 2)).as("mediana di %s in ms (misure: %s)", percorso, tempi)
                .isLessThan(SOGLIA_MS);
    }
}
