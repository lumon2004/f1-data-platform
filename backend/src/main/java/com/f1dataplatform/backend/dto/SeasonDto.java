package com.f1dataplatform.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDate;

@Schema(name = "Season", description = "Stagione con almeno un Gran Premio caricato.")
public record SeasonDto(
        @Schema(example = "2023") int year,
        @Schema(description = "Numero di Gran Premi della stagione.", example = "22") int races,
        @Schema(description = "Numero di Gran Premi con gara sprint.", example = "6") int sprints,
        @Schema(description = "Data del primo Gran Premio.", example = "2023-03-05") LocalDate firstRaceDate,
        @Schema(description = "Data dell'ultimo Gran Premio.", example = "2023-11-26") LocalDate lastRaceDate) {
}
