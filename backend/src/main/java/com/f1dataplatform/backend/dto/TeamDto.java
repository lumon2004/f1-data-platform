package com.f1dataplatform.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(name = "Team", description = "Scuderia (solo dati testuali).")
public record TeamDto(
        @Schema(description = "Identificativo della scuderia, da usare negli altri endpoint.", example = "9") int id,
        @Schema(example = "Red Bull") String name,
        @Schema(example = "Austrian", nullable = true) String nationality) {
}
