package com.f1dataplatform.backend.repository;

import com.f1dataplatform.backend.dto.CircuitDto;
import com.f1dataplatform.backend.dto.DriverDto;
import com.f1dataplatform.backend.dto.TeamDto;
import java.sql.ResultSet;
import java.sql.SQLException;

/** Mappatura delle colonne condivise tra le query: le colonne hanno sempre gli stessi alias. */
final class RowMappers {

    /** Colonne di un pilota, con la tabella {@code drivers} chiamata {@code d}. */
    static final String DRIVER_COLUMNS = """
            d.id AS driver_id, d.code AS driver_code, d.given_name AS driver_given_name,
            d.family_name AS driver_family_name, d.permanent_number AS driver_number,
            d.nationality AS driver_nationality""";

    /** Colonne di una scuderia, con la tabella {@code constructors} chiamata {@code c}. */
    static final String TEAM_COLUMNS = "c.id AS team_id, c.name AS team_name, c.nationality AS team_nationality";

    /** Colonne di un circuito, con la tabella {@code circuits} chiamata {@code ci}. */
    static final String CIRCUIT_COLUMNS = """
            ci.id AS circuit_id, ci.name AS circuit_name, ci.locality AS circuit_locality,
            ci.country AS circuit_country""";

    private RowMappers() {
    }

    static DriverDto driver(ResultSet rs) throws SQLException {
        String nome = rs.getString("driver_given_name");
        String cognome = rs.getString("driver_family_name");
        return new DriverDto(rs.getInt("driver_id"), rs.getString("driver_code"), nome + " " + cognome, nome,
                cognome, intero(rs, "driver_number"), rs.getString("driver_nationality"));
    }

    static TeamDto team(ResultSet rs) throws SQLException {
        return new TeamDto(rs.getInt("team_id"), rs.getString("team_name"), rs.getString("team_nationality"));
    }

    static CircuitDto circuit(ResultSet rs) throws SQLException {
        return new CircuitDto(rs.getInt("circuit_id"), rs.getString("circuit_name"),
                rs.getString("circuit_locality"), rs.getString("circuit_country"));
    }

    /** Intero che può essere NULL ({@code getInt} restituirebbe 0). */
    static Integer intero(ResultSet rs, String colonna) throws SQLException {
        int valore = rs.getInt(colonna);
        return rs.wasNull() ? null : valore;
    }

    /** Decimale che può essere NULL. */
    static Double decimale(ResultSet rs, String colonna) throws SQLException {
        double valore = rs.getDouble(colonna);
        return rs.wasNull() ? null : valore;
    }
}
