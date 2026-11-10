package com.f1dataplatform.backend;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

/**
 * Piloti, scuderie e classifiche di una stagione. Valori attesi calcolati a mano da results.csv e
 * sprint_results.csv del dataset di esempio; i totali coincidono con le classifiche ufficiali.
 */
class SeasonApiTest extends PostgresIntegrationTest {

    @Test
    void driversDellaStagioneInOrdineDiCognomeConLaScuderia() {
        JsonNode piloti = getJson("/api/seasons/2023/drivers");

        // 22 piloti con almeno una gara nel 2023 (20 titolari, più Lawson e De Vries/Ricciardo in AlphaTauri).
        assertThat(piloti).hasSize(22);
        for (JsonNode p : piloti) {
            assertThat(p.fieldNames()).toIterable().containsExactly("id", "code", "name", "givenName", "familyName",
                    "number", "nationality", "team", "teams");
            assertThat(p.get("team").fieldNames()).toIterable().contains("id", "name");
            assertThat(p.get("teams")).hasSize(1);
            assertThat(p.get("teams").get(0)).isEqualTo(p.get("team"));
        }
        assertThat(piloti.findValuesAsText("familyName")).startsWith("Albon", "Alonso", "Bottas", "Gasly")
                .isSorted().contains("Verstappen", "Lawson", "de Vries");
        JsonNode albon = piloti.get(0);
        assertThat(albon.get("id").asInt()).isEqualTo(848);
        assertThat(albon.get("code").asText()).isEqualTo("ALB");
        assertThat(albon.get("name").asText()).isEqualTo("Alexander Albon");
        assertThat(albon.get("team").get("name").asText()).isEqualTo("Williams");
    }

    @Test
    void driverConDueScuderieNellaStagione() {
        // Bearman 2024: una gara con Ferrari (Arabia Saudita), poi due con Haas.
        JsonNode piloti = getJson("/api/seasons/2024/drivers");

        assertThat(piloti).hasSize(24);
        JsonNode bearman = piloti.get(2);
        assertThat(bearman.get("code").asText()).isEqualTo("BEA");
        assertThat(bearman.get("team").get("name").asText()).isEqualTo("Haas F1 Team");
        assertThat(bearman.get("teams").findValuesAsText("name")).containsExactly("Ferrari", "Haas F1 Team");
        long conPiuScuderie = 0;
        for (JsonNode p : piloti) {
            conPiuScuderie += p.get("teams").size() > 1 ? 1 : 0;
        }
        assertThat(conPiuScuderie).isEqualTo(1);
    }

    @Test
    void teamsDellaStagioneInOrdineDiNome() {
        JsonNode scuderie = getJson("/api/seasons/2024/teams");

        assertThat(scuderie.findValuesAsText("name")).containsExactly("Alpine F1 Team", "Aston Martin", "Ferrari",
                "Haas F1 Team", "McLaren", "Mercedes", "RB F1 Team", "Red Bull", "Sauber", "Williams");
        for (JsonNode s : scuderie) {
            assertThat(s.fieldNames()).toIterable().containsExactly("id", "name", "nationality");
        }
        // Nel 2023 le stesse dieci squadre avevano in parte altri nomi.
        assertThat(getJson("/api/seasons/2023/teams").findValuesAsText("name"))
                .hasSize(10).contains("Alfa Romeo", "AlphaTauri").doesNotContain("Sauber", "RB F1 Team");
    }

    @ParameterizedTest(name = "piloti {0}: {1}° {2}")
    @CsvSource({
            // stagione, posizione, sigla, scuderia, punti, punti gara, punti sprint, vittorie, podi
            "2023,  1, VER, Red Bull,     575, 530, 45, 19, 21",
            "2023,  2, PER, Red Bull,     285, 260, 25,  2,  9",
            "2023,  3, HAM, Mercedes,     234, 217, 17,  0,  6",
            // Pari a 206 punti: Alonso davanti per i piazzamenti (3 secondi posti contro 3, poi 5 terzi contro 3).
            "2023,  4, ALO, Aston Martin, 206, 198,  8,  0,  8",
            "2023,  5, LEC, Ferrari,      206, 185, 21,  0,  6",
            "2023,  6, NOR, McLaren,      205, 184, 21,  0,  7",
            "2023, 22, DEV, AlphaTauri,     0,   0,  0,  0,  0",
            "2022,  1, VER, Red Bull,     454, 433, 21, 15, 17",
            "2022,  2, LEC, Ferrari,      308, 291, 17,  3, 11",
            "2022,  3, PER, Red Bull,     305, 291, 14,  2, 11",
            // Pari a 37 punti: Ricciardo davanti (miglior risultato un quinto posto, Vettel un sesto).
            "2022, 11, RIC, McLaren,       37,  34,  3,  0,  0",
            "2022, 12, VET, Aston Martin,  37,  37,  0,  0,  0",
            "2024,  1, VER, Red Bull,     437, 399, 38,  9, 14",
            "2024,  2, NOR, McLaren,      374, 344, 30,  4, 13",
            "2024,  3, LEC, Ferrari,      356, 327, 29,  3, 13",
    })
    void classificaPiloti(int stagione, int posizione, String sigla, String scuderia, double punti, double gara,
            double sprint, int vittorie, int podi) {
        JsonNode riga = getJson("/api/seasons/" + stagione + "/standings/drivers").get(posizione - 1);

        assertThat(riga.get("position").asInt()).isEqualTo(posizione);
        assertThat(riga.get("driver").get("code").asText()).isEqualTo(sigla);
        assertThat(riga.get("team").get("name").asText()).isEqualTo(scuderia);
        assertThat(riga.get("points").asDouble()).as("points").isEqualTo(punti);
        assertThat(riga.get("racePoints").asDouble()).as("racePoints").isEqualTo(gara);
        assertThat(riga.get("sprintPoints").asDouble()).as("sprintPoints").isEqualTo(sprint);
        assertThat(riga.get("wins").asInt()).as("wins").isEqualTo(vittorie);
        assertThat(riga.get("podiums").asInt()).as("podiums").isEqualTo(podi);
    }

