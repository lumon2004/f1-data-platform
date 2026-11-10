package com.f1dataplatform.backend.dto;

/** Valori aggregati calcolati in SQL, comuni alle statistiche di pilota e di scuderia. */
public record StatisticsValues(
        int races,
        int starts,
        int wins,
        int podiums,
        double points,
        double sprintPoints,
        int poles,
        int fastestLaps,
        int retirements,
        Integer bestFinish,
        Double averageFinish,
        Double averageGrid) {
}
