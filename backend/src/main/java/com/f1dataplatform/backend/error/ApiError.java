package com.f1dataplatform.backend.error;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;

/** Corpo uniforme di ogni risposta d'errore dell'API. */
@Schema(name = "ApiError", description = "Corpo uniforme delle risposte d'errore.")
public record ApiError(
        @Schema(description = "Codice di stato HTTP.", example = "404") int status,
        @Schema(description = "Nome standard dello stato HTTP.", example = "Not Found") String error,
        @Schema(description = "Descrizione leggibile dell'errore, senza dettagli interni.",
                example = "Gara 999999 inesistente") String message,
        @Schema(description = "Percorso richiesto.", example = "/api/races/999999") String path,
        @Schema(description = "Istante dell'errore (UTC).") Instant timestamp) {
}
