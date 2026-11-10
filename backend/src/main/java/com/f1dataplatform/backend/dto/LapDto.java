package com.f1dataplatform.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(name = "Lap", description = "Giro cronometrato di un pilota in gara.")
public record LapDto(
        @Schema(description = "Numero del giro.", example = "1") int lap,
        @Schema(description = "Posizione al termine del giro.", example = "1", nullable = true) Integer position,
        @Schema(description = "Tempo sul giro in millisecondi.", example = "99019") int timeMs) {
}
