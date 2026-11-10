package com.f1dataplatform.backend;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

/**
 * Statistiche di piloti e scuderie.
 *
 * <p>I valori attesi sono calcolati a mano dai CSV del dataset di esempio ({@code results.csv} per le
 * gare, {@code sprint_results.csv} per i punti delle sprint) e fissati qui: non derivano dall'API.
 * Riscontro con i totali ufficiali di campionato (gare + sprint): Verstappen 2023 = 530 + 45 = 575,
 * Hamilton 2022 = 233 + 7 = 240, Red Bull 2023 = 790 + 70 = 860, Ferrari 2022 = 519 + 35 = 554,
 * McLaren 2024 = 609 + 57 = 666.
 */
class StatisticsApiTest extends PostgresIntegrationTest {

    @ParameterizedTest(name = "pilota {0} {2}")
    @CsvSource(nullValues = "-", value = {
            // sigla, id, stagione, races, starts, wins, podiums, points, sprintPoints
            "VER, 830, 2023, 22, 22, 19, 21,  530,  45",
            "VER, 830,    -, 68, 68, 43, 52, 1362, 104",
            "HAM,   1, 2022, 22, 22,  0,  9,  233,   7",
            "LEC, 844, 2024, 24, 24,  3, 13,  327,  29",
            "LEC, 844, 2022, 22, 22,  3, 11,  291,  17",
            "NOR, 846, 2024, 24, 24,  4, 13,  344,  30",
            // Schumacher 2022: iscritto a 22 gare, non partito in Arabia Saudita (esito withdrawn).
            "MSC, 854, 2022, 22, 21,  0,  0,   12,   0",
            // De Vries: 1 gara nel 2022 e 10 nel 2023.
            "DEV, 856,    -, 11, 11,  0,  0,    2,   0",
            "BEA, 860, 2024,  3,  3,  0,  0,    7,   0",
    })
    void statistichePilotaCalcolateAManoDaiCsv(String sigla, int id, Integer stagione, int races, int starts,
            int wins, int podiums, double points, double sprintPoints) {
        JsonNode stat = getJson("/api/drivers/" + id + "/statistics" + (stagione == null ? "" : "?season=" + stagione));

        assertThat(stat.get("driver").get("id").asInt()).isEqualTo(id);
        assertThat(stat.get("driver").get("code").asText()).isEqualTo(sigla);
        assertThat(stat.get("season").isNull()).isEqualTo(stagione == null);
        assertThat(stat.get("races").asInt()).as("races").isEqualTo(races);
        assertThat(stat.get("starts").asInt()).as("starts").isEqualTo(starts);
        assertThat(stat.get("wins").asInt()).as("wins").isEqualTo(wins);
        assertThat(stat.get("podiums").asInt()).as("podiums").isEqualTo(podiums);
        assertThat(stat.get("points").asDouble()).as("points").isEqualTo(points);
        assertThat(stat.get("sprintPoints").asDouble()).as("sprintPoints").isEqualTo(sprintPoints);
    }

    @ParameterizedTest(name = "scuderia {0} {2}")
    @CsvSource(nullValues = "-", value = {
            // nome, id, stagione, races, starts, wins, podiums (piazzamenti), points, sprintPoints
            "Red Bull,   9, 2023, 22, 22, 21, 30,  790,  70",
            "Red Bull,   9,    -, 68, 68, 47, 76, 2051, 157",
            "Ferrari,    6, 2022, 22, 22,  4, 20,  519,  35",
            "McLaren,    1, 2024, 24, 24,  6, 21,  609,  57",
            "Mercedes, 131, 2022, 22, 22,  1, 17,  495,  20",
            "Haas F1 Team, 210, -, 68, 68,  0,  0,   93,  14",
    })
    void statisticheScuderiaCalcolateAManoDaiCsv(String nome, int id, Integer stagione, int races, int starts,
            int wins, int podiums, double points, double sprintPoints) {
        JsonNode stat = getJson("/api/teams/" + id + "/statistics" + (stagione == null ? "" : "?season=" + stagione));

        assertThat(stat.get("team").get("id").asInt()).isEqualTo(id);
        assertThat(stat.get("team").get("name").asText()).isEqualTo(nome);
        assertThat(stat.get("season").isNull()).isEqualTo(stagione == null);
        assertThat(stat.get("races").asInt()).as("races").isEqualTo(races);
        assertThat(stat.get("starts").asInt()).as("starts").isEqualTo(starts);
        assertThat(stat.get("wins").asInt()).as("wins").isEqualTo(wins);
        assertThat(stat.get("podiums").asInt()).as("podiums").isEqualTo(podiums);
        assertThat(stat.get("points").asDouble()).as("points").isEqualTo(points);
        assertThat(stat.get("sprintPoints").asDouble()).as("sprintPoints").isEqualTo(sprintPoints);
    }