    @ParameterizedTest(name = "scuderie {0}: {1}° {2}")
    @CsvSource({
            // stagione, posizione, scuderia, punti, punti gara, punti sprint, vittorie, podi (piazzamenti)
            "2023,  1, Red Bull,     860, 790, 70, 21, 30",
            "2023,  2, Mercedes,     409, 374, 35,  0,  8",
            "2023,  3, Ferrari,      406, 363, 43,  1,  9",
            "2023, 10, Haas F1 Team,  12,   9,  3,  0,  0",
            "2022,  1, Red Bull,     759, 724, 35, 17, 28",
            "2022,  2, Ferrari,      554, 519, 35,  4, 20",
            // Pari a 55 punti: Alfa Romeo davanti (miglior risultato un quinto posto, Aston Martin un sesto).
            "2022,  6, Alfa Romeo,    55,  53,  2,  0,  0",
            "2022,  7, Aston Martin,  55,  55,  0,  0,  0",
            "2024,  1, McLaren,      666, 609, 57,  6, 21",
            "2024,  2, Ferrari,      652, 595, 57,  5, 22",
            "2024,  3, Red Bull,     589, 537, 52,  9, 18",
    })
    void classificaScuderie(int stagione, int posizione, String scuderia, double punti, double gara, double sprint,
            int vittorie, int podi) {
        JsonNode riga = getJson("/api/seasons/" + stagione + "/standings/teams").get(posizione - 1);

        assertThat(riga.get("position").asInt()).isEqualTo(posizione);
        assertThat(riga.get("team").get("name").asText()).isEqualTo(scuderia);
        assertThat(riga.get("points").asDouble()).as("points").isEqualTo(punti);
        assertThat(riga.get("racePoints").asDouble()).as("racePoints").isEqualTo(gara);
        assertThat(riga.get("sprintPoints").asDouble()).as("sprintPoints").isEqualTo(sprint);
        assertThat(riga.get("wins").asInt()).as("wins").isEqualTo(vittorie);
        assertThat(riga.get("podiums").asInt()).as("podiums").isEqualTo(podi);
    }

    @Test
    void leClassificheSonoCompleteOrdinateESenzaExAequo() {
        for (int anno : new int[] {2022, 2023, 2024}) {
            JsonNode piloti = getJson("/api/seasons/" + anno + "/standings/drivers");
            JsonNode scuderie = getJson("/api/seasons/" + anno + "/standings/teams");

            assertThat(piloti).hasSize(getJson("/api/seasons/" + anno + "/drivers").size());
            assertThat(scuderie).hasSize(10);
            for (JsonNode classifica : List.of(piloti, scuderie)) {
                List<Double> punti = new ArrayList<>();
                for (int i = 0; i < classifica.size(); i++) {
                    JsonNode riga = classifica.get(i);
                    assertThat(riga.get("position").asInt()).isEqualTo(i + 1);
                    assertThat(riga.get("points").asDouble())
                            .isEqualTo(riga.get("racePoints").asDouble() + riga.get("sprintPoints").asDouble());
                    punti.add(-riga.get("points").asDouble());
                }
                assertThat(punti).as("punti decrescenti").isSorted();
            }
            // La somma dei punti dei piloti è quella delle scuderie.
            assertThat(piloti.findValues("points").stream().mapToDouble(JsonNode::asDouble).sum())
                    .isEqualTo(scuderie.findValues("points").stream().mapToDouble(JsonNode::asDouble).sum());
        }
    }

    @Test
    void laClassificaPilotiHaLoSchemaAtteso() {
        JsonNode primo = getJson("/api/seasons/2023/standings/drivers").get(0);
        assertThat(primo.fieldNames()).toIterable().containsExactly("position", "driver", "team", "points",
                "racePoints", "sprintPoints", "wins", "podiums");
        assertThat(primo.get("driver").fieldNames()).toIterable().contains("id", "code", "name");

        JsonNode prima = getJson("/api/seasons/2023/standings/teams").get(0);
        assertThat(prima.fieldNames()).toIterable().containsExactly("position", "team", "points", "racePoints",
                "sprintPoints", "wins", "podiums");
    }
}
