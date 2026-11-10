package com.f1dataplatform.backend;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.simple.JdbcClient;

class BackendApplicationTest extends PostgresIntegrationTest {

    @Autowired
    private JdbcClient jdbc;

    @Test
    void healthRispondeUp() {
        ResponseEntity<Map> risposta = rest.getForEntity("/actuator/health", Map.class);

        assertThat(risposta.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(risposta.getBody()).containsEntry("status", "UP");
    }

    @Test
    void ilDatabaseEUnPostgresqlReale() {
        String versione = jdbc.sql("select version()").query(String.class).single();

        assertThat(versione).startsWith("PostgreSQL");
    }

    @Test
    void flywayHaApplicatoLeMigrazioni() {
        Integer applicate = jdbc.sql("select count(*) from flyway_schema_history where success")
                .query(Integer.class).single();
        java.util.List<String> tabelle = jdbc.sql(
                        "select table_name from information_schema.tables where table_schema = 'public'")
                .query(String.class).list();

        assertThat(applicate).isGreaterThanOrEqualTo(4);
        assertThat(tabelle).contains("seasons", "races", "circuits", "drivers", "constructors",
                "sessions", "results", "laps", "stints", "pit_stops");
    }

    @Test
    void openApiDisponibile() {
        ResponseEntity<Map> risposta = rest.getForEntity("/v3/api-docs", Map.class);

        assertThat(risposta.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(risposta.getBody()).containsKey("openapi");
    }
}
