package com.f1dataplatform.backend.api;

import com.f1dataplatform.backend.dto.DriverLapsDto;
import com.f1dataplatform.backend.dto.LapDto;
import com.f1dataplatform.backend.dto.PitStopDto;
import com.f1dataplatform.backend.dto.QualifyingResultDto;
import com.f1dataplatform.backend.dto.RaceDto;
import com.f1dataplatform.backend.dto.ResultDto;
import com.f1dataplatform.backend.dto.StintDto;
import com.f1dataplatform.backend.error.BadRequestException;
import com.f1dataplatform.backend.error.NotFoundException;
import com.f1dataplatform.backend.repository.RaceRepository;
import com.f1dataplatform.backend.repository.StatisticsRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.util.List;
import java.util.Set;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping(path = "/api/races", produces = MediaType.APPLICATION_JSON_VALUE)
@Tag(name = "Gare", description = "Dettaglio, classifiche e giri di un Gran Premio")
public class RaceController {

    /** Sessioni che hanno una classifica a punti. */
    private static final Set<String> SESSIONI_CON_CLASSIFICA = Set.of("race", "sprint");

    private final RaceRepository races;
    private final StatisticsRepository anagrafiche;

    public RaceController(RaceRepository races, StatisticsRepository anagrafiche) {
        this.races = races;
        this.anagrafiche = anagrafiche;
    }

    @GetMapping("/{raceId}")
    @Operation(summary = "Dettaglio di una gara",
            description = "Gran Premio con stagione, round, data, circuito e sessioni del weekend.")
    @ApiResponse(responseCode = "200", description = "Dettaglio della gara.")
    @BadRequestResponse
    @NotFoundResponse
    public RaceDto race(@Parameter(description = "Identificativo della gara.", example = "1098")
            @PathVariable int raceId) {
        return races.findRace(raceId).orElseThrow(() -> garaInesistente(raceId));
    }

    @GetMapping("/{raceId}/results")
    @Operation(summary = "Classifica di una gara",
            description = "Classifica in ordine di arrivo: prima i classificati, poi i non classificati "
                    + "(position null). Senza parametri restituisce solo i risultati della gara, mai quelli della "
                    + "sprint; con session=sprint restituisce la classifica della sprint, e 404 se il weekend "
                    + "non ne ha una.")
    @ApiResponse(responseCode = "200", description = "Classifica della sessione.")
    @BadRequestResponse
    @NotFoundResponse
    public List<ResultDto> results(
            @Parameter(description = "Identificativo della gara.", example = "1098") @PathVariable int raceId,
            @Parameter(description = "Sessione di cui si vuole la classifica.",
                    schema = @Schema(allowableValues = {"race", "sprint"}, defaultValue = "race"))
            @RequestParam(defaultValue = "race") String session) {
        if (!SESSIONI_CON_CLASSIFICA.contains(session)) {
            throw new BadRequestException(
                    "Parametro 'session' non valido: '%s' (valori ammessi: race, sprint)".formatted(session));
        }
        if (!races.raceExists(raceId)) {
            throw garaInesistente(raceId);
        }
        if (!session.equals("race") && !races.sessionExists(raceId, session)) {
            throw new NotFoundException("La gara %d non ha una sessione '%s'".formatted(raceId, session));
        }
        return races.findResults(raceId, session);
    }

    @GetMapping("/{raceId}/laps/{driverId}")
    @Operation(summary = "Giri di un pilota in una gara",
            description = "Giri cronometrati del pilota in gara, in ordine di giro, con posizione e tempo in "
                    + "millisecondi. Lista vuota se il pilota esiste ma non ha giri in quella gara (non ha "
                    + "partecipato o non ha completato il primo giro); 404 se la gara o il pilota non esistono.")
    @ApiResponse(responseCode = "200", description = "Giri del pilota; lista vuota se non ne ha.")
    @BadRequestResponse
    @NotFoundResponse
    public List<LapDto> laps(
            @Parameter(description = "Identificativo della gara.", example = "1098") @PathVariable int raceId,
            @Parameter(description = "Identificativo del pilota.", example = "830") @PathVariable int driverId) {
        if (!races.raceExists(raceId)) {
            throw garaInesistente(raceId);
        }
        if (anagrafiche.findDriver(driverId).isEmpty()) {
            throw new NotFoundException("Pilota %d inesistente".formatted(driverId));
        }
        return races.findLaps(raceId, driverId);
    }

    @GetMapping("/{raceId}/laps")
    @Operation(summary = "Tutti i giri di una gara",
            description = "Giri cronometrati di tutti i piloti della gara in una sola risposta, raggruppati per "
                    + "pilota. I piloti sono nell'ordine d'arrivo della classifica; chi è in classifica senza giri "
                    + "cronometrati compare con una lista vuota. Serve ai grafici dei tempi e delle posizioni.")
    @ApiResponse(responseCode = "200", description = "Giri della gara per pilota.")
    @BadRequestResponse
    @NotFoundResponse
    public List<DriverLapsDto> raceLaps(
            @Parameter(description = "Identificativo della gara.", example = "1098") @PathVariable int raceId) {
        richiediGara(raceId);
        return races.findRaceLaps(raceId);
    }

    @GetMapping("/{raceId}/pit-stops")
    @Operation(summary = "Soste ai box di una gara",
            description = "Soste di tutti i piloti in ordine di giro (a parità di giro, per ora della sosta). "
                    + "Lista vuota se per la gara non ci sono soste registrate (la fonte le riporta dal 2011).")
    @ApiResponse(responseCode = "200", description = "Soste della gara.")
    @BadRequestResponse
    @NotFoundResponse
    public List<PitStopDto> pitStops(
            @Parameter(description = "Identificativo della gara.", example = "1098") @PathVariable int raceId) {
        richiediGara(raceId);
        return races.findPitStops(raceId);
    }

    @GetMapping("/{raceId}/stints")
    @Operation(summary = "Stint di una gara",
            description = "Stint di ogni pilota, cioè i tratti di gara tra due soste: sono derivati dai pit stop, "
                    + "non forniti dalla fonte. compound è sempre null perché la fonte dei dati non contiene le "
                    + "mescole. Piloti nell'ordine d'arrivo, stint in ordine. Lista vuota se la gara non ha soste "
                    + "registrate; un pilota senza giri completati non ha stint.")
    @ApiResponse(responseCode = "200", description = "Stint della gara.")
    @BadRequestResponse
    @NotFoundResponse
    public List<StintDto> stints(
            @Parameter(description = "Identificativo della gara.", example = "1098") @PathVariable int raceId) {
        richiediGara(raceId);
        return races.findStints(raceId);
    }

    @GetMapping("/{raceId}/qualifying")
    @Operation(summary = "Classifica della qualifica",
            description = "Classifica della qualifica in ordine di posizione, con i migliori tempi di Q1, Q2 e Q3 "
                    + "in millisecondi (null per le fasi non disputate). Lista vuota se per la gara non ci sono "
                    + "dati di qualifica.")
    @ApiResponse(responseCode = "200", description = "Classifica della qualifica.")
    @BadRequestResponse
    @NotFoundResponse
    public List<QualifyingResultDto> qualifying(
            @Parameter(description = "Identificativo della gara.", example = "1098") @PathVariable int raceId) {
        richiediGara(raceId);
        return races.findQualifying(raceId);
    }

    private void richiediGara(int raceId) {
        if (!races.raceExists(raceId)) {
            throw garaInesistente(raceId);
        }
    }

    private static NotFoundException garaInesistente(int raceId) {
        return new NotFoundException("Gara %d inesistente".formatted(raceId));
    }
}
