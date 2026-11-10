package com.f1dataplatform.backend.config;

import com.f1dataplatform.backend.error.ApiError;
import io.swagger.v3.core.converter.ModelConverters;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.media.Content;
import io.swagger.v3.oas.models.media.MediaType;
import io.swagger.v3.oas.models.media.Schema;
import io.swagger.v3.oas.models.responses.ApiResponse;
import org.springdoc.core.customizers.OpenApiCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/** Intestazione della documentazione OpenAPI e risposta 500 comune a tutte le operazioni dell'API. */
@Configuration
public class OpenApiConfig {

    @Bean
    OpenAPI f1DataPlatformOpenApi() {
        return new OpenAPI().info(new Info()
                .title("F1 Data Platform API")
                .version("v1")
                .description("""
                        API di sola lettura sui dati storici di Formula 1 caricati dalla pipeline: stagioni, \
                        calendario, classifiche, giri e statistiche di piloti e scuderie.

                        Convenzioni: campi in camelCase; tempi e durate in millisecondi interi; date ISO 8601; \
                        gli identificativi sono quelli restituiti dall'API stessa. Ogni errore ha lo stesso corpo \
                        JSON (ApiError): 400 per parametri non validi, 404 per risorse o percorsi inesistenti, \
                        500 senza dettagli interni.

                        Fonte dei dati: dataset Kaggle "Formula 1 World Championship (1950 - 2024)" di Rohan Rao, \
                        derivato da Ergast. Progetto non ufficiale, non affiliato a Formula 1, FIA o alle scuderie."""));
    }

    /** Aggiunge a ogni operazione sotto /api la risposta 500 con lo schema d'errore comune. */
    @Bean
    OpenApiCustomizer erroreInternoPerOgniOperazione() {
        return openApi -> {
            ModelConverters.getInstance().read(ApiError.class).forEach(openApi.getComponents()::addSchemas);
            if (openApi.getPaths() == null) {
                return;
            }
            openApi.getPaths().forEach((percorso, voce) -> {
                if (percorso.startsWith("/api/")) {
                    voce.readOperations().forEach(operazione -> operazione.getResponses().addApiResponse("500",
                            new ApiResponse().description("Errore interno, senza dettagli.")
                                    .content(new Content().addMediaType("application/json", new MediaType()
                                            .schema(new Schema<>().$ref("#/components/schemas/ApiError"))))));
                }
            });
        };
    }
}
