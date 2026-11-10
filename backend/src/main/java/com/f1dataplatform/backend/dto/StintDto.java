package com.f1dataplatform.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(name = "Stint", description = "Tratto di gara di un pilota tra due soste, derivato dai pit stop.")
public record StintDto(
        DriverDto driver,
        @Schema(description = "Numero progressivo dello stint del pilota.", example = "1") int stint,
        @Schema(description = "Primo giro dello stint.", example = "1") int startLap,
        @Schema(description = "Ultimo giro dello stint.", example = "14") int endLap,
        @Schema(description = "Numero di giri dello stint.", example = "14") int laps,
        @Schema(description = "Mescola: sempre null, la fonte dei dati non contiene le mescole.", nullable = true)
        String compound) {
}
