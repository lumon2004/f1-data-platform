package com.f1dataplatform.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(name = "QualifyingResult", description = "Riga della classifica della qualifica.")
public record QualifyingResultDto(
        @Schema(description = "Posizione in qualifica.", example = "1") int position,
        DriverDto driver,
        TeamDto team,
        @Schema(description = "Numero di gara della vettura.", example = "1", nullable = true) Integer carNumber,
        @Schema(description = "Miglior tempo in Q1, in millisecondi.", example = "91295", nullable = true) Integer q1Ms,
        @Schema(description = "Miglior tempo in Q2; null se eliminato in Q1.", example = "90503", nullable = true)
        Integer q2Ms,
        @Schema(description = "Miglior tempo in Q3; null se eliminato prima.", example = "89708", nullable = true)
        Integer q3Ms) {
}
