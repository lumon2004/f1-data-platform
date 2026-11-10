package com.f1dataplatform.backend.error;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.boot.web.error.ErrorAttributeOptions;
import org.springframework.boot.web.servlet.error.DefaultErrorAttributes;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.WebRequest;

/**
 * Corpo degli errori che non passano dai controller (richieste rifiutate dal container, filtri):
 * la pagina d'errore predefinita di Spring Boot usa gli stessi campi di {@link ApiError}.
 */
@Component
public class ApiErrorAttributes extends DefaultErrorAttributes {

    @Override
    public Map<String, Object> getErrorAttributes(WebRequest webRequest, ErrorAttributeOptions options) {
        Map<String, Object> predefiniti = super.getErrorAttributes(webRequest, ErrorAttributeOptions.defaults());
        int stato = predefiniti.get("status") instanceof Integer s ? s : 500;

        Map<String, Object> corpo = new LinkedHashMap<>();
        corpo.put("status", stato);
        corpo.put("error", ErrorMessages.nome(stato));
        corpo.put("message", ErrorMessages.generico(stato));
        corpo.put("path", predefiniti.get("path"));
        corpo.put("timestamp", Instant.now().toString());
        return corpo;
    }
}
