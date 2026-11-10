package com.f1dataplatform.backend.config;

import com.f1dataplatform.backend.error.ApiError;
import io.swagger.v3.core.converter.ModelConverters;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.media.Content;
import io.swagger.v3.oas.models.media.MediaType;
import io.swagger.v3.oas.models.media.Schema;
import io.swagger.v3.oas.models.responses.ApiResponse;
import java.util.List;
import java.util.Map;
import org.springdoc.core.customizers.OpenApiCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;

/** Intestazione della documentazione OpenAPI, errori comuni a tutte le operazioni e campi obbligatori. */
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
                        gli identificativi sono quelli restituiti dall'API stessa. Negli schemi i campi \
                        elencati in required sono sempre presenti e mai null; gli altri possono valere null.

                        Ogni errore ha lo stesso corpo JSON (ApiError): 400 per parametri o indirizzi non validi \
                        (compresi quelli che il server respinge prima di interpretarli), 404 per risorse o \
                        percorsi inesistenti, 503 se il database non è raggiungibile, 500 senza dettagli interni.

                        Fonte dei dati: dataset Kaggle "Formula 1 World Championship (1950 - 2024)" di Rohan Rao, \
                        derivato da Ergast. Progetto non ufficiale, non affiliato a Formula 1, FIA o alle scuderie."""));
    }

    /** Aggiunge a ogni operazione sotto /api le risposte 500 e 503 con lo schema d'errore comune. */
    @Bean
    @Order(0)
    OpenApiCustomizer erroriDelServerPerOgniOperazione() {
        return openApi -> {
            ModelConverters.getInstance(true).read(ApiError.class).forEach(openApi.getComponents()::addSchemas);
            if (openApi.getPaths() == null) {
                return;
            }
            openApi.getPaths().forEach((percorso, voce) -> {
                if (percorso.startsWith("/api/")) {
                    voce.readOperations().forEach(operazione -> {
                        operazione.getResponses().addApiResponse("500", errore("Errore interno, senza dettagli."));
                        operazione.getResponses().addApiResponse("503", errore("Database non raggiungibile."));
                    });
                }
            });
        };
    }

    private static ApiResponse errore(String descrizione) {
        return new ApiResponse().description(descrizione)
                .content(new Content().addMediaType("application/json", new MediaType()
                        .schema(new Schema<>().$ref("#/components/schemas/ApiError"))));
    }

    /**
     * Dichiara {@code required} ogni proprietà che non è marcata nullable: i DTO sono record serializzati
     * per intero, quindi un campo è sempre presente, e quelli che possono valere null sono tutti annotati
     * come tali. Gira dopo il personalizzatore che registra ApiError.
     */
    @Bean
    @Order(Ordered.LOWEST_PRECEDENCE)
    OpenApiCustomizer campiObbligatori() {
        return openApi -> openApi.getComponents().getSchemas().values().forEach(schema -> {
            Map<String, Schema<?>> proprieta = proprietaDi(schema);
            if (proprieta == null) {
                return;
            }
            List<String> obbligatori = proprieta.entrySet().stream()
                    .filter(p -> !ammetteNull(p.getValue()))
                    .map(Map.Entry::getKey)
                    .toList();
            schema.setRequired(obbligatori.isEmpty() ? null : obbligatori);
        });
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    private static Map<String, Schema<?>> proprietaDi(Schema schema) {
        return schema.getProperties();
    }

    /** Nullable in OpenAPI 3.0 ({@code nullable: true}) o 3.1 ({@code "null"} tra i tipi). */
    private static boolean ammetteNull(Schema<?> proprieta) {
        return Boolean.TRUE.equals(proprieta.getNullable())
                || (proprieta.getTypes() != null && proprieta.getTypes().contains("null"));
    }
}
