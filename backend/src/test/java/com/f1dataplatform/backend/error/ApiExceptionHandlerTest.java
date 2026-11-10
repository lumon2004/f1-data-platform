package com.f1dataplatform.backend.error;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.BadSqlGrammarException;
import org.springframework.mock.web.MockHttpServletRequest;

/** Errori del server: corpo comune e nessun testo dell'eccezione nella risposta. */
class ApiExceptionHandlerTest {

    private final ApiExceptionHandler handler = new ApiExceptionHandler();
    private final MockHttpServletRequest richiesta = new MockHttpServletRequest("GET", "/api/seasons");

    @Test
    void erroreImprevisto500SenzaDettagli() {
        Exception interna = new BadSqlGrammarException("query", "select * from results where segreto",
                new java.sql.SQLException("column segreto does not exist"));

        ResponseEntity<ApiError> risposta = handler.altro(interna, richiesta);

        assertThat(risposta.getStatusCode().value()).isEqualTo(500);
        ApiError corpo = risposta.getBody();
        assertThat(corpo).isNotNull();
        assertThat(corpo.status()).isEqualTo(500);
        assertThat(corpo.error()).isEqualTo("Internal Server Error");
        assertThat(corpo.message()).isEqualTo("Errore interno del server")
                .doesNotContain("segreto").doesNotContain("select");
        assertThat(corpo.path()).isEqualTo("/api/seasons");
        assertThat(corpo.timestamp()).isNotNull();
    }

    @Test
    void databaseNonDisponibile503SenzaDettagli() {
        DataAccessResourceFailureException interna = new DataAccessResourceFailureException(
                "Failed to obtain JDBC Connection", new java.sql.SQLException("Connection to db:5432 refused"));

        ResponseEntity<ApiError> risposta = handler.databaseNonDisponibile(interna, richiesta);

        assertThat(risposta.getStatusCode().value()).isEqualTo(503);
        ApiError corpo = risposta.getBody();
        assertThat(corpo).isNotNull();
        assertThat(corpo.status()).isEqualTo(503);
        assertThat(corpo.error()).isEqualTo("Service Unavailable");
        assertThat(corpo.message()).isEqualTo("Database non disponibile, riprova tra poco")
                .doesNotContain("db:5432").doesNotContain("JDBC");
        assertThat(corpo.path()).isEqualTo("/api/seasons");
    }
}
