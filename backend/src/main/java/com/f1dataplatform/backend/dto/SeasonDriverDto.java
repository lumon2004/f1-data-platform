package com.f1dataplatform.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

@Schema(name = "SeasonDriver", description = "Pilota con almeno un risultato di gara nella stagione.")
public record SeasonDriverDto(
        @Schema(description = "Identificativo del pilota.", example = "830") int id,
        @Schema(description = "Sigla di tre lettere; assente per i piloti storici.", example = "VER", nullable = true)
        String code,
        @Schema(description = "Nome e cognome.", example = "Max Verstappen") String name,
        @Schema(example = "Max") String givenName,
        @Schema(example = "Verstappen") String familyName,
        @Schema(description = "Numero permanente; può mancare.", example = "33", nullable = true) Integer number,
        @Schema(example = "Dutch", nullable = true) String nationality,
        @Schema(description = "Scuderia più recente della stagione: quella dell'ultima gara disputata.") TeamDto team,
        @Schema(description = "Tutte le scuderie con cui il pilota ha corso nella stagione, in ordine di prima "
                + "apparizione; un solo elemento se non ha cambiato scuderia.") List<TeamDto> teams) {
}
