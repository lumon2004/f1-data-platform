package com.f1dataplatform.backend;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * Giri dell'intera gara, soste, stint e qualifica. Valori attesi calcolati a mano da lap_times.csv,
 * pit_stops.csv e qualifying.csv; gli stint attesi seguono la regola di docs/modello-dati.md.
 */
class RaceAnalysisApiTest extends PostgresIntegrationTest {

    @Test
    void raceLapsRaggruppaIGiriPerPilotaInOrdineDArrivo() {
        JsonNode piloti = getJson("/api/races/1098/laps");

        assertThat(piloti).hasSize(20);
        int totale = 0;
        for (JsonNode p : piloti) {
            assertThat(p.fieldNames()).toIterable().containsExactly("driver", "team", "laps");
            assertThat(p.get("driver").fieldNames()).toIterable().contains("id", "code", "name");
            assertThat(p.get("team").fieldNames()).toIterable().contains("id", "name");
            List<Integer> giri = new ArrayList<>();
            for (JsonNode g : p.get("laps")) {
                assertThat(g.fieldNames()).toIterable().containsExactly("lap", "position", "timeMs");
                assertThat(g.get("timeMs").asInt()).isPositive();
                giri.add(g.get("lap").asInt());
            }
            assertThat(giri).isSorted().doesNotHaveDuplicates();
            totale += giri.size();
        }
        // 1055 righe per la gara 1098 in lap_times.csv.
        assertThat(totale).isEqualTo(1055);

        // Stesso ordine della classifica.
        List<String> ordineArrivo = new ArrayList<>();
        getJson("/api/races/1098/results").forEach(r -> ordineArrivo.add(r.get("driver").get("code").asText()));
        List<String> ordineGiri = new ArrayList<>();
        piloti.forEach(p -> ordineGiri.add(p.get("driver").get("code").asText()));
        assertThat(ordineGiri).isEqualTo(ordineArrivo).startsWith("VER", "PER", "ALO").endsWith("PIA");

        JsonNode verstappen = piloti.get(0);
        assertThat(verstappen.get("team").get("name").asText()).isEqualTo("Red Bull");
        assertThat(verstappen.get("laps")).hasSize(57);
        assertThat(verstappen.get("laps").get(0).get("timeMs").asInt()).isEqualTo(99_019);
        assertThat(piloti.get(19).get("laps")).hasSize(13);
    }

    @Test
    void raceLapsCoincideConIGiriDelSingoloPilota() {
        for (JsonNode p : getJson("/api/races/1115/laps")) {
            assertThat(p.get("laps"))
                    .isEqualTo(getJson("/api/races/1115/laps/" + p.get("driver").get("id").asInt()));
        }
    }

    @Test
    void raceLapsIncludeChiNonHaGiri() {
        // Imola 2022: Sainz è in classifica (ritirato al primo giro) ma non ha giri cronometrati.
        JsonNode piloti = getJson("/api/races/1077/laps");

        assertThat(piloti).hasSize(20);
        JsonNode sainz = null;
        for (JsonNode p : piloti) {
            if (p.get("driver").get("code").asText().equals("SAI")) {
                sainz = p;
            }
        }
        assertThat(sainz).isNotNull();
        assertThat(sainz.get("laps").isArray()).isTrue();
        assertThat(sainz.get("laps")).isEmpty();
    }

    @Test
    void pitStopsInOrdineDiGiro() {
        JsonNode soste = getJson("/api/races/1098/pit-stops");

        // 50 soste per la gara 1098 in pit_stops.csv.
        assertThat(soste).hasSize(50);
        List<Integer> giri = new ArrayList<>();
        for (JsonNode s : soste) {
            assertThat(s.fieldNames()).toIterable()
                    .containsExactly("driver", "stop", "lap", "durationMs", "timeOfDay");
            assertThat(s.get("driver").fieldNames()).toIterable().contains("id", "code", "name");
            assertThat(s.get("durationMs").asInt()).isPositive();
            giri.add(s.get("lap").asInt());
        }
        assertThat(giri).isSorted();

        // Prima sosta della gara: Gasly al giro 9, 25,885 s.
        JsonNode prima = soste.get(0);
        assertThat(prima.get("driver").get("code").asText()).isEqualTo("GAS");
        assertThat(prima.get("stop").asInt()).isEqualTo(1);
        assertThat(prima.get("lap").asInt()).isEqualTo(9);
        assertThat(prima.get("durationMs").asInt()).isEqualTo(25_885);
        assertThat(prima.get("timeOfDay").asText()).isEqualTo("18:18:56");
        // Al giro 10 Norris (18:20:31) si ferma prima di Tsunoda (18:20:34).
        assertThat(soste.get(1).get("driver").get("code").asText()).isEqualTo("NOR");
        assertThat(soste.get(2).get("driver").get("code").asText()).isEqualTo("TSU");

        // Le due soste di Verstappen: giri 14 e 36.
        List<String> verstappen = new ArrayList<>();
        for (JsonNode s : soste) {
            if (s.get("driver").get("id").asInt() == 830) {
                verstappen.add(s.get("stop").asInt() + "@" + s.get("lap").asInt() + ":" + s.get("durationMs").asInt());
            }
        }
        assertThat(verstappen).containsExactly("1@14:24289", "2@36:24910");
    }

