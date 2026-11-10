package com.f1dataplatform.backend.error;

/** La risorsa richiesta non esiste: diventa una risposta 404. */
public class NotFoundException extends RuntimeException {

    public NotFoundException(String message) {
        super(message);
    }
}
