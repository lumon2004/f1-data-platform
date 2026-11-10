package com.f1dataplatform.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDate;
import java.time.LocalTime;

@Schema(name = "Session", description = "Sessione del weekend di gara.")
public record SessionDto(
        @Schema(description = "Tipo di sessione.", example = "race",
                allowableValues = {"fp1", "fp2", "fp3", "qualifying", "sprint", "race"}) String type,
        @Schema(description = "Data; può mancare per le sessioni storiche.", example = "2023-03-05", nullable = true)
        LocalDate date,
        @Schema(description = "Ora di inizio in UTC; può mancare.", example = "15:00:00", type = "string",
                nullable = true) LocalTime startTimeUtc,
        @Schema(description = "Vero se per la sessione esiste una classifica "
                + "(GET /api/races/{raceId}/results?session=...).") boolean hasResults,
        @Schema(description = "Vero se per la sessione esistono giri cronometrati.") boolean hasLaps) {
}