    @Test
    void stintsDerivatiDalleSosteSenzaMescola() {
        JsonNode stint = getJson("/api/races/1098/stints");

        // Un pilota con n soste ha n + 1 stint, salvo ritiri ai box: 70 in tutto per la gara 1098.
        assertThat(stint).hasSize(70);
        for (JsonNode s : stint) {
            assertThat(s.fieldNames()).toIterable()
                    .containsExactly("driver", "stint", "startLap", "endLap", "laps", "compound");
            assertThat(s.get("compound").isNull()).as("la fonte non ha le mescole").isTrue();
            assertThat(s.get("laps").asInt())
                    .isEqualTo(s.get("endLap").asInt() - s.get("startLap").asInt() + 1).isPositive();
        }

        // Verstappen (vincitore, quindi primo): soste ai giri 14 e 36, 57 giri completati.
        assertThat(descrivi(stint, 830)).containsExactly("1:1-14", "2:15-36", "3:37-57");
        assertThat(stint.get(0).get("driver").get("code").asText()).isEqualTo("VER");
        // Piastri: ritirato al giro 13 senza stint ulteriori.
        assertThat(descrivi(stint, 857)).containsExactly("1:1-13");
        assertThat(stint.get(69).get("driver").get("code").asText()).isEqualTo("PIA");
    }

    @Test
    void stintsDiUnaGaraConTreSoste() {
        JsonNode stint = getJson("/api/races/1115/stints");

        // Qatar 2023 (soste obbligate): 54 soste, 72 stint; Verstappen ai giri 17, 34 e 51.
        assertThat(getJson("/api/races/1115/pit-stops")).hasSize(54);
        assertThat(stint).hasSize(72);
        assertThat(descrivi(stint, 830)).containsExactly("1:1-17", "2:18-34", "3:35-51", "4:52-57");
        assertThat(descrivi(stint, 857)).containsExactly("1:1-12", "2:13-25", "3:26-43", "4:44-57");
    }

    private static List<String> descrivi(JsonNode stint, int driverId) {
        List<String> descrizioni = new ArrayList<>();
        for (JsonNode s : stint) {
            if (s.get("driver").get("id").asInt() == driverId) {
                descrizioni.add(s.get("stint").asInt() + ":" + s.get("startLap").asInt() + "-"
                        + s.get("endLap").asInt());
            }
        }
        return descrizioni;
    }

    @Test
    void qualifyingInOrdineDiPosizioneConITempiInMillisecondi() {
        JsonNode qualifica = getJson("/api/races/1098/qualifying");

        assertThat(qualifica).hasSize(20);
        for (int i = 0; i < qualifica.size(); i++) {
            JsonNode q = qualifica.get(i);
            assertThat(q.fieldNames()).toIterable()
                    .containsExactly("position", "driver", "team", "carNumber", "q1Ms", "q2Ms", "q3Ms");
            assertThat(q.get("position").asInt()).isEqualTo(i + 1);
        }
        // Pole di Verstappen: 1:31.295, 1:30.503, 1:29.708.
        JsonNode pole = qualifica.get(0);
        assertThat(pole.get("driver").get("code").asText()).isEqualTo("VER");
        assertThat(pole.get("team").get("name").asText()).isEqualTo("Red Bull");
        assertThat(pole.get("q1Ms").asInt()).isEqualTo(91_295);
        assertThat(pole.get("q2Ms").asInt()).isEqualTo(90_503);
        assertThat(pole.get("q3Ms").asInt()).isEqualTo(89_708);
        assertThat(qualifica.get(1).get("driver").get("code").asText()).isEqualTo("PER");
        assertThat(qualifica.get(1).get("q3Ms").asInt()).isEqualTo(89_846);
        // Ultimo: Gasly, eliminato in Q1 con 1:32.181.
        JsonNode ultimo = qualifica.get(19);
        assertThat(ultimo.get("driver").get("code").asText()).isEqualTo("GAS");
        assertThat(ultimo.get("q1Ms").asInt()).isEqualTo(92_181);
        assertThat(ultimo.get("q2Ms").isNull()).isTrue();
        assertThat(ultimo.get("q3Ms").isNull()).isTrue();
    }
}
