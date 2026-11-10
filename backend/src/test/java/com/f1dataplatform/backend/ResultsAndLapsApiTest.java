package com.f1dataplatform.backend;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/** Classifiche e giri: schema, valori noti da results.csv e lap_times.csv, gare con sprint. */
class ResultsAndLapsApiTest extends PostgresIntegrationTest {

    @Test
    void resultsHaLoSchemaDelContratto() {
        JsonNode risultati = getJson("/api/races/1098/results");

        assertThat(risultati).hasSize(20);
        for (JsonNode r : risultati) {
            assertThat(r.fieldNames()).toIterable().contains("position", "points", "status", "laps", "driver",
                    "team", "positionOrder", "outcome", "grid", "timeMs", "gapMs", "fastestLap", "carNumber");
            assertThat(r.get("position").isNull() || r.get("position").isInt()).isTrue();
            assertThat(r.get("points").isNumber()).isTrue();
            assertThat(r.get("laps").isInt()).isTrue();
            assertThat(r.get("status").isTextual()).isTrue();
            assertThat(r.get("driver").fieldNames()).toIterable().contains("id", "code", "name");
            assertThat(r.get("team").fieldNames()).toIterable().contains("id", "name");
        }
    }

    @Test
    void resultsDelBahrain2023CoincidonoConIlCsv() {
        JsonNode risultati = getJson("/api/races/1098/results");

        JsonNode primo = risultati.get(0);
        assertThat(primo.get("position").asInt()).isEqualTo(1);
        assertThat(primo.get("points").asDouble()).isEqualTo(25.0);
        assertThat(primo.get("status").asText()).isEqualTo("Finished");
        assertThat(primo.get("outcome").asText()).isEqualTo("classified");
        assertThat(primo.get("laps").asInt()).isEqualTo(57);
        assertThat(primo.get("grid").asInt()).isEqualTo(1);
        assertThat(primo.get("carNumber").asInt()).isEqualTo(1);
        assertThat(primo.get("timeMs").asInt()).isEqualTo(5_636_736);
        assertThat(primo.get("gapMs").asInt()).isZero();
        assertThat(primo.get("fastestLap").get("lap").asInt()).isEqualTo(44);
        assertThat(primo.get("fastestLap").get("rank").asInt()).isEqualTo(6);
        assertThat(primo.get("fastestLap").get("timeMs").asInt()).isEqualTo(96_236);
        assertThat(primo.get("fastestLap").get("speedKph").asDouble()).isEqualTo(202.452);
        assertThat(primo.get("driver").get("id").asInt()).isEqualTo(830);
        assertThat(primo.get("driver").get("code").asText()).isEqualTo("VER");
        assertThat(primo.get("driver").get("name").asText()).isEqualTo("Max Verstappen");
        assertThat(primo.get("driver").get("nationality").asText()).isEqualTo("Dutch");
        assertThat(primo.get("team").get("id").asInt()).isEqualTo(9);
        assertThat(primo.get("team").get("name").asText()).isEqualTo("Red Bull");

        JsonNode secondo = risultati.get(1);
        assertThat(secondo.get("driver").get("code").asText()).isEqualTo("PER");
        assertThat(secondo.get("gapMs").asInt()).isEqualTo(11_987);

        // Ultimo in ordine di arrivo: Piastri, ritirato al giro 13 per un guasto elettrico.
        JsonNode ultimo = risultati.get(19);
        assertThat(ultimo.get("driver").get("code").asText()).isEqualTo("PIA");
        assertThat(ultimo.get("position").isNull()).isTrue();
        assertThat(ultimo.get("outcome").asText()).isEqualTo("retired");
        assertThat(ultimo.get("status").asText()).isEqualTo("Electrical");
        assertThat(ultimo.get("laps").asInt()).isEqualTo(13);
        assertThat(ultimo.get("timeMs").isNull()).isTrue();
        assertThat(ultimo.get("gapMs").isNull()).isTrue();
        assertThat(ultimo.get("points").asDouble()).isZero();
    }

