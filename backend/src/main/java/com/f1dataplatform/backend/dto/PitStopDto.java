package com.f1dataplatform.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalTime;

@Schema(name = "PitStop", description = "Sosta ai box di un pilota in gara.")
public record PitStopDto(
        DriverDto driver,
        @Schema(description = "Numero progressivo della sosta del pilota.", example = "1") int stop,
        @Schema(description = "Giro al termine del quale il pilota entra ai box.", example = "14") int lap,
        @Schema(description = "Durata della sosta in millisecondi (ingresso-uscita dalla pit lane); può mancare.",
                example = "24289", nullable = true) Integer durationMs,
        @Schema(description = "Ora locale della sosta; può mancare.", example = "18:26:35", type = "string",
                nullable = true) LocalTime timeOfDay) {
}
