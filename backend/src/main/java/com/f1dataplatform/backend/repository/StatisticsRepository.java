package com.f1dataplatform.backend.repository;

import com.f1dataplatform.backend.dto.DriverDto;
import com.f1dataplatform.backend.dto.StatisticsValues;
import com.f1dataplatform.backend.dto.TeamDto;
import java.sql.Types;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Anagrafica e statistiche aggregate di piloti e scuderie: tutti i calcoli avvengono in SQL. */
@Repository
public class StatisticsRepository {

    /**
     * Stessa query per pilota e scuderia: cambia solo la colonna di {@code results} su cui si filtra
     * (il segnaposto {@code %1$s} riceve una costante del codice, mai un valore della richiesta).
     *
     * <ul>
     *   <li>{@code gp}: le sole righe di gara ({@code session_type = 'race'}); le sprint non entrano
     *       in nessun conteggio;</li>
     *   <li>le gare si contano con {@code count(DISTINCT race_id)}: una scuderia ha più righe per gara,
     *       e nelle stagioni storiche può averle anche un pilota (vetture condivise);</li>
     *   <li>podi = piazzamenti: {@code count(DISTINCT (race_id, position))}, due vetture della stessa
     *       scuderia sul podio valgono due;</li>
     *   <li>i punti delle sprint sono sommati a parte.</li>
     * </ul>
     */
    private static final String STATISTICS_SQL = """
            WITH gp AS (
                SELECT res.race_id, res.position, res.grid_position, res.points, res.outcome,
                       res.fastest_lap_rank
                FROM results res
                JOIN races r ON r.id = res.race_id
                WHERE res.%1$s = :id
                  AND res.session_type = 'race'
                  AND (CAST(:season AS integer) IS NULL OR r.season_year = CAST(:season AS integer))
            ), sprint AS (
                SELECT coalesce(sum(res.points), 0) AS points
                FROM results res
                JOIN races r ON r.id = res.race_id
                WHERE res.%1$s = :id
                  AND res.session_type = 'sprint'
                  AND (CAST(:season AS integer) IS NULL OR r.season_year = CAST(:season AS integer))
            )
            SELECT count(DISTINCT race_id)                                          AS races,
                   count(DISTINCT race_id)
                       FILTER (WHERE outcome NOT IN ('withdrawn', 'failed_to_qualify')) AS starts,
                   count(DISTINCT race_id) FILTER (WHERE position = 1)              AS wins,
                   count(DISTINCT (race_id, position)) FILTER (WHERE position <= 3) AS podiums,
                   coalesce(sum(points), 0)                                         AS points,
                   (SELECT points FROM sprint)                                      AS sprint_points,
                   count(DISTINCT race_id) FILTER (WHERE grid_position = 1)         AS poles,
                   count(DISTINCT race_id) FILTER (WHERE fastest_lap_rank = 1)      AS fastest_laps,
                   count(*) FILTER (WHERE outcome = 'retired')                      AS retirements,
                   min(position)                                                    AS best_finish,
                   round(avg(position), 2)                                          AS average_finish,
                   round(avg(grid_position), 2)                                     AS average_grid
            FROM gp
            """;

    private final JdbcClient jdbc;

    public StatisticsRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public Optional<DriverDto> findDriver(int driverId) {
        return jdbc.sql("SELECT " + RowMappers.DRIVER_COLUMNS + " FROM drivers d WHERE d.id = :id")
                .param("id", driverId)
                .query((rs, n) -> RowMappers.driver(rs))
                .optional();
    }

    public Optional<TeamDto> findTeam(int teamId) {
        return jdbc.sql("SELECT " + RowMappers.TEAM_COLUMNS + " FROM constructors c WHERE c.id = :id")
                .param("id", teamId)
                .query((rs, n) -> RowMappers.team(rs))
                .optional();
    }

    public StatisticsValues driverStatistics(int driverId, Integer season) {
        return statistics("driver_id", driverId, season);
    }

    public StatisticsValues teamStatistics(int teamId, Integer season) {
        return statistics("constructor_id", teamId, season);
    }

    private StatisticsValues statistics(String colonna, int id, Integer season) {
        return jdbc.sql(STATISTICS_SQL.formatted(colonna))
                .param("id", id)
                .param("season", season, Types.INTEGER)
                .query((rs, n) -> new StatisticsValues(rs.getInt("races"), rs.getInt("starts"), rs.getInt("wins"),
                        rs.getInt("podiums"), rs.getDouble("points"), rs.getDouble("sprint_points"),
                        rs.getInt("poles"), rs.getInt("fastest_laps"), rs.getInt("retirements"),
                        RowMappers.intero(rs, "best_finish"), RowMappers.decimale(rs, "average_finish"),
                        RowMappers.decimale(rs, "average_grid")))
                .single();
    }
}
