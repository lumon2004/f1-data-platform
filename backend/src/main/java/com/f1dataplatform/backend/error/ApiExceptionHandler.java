package com.f1dataplatform.backend.error;

import jakarta.servlet.http.HttpServletRequest;
import java.time.Instant;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.ErrorResponse;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

/**
 * Traduce ogni eccezione in una risposta JSON con lo stesso corpo ({@link ApiError}).
 *
 * <p>I messaggi sono scritti qui: quelli delle eccezioni interne (SQL, driver, framework) non
 * arrivano mai al client.
 */
@RestControllerAdvice
public class ApiExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(ApiExceptionHandler.class);

    @ExceptionHandler(NotFoundException.class)
    ResponseEntity<ApiError> nonTrovato(NotFoundException ex, HttpServletRequest request) {
        return risposta(HttpStatus.NOT_FOUND, ex.getMessage(), request);
    }

    @ExceptionHandler(BadRequestException.class)
    ResponseEntity<ApiError> nonValido(BadRequestException ex, HttpServletRequest request) {
        return risposta(HttpStatus.BAD_REQUEST, ex.getMessage(), request);
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    ResponseEntity<ApiError> tipoNonValido(MethodArgumentTypeMismatchException ex, HttpServletRequest request) {
        String messaggio = "Parametro '%s' non valido: '%s' non è un numero intero ammesso"
                .formatted(ex.getName(), ex.getValue());
        return risposta(HttpStatus.BAD_REQUEST, messaggio, request);
    }

    @ExceptionHandler(MissingServletRequestParameterException.class)
    ResponseEntity<ApiError> parametroMancante(MissingServletRequestParameterException ex,
            HttpServletRequest request) {
        return risposta(HttpStatus.BAD_REQUEST, "Parametro '%s' mancante".formatted(ex.getParameterName()), request);
    }

    @ExceptionHandler(NoResourceFoundException.class)
    ResponseEntity<ApiError> percorsoInesistente(NoResourceFoundException ex, HttpServletRequest request) {
        return risposta(HttpStatus.NOT_FOUND, "Percorso inesistente: " + request.getRequestURI(), request);
    }

    /**
     * Database irraggiungibile (connessione non ottenuta entro il timeout, o caduta durante la query):
     * 503, perché il guasto è temporaneo e non dipende dalla richiesta.
     */
    @ExceptionHandler(DataAccessResourceFailureException.class)
    ResponseEntity<ApiError> databaseNonDisponibile(DataAccessResourceFailureException ex,
            HttpServletRequest request) {
        log.warn("Database non disponibile su {} {}: {}", request.getMethod(), request.getRequestURI(),
                ex.getMostSpecificCause().getMessage());
        return risposta(HttpStatus.SERVICE_UNAVAILABLE,
                ErrorMessages.generico(HttpStatus.SERVICE_UNAVAILABLE.value()), request);
    }

    @ExceptionHandler(Exception.class)
    ResponseEntity<ApiError> altro(Exception ex, HttpServletRequest request) {
        if (ex instanceof ErrorResponse errore && !errore.getStatusCode().is5xxServerError()) {
            // Errori del client riconosciuti da Spring MVC (metodo non consentito, formato non accettabile, ...).
            return risposta(errore.getStatusCode(), ErrorMessages.generico(errore.getStatusCode().value()), request);
        }
        log.error("Errore non gestito su {} {}", request.getMethod(), request.getRequestURI(), ex);
        return risposta(HttpStatus.INTERNAL_SERVER_ERROR,
                ErrorMessages.generico(HttpStatus.INTERNAL_SERVER_ERROR.value()), request);
    }

    private static ResponseEntity<ApiError> risposta(HttpStatusCode stato, String messaggio,
            HttpServletRequest request) {
        ApiError corpo = new ApiError(stato.value(), ErrorMessages.nome(stato.value()), messaggio,
                request.getRequestURI(), Instant.now());
        return ResponseEntity.status(stato).contentType(MediaType.APPLICATION_JSON).body(corpo);
    }
}
