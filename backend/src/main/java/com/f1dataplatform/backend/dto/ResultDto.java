package com.f1dataplatform.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(name = "Result", description = "Riga della classifica di una sessione (gara o sprint).")
public record ResultDto(
        @Schema(description = "Posizione finale; null se il pilota non è classificato.", example = "1",
                nullable = true) Integer position,
        @Schema(description = "Ordine in classifica, valorizzato anche per i non classificati.", example = "1")
        int positionOrder,
        @Schema(description = "Punti ottenuti nella sessione.", example = "25") double points,
        @Schema(description = "Stato di arrivo secondo la fonte.", example = "Finished") String status,
        @Schema(description = "Esito.", example = "classified",
                allowableValues = {"classified", "retired", "disqualified", "excluded", "withdrawn",
                        "failed_to_qualify", "not_classified"}) String outcome,
        @Schema(description = "Giri completati.", example = "57") int laps,
        @Schema(description = "Casella di partenza; null per partenza dalla pit lane o mancata partenza.",
                example = "1", nullable = true) Integer grid,
        @Schema(description = "Numero di gara della vettura.", example = "1", nullable = true) Integer carNumber,
        @Schema(description = "Tempo totale in millisecondi; presente solo per chi arriva a pieni giri.",
                example = "5636736", nullable = true) Integer timeMs,
        @Schema(description = "Distacco dal vincitore in millisecondi (0 per il vincitore); null senza tempo.",
                example = "0", nullable = true) Integer gapMs,
        @Schema(description = "Giro più veloce; null se la fonte non lo riporta.", nullable = true)
        FastestLapDto fastestLap,
        DriverDto driver,
        TeamDto team) {
}
