package com.f1dataplatform.backend.api;

import com.f1dataplatform.backend.dto.DriverDto;
import com.f1dataplatform.backend.dto.DriverStatisticsDto;
import com.f1dataplatform.backend.dto.TeamDto;
import com.f1dataplatform.backend.dto.TeamStatisticsDto;
import com.f1dataplatform.backend.error.NotFoundException;
import com.f1dataplatform.backend.repository.StatisticsRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping(path = "/api", produces = MediaType.APPLICATION_JSON_VALUE)
@Tag(name = "Statistiche", description = "Statistiche aggregate di piloti e scuderie, calcolate dal database")
public class StatisticsController {

    private static final String DEFINIZIONI_COMUNI = """
            Si contano le sole gare (Gran Premi): le sprint non entrano in races, wins, podiums né points. \
            races conta le iscrizioni, cioè i Gran Premi distinti in cui si compare in classifica, anche senza \
            aver preso il via; starts conta le sole partenze. points è la somma dei punti delle gare; i punti \
            delle sprint sono in sprintPoints (totale di campionato = points + sprintPoints). \
            Senza il parametro season le statistiche coprono tutte le stagioni caricate; con una stagione in cui \
            non ci sono gare disputate i contatori valgono 0 e le medie null.""";

    private final StatisticsRepository statistics;

    public StatisticsController(StatisticsRepository statistics) {
        this.statistics = statistics;
    }

    @GetMapping("/drivers/{driverId}/statistics")
    @Operation(summary = "Statistiche di un pilota",
            description = "Gare, vittorie, podi, punti e medie di un pilota. podiums conta i piazzamenti tra i "
                    + "primi tre. " + DEFINIZIONI_COMUNI)
    @ApiResponse(responseCode = "200", description = "Statistiche del pilota.")
    @BadRequestResponse
    @NotFoundResponse
    public DriverStatisticsDto driver(
            @Parameter(description = "Identificativo del pilota.", example = "830") @PathVariable int driverId,
            @Parameter(description = "Limita le statistiche a una stagione.", example = "2023")
            @RequestParam(required = false) Integer season) {
        DriverDto pilota = statistics.findDriver(driverId)
                .orElseThrow(() -> new NotFoundException("Pilota %d inesistente".formatted(driverId)));
        return DriverStatisticsDto.of(pilota, season, statistics.driverStatistics(driverId, season));
    }

    @GetMapping("/teams/{teamId}/statistics")
    @Operation(summary = "Statistiche di una scuderia",
            description = "Gare, vittorie, podi, punti e medie di una scuderia, su tutte le sue vetture. podiums "
                    + "conta i piazzamenti a podio: due vetture tra i primi tre nella stessa gara valgono due "
                    + "podi, quindi podiums può superare races (le vittorie restano al massimo una per gara). "
                    + DEFINIZIONI_COMUNI)
    @ApiResponse(responseCode = "200", description = "Statistiche della scuderia.")
    @BadRequestResponse
    @NotFoundResponse
    public TeamStatisticsDto team(
            @Parameter(description = "Identificativo della scuderia.", example = "9") @PathVariable int teamId,
            @Parameter(description = "Limita le statistiche a una stagione.", example = "2023")
            @RequestParam(required = false) Integer season) {
        TeamDto scuderia = statistics.findTeam(teamId)
                .orElseThrow(() -> new NotFoundException("Scuderia %d inesistente".formatted(teamId)));
        return TeamStatisticsDto.of(scuderia, season, statistics.teamStatistics(teamId, season));
    }
}
