package com.f1dataplatform.backend.error;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockHttpServletRequest;

/** Un errore imprevisto diventa un 500 con il corpo comune e senza il testo dell'eccezione. */
class ApiExceptionHandlerTest {

    @Test
    void erroreInternoSenzaDettagli() {
        MockHttpServletRequest richiesta = new MockHttpServletRequest("GET", "/api/seasons");
        Exception interna = new DataAccessResourceFailureException(
                "Connection to db:5432 refused", new java.sql.SQLException("select * from results"));

        ResponseEntity<ApiError> risposta = new ApiExceptionHandler().altro(interna, richiesta);

        assertThat(risposta.getStatusCode().value()).isEqualTo(500);
        ApiError corpo = risposta.getBody();
        assertThat(corpo).isNotNull();
        assertThat(corpo.status()).isEqualTo(500);
        assertThat(corpo.error()).isEqualTo("Internal Server Error");
        assertThat(corpo.message()).isEqualTo("Errore interno del server")
                .doesNotContain("db:5432").doesNotContain("select");
        assertThat(corpo.path()).isEqualTo("/api/seasons");
        assertThat(corpo.timestamp()).isNotNull();
    }
}
