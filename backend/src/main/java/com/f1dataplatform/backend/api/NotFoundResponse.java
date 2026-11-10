package com.f1dataplatform.backend.api;

import com.f1dataplatform.backend.error.ApiError;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/** Documenta la risposta 404 di un'operazione. */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@ApiResponse(responseCode = "404", description = "Risorsa inesistente.",
        content = @Content(mediaType = "application/json", schema = @Schema(implementation = ApiError.class)))
@interface NotFoundResponse {
}
