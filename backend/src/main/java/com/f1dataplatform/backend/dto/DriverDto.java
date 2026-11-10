package com.f1dataplatform.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(name = "Driver", description = "Pilota (solo dati testuali).")
public record DriverDto(
        @Schema(description = "Identificativo del pilota, da usare negli altri endpoint.", example = "830") int id,
        @Schema(description = "Sigla di tre lettere; assente per i piloti storici.", example = "VER", nullable = true)
        String code,
        @Schema(description = "Nome e cognome.", example = "Max Verstappen") String name,
        @Schema(example = "Max") String givenName,
        @Schema(example = "Verstappen") String familyName,
        @Schema(description = "Numero permanente; può mancare.", example = "33", nullable = true) Integer number,
        @Schema(example = "Dutch", nullable = true) String nationality) {
}
