package com.f1dataplatform.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(name = "Winner", description = "Vincitore del Gran Premio.")
public record WinnerDto(DriverDto driver, TeamDto team) {
}
