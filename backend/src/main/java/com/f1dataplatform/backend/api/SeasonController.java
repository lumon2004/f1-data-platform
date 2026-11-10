package com.f1dataplatform.backend.api;

import com.f1dataplatform.backend.dto.RaceSummaryDto;
import com.f1dataplatform.backend.dto.SeasonDto;
import com.f1dataplatform.backend.error.NotFoundException;
import com.f1dataplatform.backend.repository.RaceRepository;
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

    private final RaceRepository races;

    public SeasonController(RaceRepository races) {
        this.races = races;
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
}
