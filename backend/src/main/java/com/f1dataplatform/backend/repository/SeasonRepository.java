package com.f1dataplatform.backend.repository;

import com.f1dataplatform.backend.dto.DriverDto;
import com.f1dataplatform.backend.dto.DriverStandingDto;
import com.f1dataplatform.backend.dto.SeasonDriverDto;
import com.f1dataplatform.backend.dto.TeamDto;
import com.f1dataplatform.backend.dto.TeamStandingDto;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Piloti, scuderie e classifiche di campionato di una stagione. */
@Repository
public class SeasonRepository {

    /**
     * Classifica di campionato, comune a piloti e scuderie ({@code %1$s} = colonna di {@code results},
     * costante del codice).
     *
     * <ul>
     *   <li>punti = gare + sprint; vittorie e podi solo dalle gare;</li>
     *   <li>entra in classifica chi ha almeno un risultato di gara nella stagione;</li>
     *   <li>a parità di punti decide il confronto dei piazzamenti in gara, come nel regolamento: più
     *       vittorie, poi più secondi posti, e così via ({@code counts} è il vettore dei piazzamenti per
     *       posizione, e i vettori si confrontano elemento per elemento).</li>
     * </ul>
     */
    private static final String STANDINGS_CTE = """
            WITH season_results AS (
                SELECT res.%1$s AS entity_id, res.race_id, res.session_type, res.position, res.points
                FROM results res
                JOIN races r ON r.id = res.race_id
                WHERE r.season_year = :year AND res.session_type IN ('race', 'sprint')
            ), totals AS (
                SELECT entity_id,
                       coalesce(sum(points), 0)                                           AS points,
                       coalesce(sum(points) FILTER (WHERE session_type = 'race'), 0)      AS race_points,
                       coalesce(sum(points) FILTER (WHERE session_type = 'sprint'), 0)    AS sprint_points,
                       count(DISTINCT race_id)
                           FILTER (WHERE session_type = 'race' AND position = 1)          AS wins,
                       count(DISTINCT (race_id, position))
                           FILTER (WHERE session_type = 'race' AND position <= 3)         AS podiums
                FROM season_results
                GROUP BY entity_id
                HAVING count(*) FILTER (WHERE session_type = 'race') > 0
            ), placements AS (
                SELECT entity_id, position, count(*) AS n
                FROM season_results
                WHERE session_type = 'race' AND position IS NOT NULL
                GROUP BY entity_id, position
            ), countback AS (
                SELECT t.entity_id, array_agg(coalesce(p.n, 0) ORDER BY g.pos) AS counts
                FROM totals t
                CROSS JOIN generate_series(1, (SELECT coalesce(max(position), 1) FROM placements)) AS g(pos)
                LEFT JOIN placements p ON p.entity_id = t.entity_id AND p.position = g.pos
                GROUP BY t.entity_id
            ), standings AS (
                SELECT row_number() OVER (ORDER BY t.points DESC, cb.counts DESC, t.entity_id) AS standing,
                       t.*
                FROM totals t
                JOIN countback cb ON cb.entity_id = t.entity_id
            )
            """;

    private final JdbcClient jdbc;

    public SeasonRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /** Vero se la stagione ha almeno una gara. */
    public boolean seasonHasRaces(int year) {
        return jdbc.sql("SELECT EXISTS (SELECT 1 FROM races WHERE season_year = :year)")
                .param("year", year).query(Boolean.class).single();
    }

