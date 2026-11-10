package com.f1dataplatform.backend;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.simple.JdbcClient;

class BackendApplicationTest extends PostgresIntegrationTest {

    @Autowired
    private TestRestTemplate rest;

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
    void flywayHaInizializzatoLoSchema() {
        Integer tabelle = jdbc.sql("select count(*) from information_schema.tables where table_name = 'flyway_schema_history'")
                .query(Integer.class).single();

        assertThat(tabelle).isEqualTo(1);
    }

    @Test
    void openApiDisponibile() {
        ResponseEntity<Map> risposta = rest.getForEntity("/v3/api-docs", Map.class);

        assertThat(risposta.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(risposta.getBody()).containsKey("openapi");
    }
}
