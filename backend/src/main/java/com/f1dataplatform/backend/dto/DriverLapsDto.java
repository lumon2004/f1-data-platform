package com.f1dataplatform.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

@Schema(name = "DriverLaps", description = "Giri di un pilota in una gara.")
public record DriverLapsDto(
        DriverDto driver,
        @Schema(description = "Scuderia con cui il pilota ha corso la gara.") TeamDto team,
        @Schema(description = "Giri in ordine; lista vuota se il pilota non ha giri cronometrati.") List<LapDto> laps) {
}
