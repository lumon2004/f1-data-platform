package com.f1dataplatform.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(name = "DriverStanding", description = "Riga della classifica piloti di una stagione, calcolata dai risultati.")
public record DriverStandingDto(
        @Schema(description = "Posizione in classifica, da 1, senza ex aequo.", example = "1") int position,
        DriverDto driver,
        @Schema(description = "Scuderia più recente del pilota nella stagione.") TeamDto team,
        @Schema(description = "Punti di campionato: gare più sprint.", example = "575") double points,
        @Schema(description = "Punti ottenuti nelle gare.", example = "530") double racePoints,
        @Schema(description = "Punti ottenuti nelle sprint.", example = "45") double sprintPoints,
        @Schema(description = "Gare vinte (sprint escluse).", example = "19") int wins,
        @Schema(description = "Piazzamenti tra i primi tre in gara (sprint escluse).", example = "21") int podiums) {
}
