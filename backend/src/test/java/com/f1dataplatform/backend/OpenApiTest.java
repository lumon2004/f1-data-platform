package com.f1dataplatform.backend;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.List;
import org.junit.jupiter.api.Test;

/** Documentazione OpenAPI generata: percorsi, schemi delle risposte, errori, definizioni dichiarate. */
class OpenApiTest extends PostgresIntegrationTest {

    private static final String ERRORE = "#/components/schemas/ApiError";

    private static final List<String> PERCORSI = List.of(
            "/api/seasons",
            "/api/seasons/{year}/races",
            "/api/races/{raceId}",
            "/api/races/{raceId}/results",
            "/api/races/{raceId}/laps/{driverId}",
            "/api/drivers/{driverId}/statistics",
            "/api/teams/{teamId}/statistics");

    @Test
    void documentaISettePercorsiConDescrizioneESchemaDellaRisposta() {
        JsonNode doc = getJson("/v3/api-docs");

        assertThat(doc.get("info").get("title").asText()).isEqualTo("F1 Data Platform API");
        assertThat(doc.get("paths").fieldNames()).toIterable().containsExactlyInAnyOrderElementsOf(PERCORSI);
        for (String percorso : PERCORSI) {
            JsonNode get = doc.get("paths").get(percorso).get("get");
            assertThat(get).as("GET %s", percorso).isNotNull();
            assertThat(get.get("summary").asText()).as("summary di %s", percorso).isNotBlank();
            assertThat(get.get("description").asText()).as("descrizione di %s", percorso).isNotBlank();
            JsonNode schema = get.at("/responses/200/content/application~1json/schema");
            assertThat(schema.isMissingNode()).as("schema della risposta 200 di %s", percorso).isFalse();
            String riferimento = schema.has("$ref") ? schema.get("$ref").asText() : schema.at("/items/$ref").asText();
            assertThat(riferimento).as("schema tipizzato per %s", percorso).startsWith("#/components/schemas/");
        }
    }

    @Test
    void documentaGliErroriConLoSchemaComune() {
        JsonNode doc = getJson("/v3/api-docs");

        for (String percorso : PERCORSI) {
            JsonNode risposte = doc.get("paths").get(percorso).get("get").get("responses");
            assertThat(risposte.at("/500/content/application~1json/schema/$ref").asText())
                    .as("500 di %s", percorso).isEqualTo(ERRORE);
            if (!percorso.equals("/api/seasons")) {
                assertThat(risposte.at("/404/content/application~1json/schema/$ref").asText())
                        .as("404 di %s", percorso).isEqualTo(ERRORE);
                assertThat(risposte.at("/400/content/application~1json/schema/$ref").asText())
                        .as("400 di %s", percorso).isEqualTo(ERRORE);
            }
        }
        JsonNode errore = doc.at("/components/schemas/ApiError/properties");
        assertThat(errore.fieldNames()).toIterable().contains("status", "message", "error", "path", "timestamp");
    }

    @Test
    void gliSchemiEspongonoICampiDelContratto() {
        JsonNode schemi = getJson("/v3/api-docs").at("/components/schemas");

        assertThat(schemi.at("/Season/properties").fieldNames()).toIterable().contains("year");
        assertThat(schemi.at("/RaceSummary/properties").fieldNames()).toIterable()
                .contains("id", "round", "name", "date");
        assertThat(schemi.at("/Race/properties").fieldNames()).toIterable()
                .contains("id", "season", "round", "name", "date", "circuit");
        assertThat(schemi.at("/Circuit/properties").fieldNames()).toIterable().contains("id", "name", "country");
        assertThat(schemi.at("/Result/properties").fieldNames()).toIterable()
                .contains("position", "points", "status", "laps", "driver", "team");
        assertThat(schemi.at("/Driver/properties").fieldNames()).toIterable().contains("id", "code", "name");
        assertThat(schemi.at("/Team/properties").fieldNames()).toIterable().contains("id", "name");
        assertThat(schemi.at("/Lap/properties").fieldNames()).toIterable().containsExactly("lap", "position", "timeMs");
        for (String statistiche : List.of("DriverStatistics", "TeamStatistics")) {
            assertThat(schemi.at("/" + statistiche + "/properties").fieldNames()).toIterable()
                    .contains("races", "wins", "podiums", "points");
        }
    }

    @Test
    void dichiaraLeDefinizioniDiPodiGareEPunti() {
        JsonNode doc = getJson("/v3/api-docs");

        String scuderia = doc.at("/paths/~1api~1teams~1{teamId}~1statistics/get/description").asText();
        assertThat(scuderia).contains("piazzamenti a podio").contains("può superare races")
                .contains("iscrizioni").contains("sprintPoints");
        String pilota = doc.at("/paths/~1api~1drivers~1{driverId}~1statistics/get/description").asText();
        assertThat(pilota).contains("iscrizioni").contains("le sprint non entrano");
        assertThat(doc.at("/components/schemas/TeamStatistics/properties/podiums/description").asText())
                .contains("due podi");
        assertThat(doc.at("/components/schemas/DriverStatistics/properties/points/description").asText())
                .contains("Non comprende i punti delle sprint");
        String classifica = doc.at("/paths/~1api~1races~1{raceId}~1results/get/description").asText();
        assertThat(classifica).contains("mai quelli della sprint");
    }
}
