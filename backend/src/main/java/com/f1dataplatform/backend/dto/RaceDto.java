package com.f1dataplatform.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.List;

@Schema(name = "Race", description = "Dettaglio di un Gran Premio.")
public record RaceDto(
        @Schema(example = "1098") int id,
        @Schema(example = "2023") int season,
        @Schema(example = "1") int round,
        @Schema(example = "Bahrain Grand Prix") String name,
        @Schema(description = "Data della gara.", example = "2023-03-05") LocalDate date,
        @Schema(description = "Ora di inizio della gara in UTC; può mancare.", example = "15:00:00", type = "string",
                nullable = true) LocalTime startTimeUtc,
        @Schema(nullable = true) String wikipediaUrl,
        CircuitDto circuit,
        @Schema(description = "Vero se il weekend comprende una gara sprint.") boolean hasSprint,
        @Schema(description = "Sessioni del weekend in ordine cronologico di formato.") List<SessionDto> sessions) {
}
