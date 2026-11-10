package com.f1dataplatform.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(name = "TeamStatistics", description = """
        Statistiche di una scuderia, calcolate sulle sole gare (Gran Premi) e su tutte le sue vetture: \
        le sprint non contano in nessun campo tranne sprintPoints.""")
public record TeamStatisticsDto(
        TeamDto team,
        @Schema(description = "Stagione del filtro; null se le statistiche coprono tutti i dati caricati.",
                example = "2023", nullable = true) Integer season,
        @Schema(description = "Gran Premi a cui la scuderia è iscritta: gare distinte con almeno una sua vettura "
                + "in classifica.", example = "22") int races,
        @Schema(description = "Gran Premi in cui almeno una vettura della scuderia ha preso il via.", example = "22")
        int starts,
        @Schema(description = "Gare vinte.", example = "21") int wins,
        @Schema(description = "Piazzamenti a podio: ogni vettura tra i primi tre conta, quindi due vetture sul podio "
                + "nella stessa gara valgono due podi e il valore può superare races.", example = "30") int podiums,
        @Schema(description = "Punti ottenuti nelle gare da tutte le vetture. Non comprende i punti delle sprint "
                + "(vedi sprintPoints): il totale di campionato è points + sprintPoints.", example = "790")
        double points,
        @Schema(description = "Punti ottenuti nelle gare sprint.", example = "70") double sprintPoints,
        @Schema(description = "Gare in cui una vettura della scuderia è partita dalla prima casella.", example = "14")
        int poles,
        @Schema(description = "Gare in cui una vettura della scuderia ha segnato il giro più veloce.", example = "11")
        int fastestLaps,
        @Schema(description = "Ritiri: vetture con esito retired (più di uno per gara è possibile).", example = "2")
        int retirements,
        @Schema(description = "Miglior posizione finale; null senza vetture classificate.", example = "1",
                nullable = true) Integer bestFinish,
        @Schema(description = "Media delle posizioni finali delle vetture classificate, a due decimali.",
                example = "2.81", nullable = true) Double averageFinish,
        @Schema(description = "Media delle caselle di partenza delle vetture (escluse pit lane e mancate partenze), "
                + "a due decimali.", example = "5.57", nullable = true) Double averageGrid) {

    public static TeamStatisticsDto of(TeamDto team, Integer season, StatisticsValues v) {
        return new TeamStatisticsDto(team, season, v.races(), v.starts(), v.wins(), v.podiums(), v.points(),
                v.sprintPoints(), v.poles(), v.fastestLaps(), v.retirements(), v.bestFinish(), v.averageFinish(),
                v.averageGrid());
    }
}
