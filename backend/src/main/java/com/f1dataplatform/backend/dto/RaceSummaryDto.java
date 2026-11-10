package com.f1dataplatform.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDate;

@Schema(name = "RaceSummary", description = "Gran Premio nel calendario di una stagione.")
public record RaceSummaryDto(
        @Schema(description = "Identificativo della gara, da usare negli altri endpoint.", example = "1098") int id,
        @Schema(example = "2023") int season,
        @Schema(example = "1") int round,
        @Schema(example = "Bahrain Grand Prix") String name,
        @Schema(description = "Data della gara.", example = "2023-03-05") LocalDate date,
        CircuitDto circuit,
        @Schema(description = "Vero se il weekend comprende una gara sprint.") boolean hasSprint,
        @Schema(description = "Vincitore della gara; null se non ci sono risultati.", nullable = true)
        WinnerDto winner) {
}
