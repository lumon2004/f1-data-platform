package com.f1dataplatform.backend.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(name = "DriverStatistics", description = """
        Statistiche di un pilota, calcolate sulle sole gare (Gran Premi): le sprint non contano \
        in nessun campo tranne sprintPoints.""")
public record DriverStatisticsDto(
        DriverDto driver,
        @Schema(description = "Stagione del filtro; null se le statistiche coprono tutti i dati caricati.",
                example = "2023", nullable = true) Integer season,
        @Schema(description = "Gran Premi a cui il pilota è iscritto: gare distinte in cui compare in classifica, "
                + "comprese quelle in cui non è partito.", example = "22") int races,
        @Schema(description = "Gran Premi in cui il pilota ha preso il via: come races, escluse le gare con esito "
                + "withdrawn o failed_to_qualify.", example = "22") int starts,
        @Schema(description = "Gare vinte.", example = "19") int wins,
        @Schema(description = "Piazzamenti tra i primi tre.", example = "21") int podiums,
        @Schema(description = "Punti ottenuti nelle gare. Non comprende i punti delle sprint (vedi sprintPoints): "
                + "il totale di campionato è points + sprintPoints.", example = "530") double points,
        @Schema(description = "Punti ottenuti nelle gare sprint.", example = "45") double sprintPoints,
        @Schema(description = "Gare iniziate dalla prima casella della griglia.", example = "12") int poles,
        @Schema(description = "Gare in cui il pilota ha segnato il giro più veloce.", example = "9") int fastestLaps,
        @Schema(description = "Gare concluse con un ritiro (esito retired).", example = "0") int retirements,
        @Schema(description = "Miglior posizione finale; null senza gare classificate.", example = "1",
                nullable = true) Integer bestFinish,
        @Schema(description = "Media delle posizioni finali nelle gare classificate, a due decimali.",
                example = "1.27", nullable = true) Double averageFinish,
        @Schema(description = "Media delle caselle di partenza (escluse pit lane e mancate partenze), a due decimali.",
                example = "3.18", nullable = true) Double averageGrid) {

    public static DriverStatisticsDto of(DriverDto driver, Integer season, StatisticsValues v) {
        return new DriverStatisticsDto(driver, season, v.races(), v.starts(), v.wins(), v.podiums(), v.points(),
                v.sprintPoints(), v.poles(), v.fastestLaps(), v.retirements(), v.bestFinish(), v.averageFinish(),
                v.averageGrid());
    }
}