    @Test
    void statistichePilotaHannoLoSchemaAttesoEICampiAggiuntivi() {
        JsonNode stat = getJson("/api/drivers/830/statistics?season=2023");

        for (String campo : new String[] {"races", "wins", "podiums", "points", "starts", "sprintPoints", "poles",
                "fastestLaps", "retirements", "bestFinish", "averageFinish", "averageGrid"}) {
            assertThat(stat.get(campo)).as(campo).isNotNull();
            assertThat(stat.get(campo).isNumber()).as(campo + " numerico").isTrue();
        }
        assertThat(stat.get("season").asInt()).isEqualTo(2023);
        assertThat(stat.get("driver").get("name").asText()).isEqualTo("Max Verstappen");
        // Verstappen 2023, da results.csv: 12 partenze dalla prima casella, 9 giri veloci, nessun ritiro,
        // media arrivi 28/22 = 1,27, media griglia 70/22 = 3,18.
        assertThat(stat.get("poles").asInt()).isEqualTo(12);
        assertThat(stat.get("fastestLaps").asInt()).isEqualTo(9);
        assertThat(stat.get("retirements").asInt()).isZero();
        assertThat(stat.get("bestFinish").asInt()).isEqualTo(1);
        assertThat(stat.get("averageFinish").asDouble()).isEqualTo(1.27);
        assertThat(stat.get("averageGrid").asDouble()).isEqualTo(3.18);
    }

    @Test
    void statisticheScuderiaHannoLoSchemaAttesoEICampiAggiuntivi() {
        JsonNode stat = getJson("/api/teams/9/statistics?season=2023");

        for (String campo : new String[] {"races", "wins", "podiums", "points", "starts", "sprintPoints", "poles",
                "fastestLaps", "retirements", "bestFinish", "averageFinish", "averageGrid"}) {
            assertThat(stat.get(campo)).as(campo).isNotNull();
            assertThat(stat.get(campo).isNumber()).as(campo + " numerico").isTrue();
        }
        // Red Bull 2023, da results.csv: 14 gare dalla prima casella, 11 giri veloci, 2 ritiri,
        // media arrivi 118/42 = 2,81, media griglia 234/42 = 5,57.
        assertThat(stat.get("poles").asInt()).isEqualTo(14);
        assertThat(stat.get("fastestLaps").asInt()).isEqualTo(11);
        assertThat(stat.get("retirements").asInt()).isEqualTo(2);
        assertThat(stat.get("bestFinish").asInt()).isEqualTo(1);
        assertThat(stat.get("averageFinish").asDouble()).isEqualTo(2.81);
        assertThat(stat.get("averageGrid").asDouble()).isEqualTo(5.57);
    }

    @Test
    void lePodiumsDiUnaScuderiaContanoIPiazzamentiEPossonoSuperareLeGare() {
        JsonNode stat = getJson("/api/teams/9/statistics?season=2023");

        // Red Bull 2023: a podio in 21 gare su 22, con 9 doppi podi: 30 piazzamenti.
        assertThat(stat.get("podiums").asInt()).isEqualTo(30).isGreaterThan(stat.get("races").asInt());
        assertThat(stat.get("wins").asInt()).isEqualTo(21).isLessThanOrEqualTo(stat.get("races").asInt());
    }

    @Test
    void leSprintNonEntranoNeiConteggi() {
        // Piastri 2023 in results.csv: 22 gare, nessuna vittoria, 2 podi (Giappone e Qatar), 82 punti.
        // In sprint_results.csv: 6 sprint, una vinta (Qatar) e un secondo posto (Belgio), 15 punti.
        // Se le sprint entrassero nei conteggi si avrebbero 28 gare, 1 vittoria, 4 podi, 97 punti.
        JsonNode stat = getJson("/api/drivers/857/statistics?season=2023");

        assertThat(stat.get("driver").get("code").asText()).isEqualTo("PIA");
        assertThat(stat.get("races").asInt()).isEqualTo(22);
        assertThat(stat.get("starts").asInt()).isEqualTo(22);
        assertThat(stat.get("wins").asInt()).isZero();
        assertThat(stat.get("podiums").asInt()).isEqualTo(2);
        assertThat(stat.get("points").asDouble()).isEqualTo(82.0);
        assertThat(stat.get("sprintPoints").asDouble()).isEqualTo(15.0);
    }

    @Test
    void stagioneSenzaGarePerIlPilotaRestituisceZeri() {
        // Bearman ha corso solo nel 2024.
        JsonNode stat = getJson("/api/drivers/860/statistics?season=2022");

        assertThat(stat.get("races").asInt()).isZero();
        assertThat(stat.get("wins").asInt()).isZero();
        assertThat(stat.get("podiums").asInt()).isZero();
        assertThat(stat.get("points").asDouble()).isZero();
        assertThat(stat.get("sprintPoints").asDouble()).isZero();
        assertThat(stat.get("bestFinish").isNull()).isTrue();
        assertThat(stat.get("averageFinish").isNull()).isTrue();
        assertThat(stat.get("averageGrid").isNull()).isTrue();
    }
}