    /** Piloti con almeno un risultato di gara nella stagione, per cognome, con le loro scuderie. */
    public List<SeasonDriverDto> findDrivers(int year) {
        record Riga(DriverDto driver, TeamDto team, boolean latest) {
        }

        List<Riga> righe = jdbc.sql("""
                        WITH entries AS (
                            SELECT res.driver_id, res.constructor_id,
                                   min(r.round) AS first_round, max(r.round) AS last_round
                            FROM results res
                            JOIN races r ON r.id = res.race_id
                            WHERE r.season_year = :year AND res.session_type = 'race'
                            GROUP BY res.driver_id, res.constructor_id
                        )
                        SELECT %s, %s,
                               e.last_round = max(e.last_round) OVER (PARTITION BY e.driver_id) AS latest
                        FROM entries e
                        JOIN drivers d ON d.id = e.driver_id
                        JOIN constructors c ON c.id = e.constructor_id
                        ORDER BY d.family_name, d.given_name, d.id, e.first_round, c.id
                        """.formatted(RowMappers.DRIVER_COLUMNS, RowMappers.TEAM_COLUMNS))
                .param("year", year)
                .query((rs, n) -> new Riga(RowMappers.driver(rs), RowMappers.team(rs), rs.getBoolean("latest")))
                .list();

        // Una riga per coppia pilota-scuderia, già in ordine: si raggruppa per pilota.
        Map<Integer, List<Riga>> perPilota = new LinkedHashMap<>();
        righe.forEach(r -> perPilota.computeIfAbsent(r.driver().id(), k -> new ArrayList<>()).add(r));
        return perPilota.values().stream().map(gruppo -> {
            DriverDto d = gruppo.get(0).driver();
            TeamDto recente = gruppo.stream().filter(Riga::latest).map(Riga::team).reduce((a, b) -> b)
                    .orElse(gruppo.get(gruppo.size() - 1).team());
            return new SeasonDriverDto(d.id(), d.code(), d.name(), d.givenName(), d.familyName(), d.number(),
                    d.nationality(), recente, gruppo.stream().map(Riga::team).toList());
        }).toList();
    }

    /** Scuderie con almeno un risultato di gara nella stagione, per nome. */
    public List<TeamDto> findTeams(int year) {
        return jdbc.sql("""
                        SELECT %s
                        FROM constructors c
                        WHERE EXISTS (SELECT 1
                                      FROM results res
                                      JOIN races r ON r.id = res.race_id
                                      WHERE res.constructor_id = c.id AND res.session_type = 'race'
                                        AND r.season_year = :year)
                        ORDER BY c.name, c.id
                        """.formatted(RowMappers.TEAM_COLUMNS))
                .param("year", year)
                .query((rs, n) -> RowMappers.team(rs))
                .list();
    }

    public List<DriverStandingDto> driverStandings(int year) {
        return jdbc.sql(STANDINGS_CTE.formatted("driver_id") + """
                        SELECT s.standing, s.points, s.race_points, s.sprint_points, s.wins, s.podiums,
                               %s, t.*
                        FROM standings s
                        JOIN drivers d ON d.id = s.entity_id
                        CROSS JOIN LATERAL (
                            SELECT %s
                            FROM results res
                            JOIN races r ON r.id = res.race_id
                            JOIN constructors c ON c.id = res.constructor_id
                            WHERE res.driver_id = s.entity_id AND res.session_type = 'race'
                              AND r.season_year = :year
                            ORDER BY r.round DESC, res.position_order, res.id
                            LIMIT 1
                        ) t
                        ORDER BY s.standing
                        """.formatted(RowMappers.DRIVER_COLUMNS, RowMappers.TEAM_COLUMNS))
                .param("year", year)
                .query((rs, n) -> new DriverStandingDto(rs.getInt("standing"), RowMappers.driver(rs),
                        RowMappers.team(rs), rs.getDouble("points"), rs.getDouble("race_points"),
                        rs.getDouble("sprint_points"), rs.getInt("wins"), rs.getInt("podiums")))
                .list();
    }

    public List<TeamStandingDto> teamStandings(int year) {
        return jdbc.sql(STANDINGS_CTE.formatted("constructor_id") + """
                        SELECT s.standing, s.points, s.race_points, s.sprint_points, s.wins, s.podiums, %s
                        FROM standings s
                        JOIN constructors c ON c.id = s.entity_id
                        ORDER BY s.standing
                        """.formatted(RowMappers.TEAM_COLUMNS))
                .param("year", year)
                .query((rs, n) -> new TeamStandingDto(rs.getInt("standing"), RowMappers.team(rs),
                        rs.getDouble("points"), rs.getDouble("race_points"), rs.getDouble("sprint_points"),
                        rs.getInt("wins"), rs.getInt("podiums")))
                .list();
    }
}