    @Test
    void resultsSonoInOrdineDiArrivoConINonClassificatiInFondo() {
        JsonNode risultati = getJson("/api/races/1098/results");

        List<Integer> ordine = new ArrayList<>();
        List<Integer> posizioni = new ArrayList<>();
        risultati.forEach(r -> {
            ordine.add(r.get("positionOrder").asInt());
            if (!r.get("position").isNull()) {
                posizioni.add(r.get("position").asInt());
            }
        });
        assertThat(ordine).isSorted().doesNotHaveDuplicates();
        // 17 classificati e 3 ritirati (Ocon, Leclerc, Piastri) in results.csv.
        assertThat(posizioni).hasSize(17).isSorted().startsWith(1);
        for (int i = 17; i < 20; i++) {
            assertThat(risultati.get(i).get("position").isNull()).isTrue();
        }
    }

    @Test
    void resultsDiUnaGaraConSprintContengonoSoloLaGara() {
        // Qatar 2023: gara vinta da Verstappen (25 punti + giro veloce), sprint vinta da Piastri (8 punti).
        JsonNode gara = getJson("/api/races/1115/results");

        assertThat(gara).hasSize(20);
        assertThat(gara.get(0).get("driver").get("code").asText()).isEqualTo("VER");
        assertThat(gara.get(0).get("points").asDouble()).isEqualTo(26.0);
        assertThat(gara.get(0).get("laps").asInt()).isEqualTo(57);
        assertThat(gara.get(1).get("driver").get("code").asText()).isEqualTo("PIA");
        assertThat(gara.findValues("driver").stream().map(d -> d.get("id").asInt()))
                .as("un pilota compare una sola volta: nessuna riga della sprint").doesNotHaveDuplicates();

        assertThat(getJson("/api/races/1115/results?session=race")).isEqualTo(gara);
    }

    @Test
    void resultsDellaSprintSoloSuRichiesta() {
        JsonNode sprint = getJson("/api/races/1115/results?session=sprint");

        assertThat(sprint).hasSize(20);
        assertThat(sprint.get(0).get("driver").get("code").asText()).isEqualTo("PIA");
        assertThat(sprint.get(0).get("points").asDouble()).isEqualTo(8.0);
        assertThat(sprint.get(0).get("laps").asInt()).isEqualTo(19);
        assertThat(sprint.get(1).get("driver").get("code").asText()).isEqualTo("VER");
        assertThat(sprint.get(1).get("points").asDouble()).isEqualTo(7.0);
    }

    @Test
    void lapsDelVincitoreInOrdineDiGiro() {
        JsonNode giri = getJson("/api/races/1098/laps/830");

        assertThat(giri).hasSize(57);
        for (int i = 0; i < giri.size(); i++) {
            JsonNode g = giri.get(i);
            assertThat(g.fieldNames()).toIterable().containsExactly("lap", "position", "timeMs");
            assertThat(g.get("lap").asInt()).isEqualTo(i + 1);
            assertThat(g.get("timeMs").isInt()).isTrue();
            assertThat(g.get("timeMs").asInt()).isPositive();
        }
        // Primi due giri di Verstappen in lap_times.csv.
        assertThat(giri.get(0).get("position").asInt()).isEqualTo(1);
        assertThat(giri.get(0).get("timeMs").asInt()).isEqualTo(99_019);
        assertThat(giri.get(1).get("timeMs").asInt()).isEqualTo(97_974);
    }

    @Test
    void lapsVuotiPerUnPilotaSenzaGiriNellaGara() {
        // Sainz a Imola 2022: in classifica, ritirato al primo giro, nessun giro cronometrato.
        JsonNode ritirato = getJson("/api/races/1077/laps/832");
        assertThat(ritirato.isArray()).isTrue();
        assertThat(ritirato).isEmpty();

        // De Vries (esordio a Monza 2022) non ha corso il Bahrain 2022: pilota esistente, gara esistente.
        JsonNode assente = getJson("/api/races/1074/laps/856");
        assertThat(assente.isArray()).isTrue();
        assertThat(assente).isEmpty();
    }
}
