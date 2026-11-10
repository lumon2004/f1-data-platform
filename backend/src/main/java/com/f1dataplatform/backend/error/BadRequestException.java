package com.f1dataplatform.backend.error;

/** Un parametro della richiesta non è valido: diventa una risposta 400. */
public class BadRequestException extends RuntimeException {

    public BadRequestException(String message) {
        super(message);
    }
}
