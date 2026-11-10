package com.f1dataplatform.backend;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/** Stagioni, calendario e dettaglio di una gara sul dataset di esempio (2022-2024). */
class CalendarApiTest extends PostgresIntegrationTest {

    @Test
    void seasonsElencaLeStagioniDelCampioneConIlNumeroDiGare() {
        JsonNode stagioni = getJson("/api/seasons");

        assertThat(stagioni.isArray()).isTrue();
        assertThat(stagioni).hasSize(3);
        // Dalla più recente; gare e sprint contate a mano da races.csv.
        assertStagione(stagioni.get(0), 2024, 24, 6, "2024-03-02", "2024-12-08");
        assertStagione(stagioni.get(1), 2023, 22, 6, "2023-03-05", "2023-11-26");
        assertStagione(stagioni.get(2), 2022, 22, 3, "2022-03-20", "2022-11-20");
    }

    private static void assertStagione(JsonNode s, int anno, int gare, int sprint, String prima, String ultima) {
        assertThat(s.get("year").asInt()).isEqualTo(anno);
        assertThat(s.get("races").asInt()).isEqualTo(gare);
        assertThat(s.get("sprints").asInt()).isEqualTo(sprint);
        assertThat(s.get("firstRaceDate").asText()).isEqualTo(prima);
        assertThat(s.get("lastRaceDate").asText()).isEqualTo(ultima);
    }

    @Test
    void racesDiUnaStagioneInOrdineDiRoundConISoliCampiDelContratto() {
        JsonNode gare = getJson("/api/seasons/2023/races");

        assertThat(gare).hasSize(22);
        List<Integer> round = new ArrayList<>();
        for (JsonNode g : gare) {
            assertThat(g.fieldNames()).toIterable()
                    .contains("id", "round", "name", "date", "season", "circuit", "hasSprint", "winner");
            assertThat(g.get("id").isInt()).isTrue();
            assertThat(g.get("season").asInt()).isEqualTo(2023);
            assertThat(g.get("date").asText()).matches("2023-\\d{2}-\\d{2}");
            assertThat(g.get("circuit").fieldNames()).toIterable().contains("id", "name", "country");
            round.add(g.get("round").asInt());
        }
        assertThat(round).isSorted().doesNotHaveDuplicates().startsWith(1).endsWith(22);
    }

    @Test
    void racesRiportaCircuitoVincitoreESprint() {
        JsonNode gare = getJson("/api/seasons/2023/races");

        JsonNode bahrain = gare.get(0);
        assertThat(bahrain.get("id").asInt()).isEqualTo(1098);
        assertThat(bahrain.get("round").asInt()).isEqualTo(1);
        assertThat(bahrain.get("name").asText()).isEqualTo("Bahrain Grand Prix");
        assertThat(bahrain.get("date").asText()).isEqualTo("2023-03-05");
        assertThat(bahrain.get("circuit").get("name").asText()).isEqualTo("Bahrain International Circuit");
        assertThat(bahrain.get("circuit").get("country").asText()).isEqualTo("Bahrain");
        assertThat(bahrain.get("hasSprint").asBoolean()).isFalse();
        assertThat(bahrain.get("winner").get("driver").get("code").asText()).isEqualTo("VER");
        assertThat(bahrain.get("winner").get("team").get("name").asText()).isEqualTo("Red Bull");

        // 6 weekend con sprint nel 2023 (sprint_results.csv); il vincitore resta quello della gara.
        long conSprint = 0;
        for (JsonNode g : gare) {
            conSprint += g.get("hasSprint").asBoolean() ? 1 : 0;
        }
        assertThat(conSprint).isEqualTo(6);
        JsonNode qatar = gare.get(16);
        assertThat(qatar.get("id").asInt()).isEqualTo(1115);
        assertThat(qatar.get("hasSprint").asBoolean()).isTrue();
        assertThat(qatar.get("winner").get("driver").get("code").asText()).isEqualTo("VER");
    }

    @Test
    void raceRestituisceIlDettaglioConCircuitoESessioni() {
        JsonNode gara = getJson("/api/races/1098");

        assertThat(gara.get("id").asInt()).isEqualTo(1098);
        assertThat(gara.get("season").asInt()).isEqualTo(2023);
        assertThat(gara.get("round").asInt()).isEqualTo(1);
        assertThat(gara.get("name").asText()).isEqualTo("Bahrain Grand Prix");
        assertThat(gara.get("date").asText()).isEqualTo("2023-03-05");
        assertThat(gara.get("startTimeUtc").asText()).isEqualTo("15:00:00");
        assertThat(gara.get("circuit").get("id").asInt()).isEqualTo(3);
        assertThat(gara.get("circuit").get("name").asText()).isEqualTo("Bahrain International Circuit");
        assertThat(gara.get("circuit").get("locality").asText()).isEqualTo("Sakhir");
        assertThat(gara.get("circuit").get("country").asText()).isEqualTo("Bahrain");
        assertThat(gara.get("hasSprint").asBoolean()).isFalse();
        assertThat(gara.get("sessions").findValuesAsText("type"))
                .containsExactly("fp1", "fp2", "fp3", "qualifying", "race");
        JsonNode sessioneGara = gara.get("sessions").get(4);
        assertThat(sessioneGara.get("date").asText()).isEqualTo("2023-03-05");
        assertThat(sessioneGara.get("hasResults").asBoolean()).isTrue();
        assertThat(sessioneGara.get("hasLaps").asBoolean()).isTrue();
        assertThat(gara.get("sessions").get(0).get("hasResults").asBoolean()).isFalse();
    }

    @Test
    void raceConSprintElencaLaSessioneSprint() {
        JsonNode gara = getJson("/api/races/1115");

        assertThat(gara.get("name").asText()).isEqualTo("Qatar Grand Prix");
        assertThat(gara.get("hasSprint").asBoolean()).isTrue();
        assertThat(gara.get("sessions").findValuesAsText("type")).contains("sprint", "race");
        for (JsonNode s : gara.get("sessions")) {
            if (s.get("type").asText().equals("sprint")) {
                assertThat(s.get("date").asText()).isEqualTo("2023-10-07");
                assertThat(s.get("hasResults").asBoolean()).isTrue();
                assertThat(s.get("hasLaps").asBoolean()).isFalse();
            }
        }
    }
}
