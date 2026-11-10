package com.f1dataplatform.backend.api;

import com.f1dataplatform.backend.dto.DriverStandingDto;
import com.f1dataplatform.backend.dto.RaceSummaryDto;
import com.f1dataplatform.backend.dto.SeasonDriverDto;
import com.f1dataplatform.backend.dto.SeasonDto;
import com.f1dataplatform.backend.dto.TeamDto;
import com.f1dataplatform.backend.dto.TeamStandingDto;
import com.f1dataplatform.backend.error.NotFoundException;
import com.f1dataplatform.backend.repository.RaceRepository;
import com.f1dataplatform.backend.repository.SeasonRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.util.List;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping(path = "/api/seasons", produces = MediaType.APPLICATION_JSON_VALUE)
@Tag(name = "Stagioni", description = "Stagioni e calendario")
public class SeasonController {

    private static final String STANDINGS_NOTE = """
            poi più secondi posti, e così via). È la classifica aggiornata all'ultima gara caricata; non applica \
            penalizzazioni né regole storiche sui migliori risultati, quindi per alcune stagioni può differire \
            da quella ufficiale. Risponde 404 se la stagione non ha gare caricate.""";

    private final RaceRepository races;
    private final SeasonRepository seasons;

    public SeasonController(RaceRepository races, SeasonRepository seasons) {
        this.races = races;
        this.seasons = seasons;
    }

    @GetMapping
    @Operation(summary = "Elenco delle stagioni",
            description = "Stagioni con almeno un Gran Premio caricato, dalla più recente, con il numero di gare.")
    public List<SeasonDto> seasons() {
        return races.findSeasons();
    }

    @GetMapping("/{year}/races")
    @Operation(summary = "Calendario di una stagione",
            description = "Gran Premi della stagione in ordine di round, con circuito, vincitore e presenza della "
                    + "sprint. Risponde 404 se la stagione non ha gare caricate.")
    @ApiResponse(responseCode = "200", description = "Calendario della stagione.")
    @BadRequestResponse
    @NotFoundResponse
    public List<RaceSummaryDto> races(
            @Parameter(description = "Anno della stagione.", example = "2023") @PathVariable int year) {
        List<RaceSummaryDto> gare = races.findRacesBySeason(year);
        if (gare.isEmpty()) {
            throw new NotFoundException("Stagione %d inesistente o senza gare".formatted(year));
        }
        return gare;
    }

    @GetMapping("/{year}/drivers")
    @Operation(summary = "Piloti di una stagione",
            description = "Piloti con almeno un risultato di gara nella stagione, in ordine di cognome. team è la "
                    + "scuderia più recente (quella dell'ultima gara disputata nella stagione); teams elenca tutte "
                    + "le scuderie con cui il pilota ha corso, in ordine di prima apparizione. Risponde 404 se la "
                    + "stagione non ha gare caricate.")
    @ApiResponse(responseCode = "200", description = "Piloti della stagione.")
    @BadRequestResponse
    @NotFoundResponse
    public List<SeasonDriverDto> drivers(
            @Parameter(description = "Anno della stagione.", example = "2023") @PathVariable int year) {
        richiediStagione(year);
        return seasons.findDrivers(year);
    }

    @GetMapping("/{year}/teams")
    @Operation(summary = "Scuderie di una stagione",
            description = "Scuderie con almeno un risultato di gara nella stagione, in ordine di nome. Risponde "
                    + "404 se la stagione non ha gare caricate.")
    @ApiResponse(responseCode = "200", description = "Scuderie della stagione.")
    @BadRequestResponse
    @NotFoundResponse
    public List<TeamDto> teams(
            @Parameter(description = "Anno della stagione.", example = "2023") @PathVariable int year) {
        richiediStagione(year);
        return seasons.findTeams(year);
    }

    @GetMapping("/{year}/standings/drivers")
    @Operation(summary = "Classifica piloti di una stagione",
            description = "Classifica di campionato calcolata dai risultati caricati: points somma i punti delle "
                    + "gare e delle sprint (dettaglio in racePoints e sprintPoints); wins e podiums contano le "
                    + "sole gare. A parità di punti decide il confronto dei piazzamenti in gara (più vittorie, "
                    + STANDINGS_NOTE)
    @ApiResponse(responseCode = "200", description = "Classifica piloti.")
    @BadRequestResponse
    @NotFoundResponse
    public List<DriverStandingDto> driverStandings(
            @Parameter(description = "Anno della stagione.", example = "2023") @PathVariable int year) {
        richiediStagione(year);
        return seasons.driverStandings(year);
    }

    @GetMapping("/{year}/standings/teams")
    @Operation(summary = "Classifica scuderie di una stagione",
            description = "Classifica di campionato calcolata dai risultati caricati: points somma i punti delle "
                    + "gare e delle sprint di tutte le vetture (dettaglio in racePoints e sprintPoints); wins e "
                    + "podiums contano le sole gare, e podiums conta i piazzamenti (due vetture a podio valgono "
                    + "due). A parità di punti decide il confronto dei piazzamenti in gara (più vittorie, "
                    + STANDINGS_NOTE)
    @ApiResponse(responseCode = "200", description = "Classifica scuderie.")
    @BadRequestResponse
    @NotFoundResponse
    public List<TeamStandingDto> teamStandings(
            @Parameter(description = "Anno della stagione.", example = "2023") @PathVariable int year) {
        richiediStagione(year);
        return seasons.teamStandings(year);
    }

    private void richiediStagione(int year) {
        if (!seasons.seasonHasRaces(year)) {
            throw new NotFoundException("Stagione %d inesistente o senza gare".formatted(year));
        }
    }
}
