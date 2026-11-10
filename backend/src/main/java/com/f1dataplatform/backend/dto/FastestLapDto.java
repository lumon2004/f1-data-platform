package com.f1dataplatform.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(name = "FastestLap", description = "Giro più veloce del pilota nella sessione.")
public record FastestLapDto(
        @Schema(description = "Numero del giro.", example = "44", nullable = true) Integer lap,
        @Schema(description = "Posizione nella graduatoria dei giri veloci (1 = giro più veloce della gara).",
                example = "6", nullable = true) Integer rank,
        @Schema(description = "Tempo in millisecondi.", example = "96236", nullable = true) Integer timeMs,
        @Schema(description = "Velocità media in km/h.", example = "202.452", nullable = true) Double speedKph) {
}
