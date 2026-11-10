package com.f1dataplatform.backend;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/**
 * Coerenza tra l'API e i CSV del dataset di esempio, letti qui direttamente: stesse gare, stesso
 * numero di risultati e di giri (il campione non ha righe scartate).
 */
class CsvCoherenceTest extends PostgresIntegrationTest {

    private static List<Map<String, String>> gareCsv;
    private static Map<String, Long> risultatiPerGara;
    private static Map<String, Long> sprintPerGara;
    private static Map<String, Long> giriPerGara;
    private static Map<String, Long> giriPerGaraEPilota;

    @BeforeAll
    static void leggiCsv() {
        gareCsv = SampleCsv.read(SAMPLE_DIR.resolve("races.csv"));
        risultatiPerGara = conta(SampleCsv.read(SAMPLE_DIR.resolve("results.csv")), "raceId");
        sprintPerGara = conta(SampleCsv.read(SAMPLE_DIR.resolve("sprint_results.csv")), "raceId");
        List<Map<String, String>> giri = SampleCsv.read(SAMPLE_DIR.resolve("lap_times.csv"));
        giriPerGara = conta(giri, "raceId");
        giriPerGaraEPilota = giri.stream()
                .collect(Collectors.groupingBy(r -> r.get("raceId") + "/" + r.get("driverId"), Collectors.counting()));
    }

    private static Map<String, Long> conta(List<Map<String, String>> righe, String colonna) {
        return righe.stream().collect(Collectors.groupingBy(r -> r.get(colonna), Collectors.counting()));
    }

    @Test
    void ilCampioneLettoDaiTestEQuelloAtteso() {
        assertThat(gareCsv).hasSize(68);
        assertThat(risultatiPerGara.values().stream().mapToLong(Long::longValue).sum()).isEqualTo(1359);
        assertThat(sprintPerGara).hasSize(15);
        assertThat(giriPerGara.values().stream().mapToLong(Long::longValue).sum()).isEqualTo(74_489);
    }

    @Test
    void leGareDellApiSonoQuelleDiRacesCsv() {
        Map<String, JsonNode> gareApi = new HashMap<>();
        for (int anno : new int[] {2022, 2023, 2024}) {
            getJson("/api/seasons/" + anno + "/races").forEach(g -> gareApi.put(g.get("id").asText(), g));
        }

        assertThat(gareApi).hasSize(gareCsv.size());
        for (Map<String, String> csv : gareCsv) {
            JsonNode api = gareApi.get(csv.get("raceId"));
            assertThat(api).as("gara %s", csv.get("raceId")).isNotNull();
            assertThat(api.get("season").asText()).isEqualTo(csv.get("year"));
            assertThat(api.get("round").asText()).isEqualTo(csv.get("round"));
            assertThat(api.get("name").asText()).isEqualTo(csv.get("name"));
            assertThat(api.get("date").asText()).isEqualTo(csv.get("date"));
            assertThat(api.get("circuit").get("id").asText()).isEqualTo(csv.get("circuitId"));
            assertThat(api.get("hasSprint").asBoolean()).isEqualTo(sprintPerGara.containsKey(csv.get("raceId")));
        }
    }

    @Test
    void ogniGaraHaTantiRisultatiQuanteRigheDiResultsCsv() {
        for (Map<String, String> gara : gareCsv) {
            String id = gara.get("raceId");
            assertThat(getJson("/api/races/" + id + "/results"))
                    .as("risultati della gara %s (%s %s)", id, gara.get("year"), gara.get("name"))
                    .hasSize(risultatiPerGara.get(id).intValue());
        }
    }

    @Test
    void ogniSprintHaTantiRisultatiQuanteRigheDiSprintResultsCsv() {
        sprintPerGara.forEach((id, righe) ->
                assertThat(getJson("/api/races/" + id + "/results?session=sprint"))
                        .as("risultati della sprint %s", id).hasSize(righe.intValue()));
    }

    /** Prima e ultima gara del campione, la gara di riferimento e tre weekend con sprint. */
    @ParameterizedTest
    @ValueSource(strings = {"1074", "1077", "1098", "1101", "1115", "1144"})
    void iGiriDiOgniPilotaCoincidonoConLapTimesCsv(String raceId) {
        long totale = 0;
        for (JsonNode risultato : getJson("/api/races/" + raceId + "/results")) {
            String driverId = risultato.get("driver").get("id").asText();
            int giri = getJson("/api/races/" + raceId + "/laps/" + driverId).size();
            assertThat((long) giri).as("giri del pilota %s nella gara %s", driverId, raceId)
                    .isEqualTo(giriPerGaraEPilota.getOrDefault(raceId + "/" + driverId, 0L));
            totale += giri;
        }
        assertThat(totale).as("giri della gara %s", raceId).isEqualTo(giriPerGara.get(raceId));
    }
}
