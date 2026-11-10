package com.f1dataplatform.backend.error;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.io.Writer;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;
import org.apache.catalina.connector.Request;
import org.apache.catalina.connector.Response;
import org.apache.catalina.valves.ErrorReportValve;
import org.apache.coyote.ActionCode;

/**
 * Corpo JSON per gli errori che Tomcat decide da solo, prima che la richiesta arrivi a Spring:
 * percorsi con caratteri non ammessi o codifiche vietate ({@code %00}, {@code %2F}, {@code [..]}),
 * richieste troppo lunghe o malformate. Senza questa valvola Tomcat risponderebbe con la sua pagina
 * HTML; così ogni errore dell'applicazione ha gli stessi campi di {@link ApiError}.
 */
public class JsonErrorReportValve extends ErrorReportValve {

    private static final ObjectMapper JSON = new ObjectMapper();

    public JsonErrorReportValve() {
        setShowReport(false);
        setShowServerInfo(false);
    }

    @Override
    protected void report(Request request, Response response, Throwable throwable) {
        int stato = response.getStatus();
        // Stesse condizioni della valvola predefinita: solo errori senza corpo già scritto, una volta sola.
        if (stato < 400 || response.getContentWritten() > 0 || !response.setErrorReported()) {
            return;
        }
        AtomicBoolean scritturaPossibile = new AtomicBoolean(false);
        response.getCoyoteResponse().action(ActionCode.IS_IO_ALLOWED, scritturaPossibile);
        if (!scritturaPossibile.get()) {
            return;
        }

        Map<String, Object> corpo = new LinkedHashMap<>();
        corpo.put("status", stato);
        corpo.put("error", ErrorMessages.nome(stato));
        corpo.put("message", ErrorMessages.generico(stato));
        corpo.put("path", percorso(request));
        corpo.put("timestamp", Instant.now().toString());
        try {
            response.setContentType("application/json");
            response.setCharacterEncoding("UTF-8");
            Writer writer = response.getReporter();
            if (writer != null) {
                writer.write(JSON.writeValueAsString(corpo));
                response.finishResponse();
            }
        } catch (IOException | IllegalStateException e) {
            // La connessione è già compromessa: non c'è altro da scrivere.
        }
    }

    /** Percorso richiesto, se Tomcat è riuscito a leggerlo; altrimenti null. */
    private static String percorso(Request request) {
        try {
            return request.getRequestURI();
        } catch (RuntimeException e) {
            return null;
        }
    }
}
