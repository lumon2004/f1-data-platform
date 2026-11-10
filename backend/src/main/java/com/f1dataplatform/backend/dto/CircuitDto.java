package com.f1dataplatform.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(name = "Circuit", description = "Circuito che ospita il Gran Premio.")
public record CircuitDto(
        @Schema(description = "Identificativo del circuito.", example = "3") int id,
        @Schema(example = "Bahrain International Circuit") String name,
        @Schema(description = "Località; può mancare.", example = "Sakhir", nullable = true) String locality,
        @Schema(example = "Bahrain") String country) {
}
