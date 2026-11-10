package com.f1dataplatform.backend;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Lettura dei CSV del dataset di esempio, per confrontare l'API con la fonte. */
final class SampleCsv {

    private SampleCsv() {
    }

    /** Righe del file come mappe intestazione → valore. */
    static List<Map<String, String>> read(Path file) {
        List<String> righe;
        try {
            righe = Files.readAllLines(file, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        List<String> intestazione = campi(righe.get(0));
        List<Map<String, String>> record = new ArrayList<>();
        for (String riga : righe.subList(1, righe.size())) {
            if (riga.isBlank()) {
                continue;
            }
            List<String> valori = campi(riga);
            Map<String, String> r = new LinkedHashMap<>();
            for (int i = 0; i < intestazione.size(); i++) {
                r.put(intestazione.get(i), valori.get(i));
            }
            record.add(r);
        }
        return record;
    }

    /** Campi di una riga CSV, con virgolette doppie e virgole dentro i campi tra virgolette. */
    private static List<String> campi(String riga) {
        List<String> campi = new ArrayList<>();
        StringBuilder corrente = new StringBuilder();
        boolean traVirgolette = false;
        for (int i = 0; i < riga.length(); i++) {
            char c = riga.charAt(i);
            if (traVirgolette) {
                if (c == '"' && i + 1 < riga.length() && riga.charAt(i + 1) == '"') {
                    corrente.append('"');
                    i++;
                } else if (c == '"') {
                    traVirgolette = false;
                } else {
                    corrente.append(c);
                }
            } else if (c == '"') {
                traVirgolette = true;
            } else if (c == ',') {
                campi.add(corrente.toString());
                corrente.setLength(0);
            } else {
                corrente.append(c);
            }
        }
        campi.add(corrente.toString());
        return campi;
    }
}
