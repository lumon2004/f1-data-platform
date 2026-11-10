package com.f1dataplatform.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(name = "TeamStanding",
        description = "Riga della classifica scuderie di una stagione, calcolata dai risultati.")
public record TeamStandingDto(
        @Schema(description = "Posizione in classifica, da 1, senza ex aequo.", example = "1") int position,
        TeamDto team,
        @Schema(description = "Punti di campionato: gare più sprint, tutte le vetture.", example = "860") double points,
        @Schema(description = "Punti ottenuti nelle gare.", example = "790") double racePoints,
        @Schema(description = "Punti ottenuti nelle sprint.", example = "70") double sprintPoints,
        @Schema(description = "Gare vinte (sprint escluse).", example = "21") int wins,
        @Schema(description = "Piazzamenti a podio in gara (sprint escluse): due vetture tra i primi tre nella "
                + "stessa gara valgono due.", example = "30") int podiums) {
}
