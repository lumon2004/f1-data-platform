package com.f1dataplatform.backend.error;

import org.springframework.http.HttpStatus;

/** Testi degli errori che non nascono da una regola dell'API: uno per codice di stato, mai dall'eccezione. */
final class ErrorMessages {

    private ErrorMessages() {
    }

    static String nome(int stato) {
        HttpStatus noto = HttpStatus.resolve(stato);
        return noto != null ? noto.getReasonPhrase() : "Error";
    }

    static String generico(int stato) {
        return switch (stato) {
            case 400 -> "Richiesta non valida";
            case 404 -> "Risorsa inesistente";
            case 405 -> "Metodo non consentito per questo percorso";
            case 406 -> "Formato di risposta non disponibile";
            case 414 -> "Indirizzo della richiesta troppo lungo";
            case 415 -> "Formato della richiesta non supportato";
            case 431 -> "Intestazioni della richiesta troppo grandi";
            case 503 -> "Database non disponibile, riprova tra poco";
            default -> stato >= 500 ? "Errore interno del server" : "Richiesta non accettata";
        };
    }
}
