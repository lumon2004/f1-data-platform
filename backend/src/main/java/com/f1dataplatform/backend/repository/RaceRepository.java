package com.f1dataplatform.backend.repository;

import com.f1dataplatform.backend.dto.FastestLapDto;
import com.f1dataplatform.backend.dto.LapDto;
import com.f1dataplatform.backend.dto.RaceDto;
import com.f1dataplatform.backend.dto.RaceSummaryDto;
import com.f1dataplatform.backend.dto.ResultDto;
import com.f1dataplatform.backend.dto.SeasonDto;
import com.f1dataplatform.backend.dto.SessionDto;
import com.f1dataplatform.backend.dto.WinnerDto;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Calendario, dettaglio delle gare, classifiche e giri. */
@Repository
public class RaceRepository {

    private final JdbcClient jdbc;

    public RaceRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /** Stagioni con almeno una gara, dalla più recente. */
    public List<SeasonDto> findSeasons() {
        return jdbc.sql("""
                        SELECT r.season_year AS year,
                               count(*) AS races,
                               count(*) FILTER (WHERE EXISTS (
                                   SELECT 1 FROM sessions sp
                                   WHERE sp.race_id = r.id AND sp.session_type = 'sprint')) AS sprints,
                               min(s.session_date) AS first_race_date,
                               max(s.session_date) AS last_race_date
                        FROM races r
                        JOIN sessions s ON s.race_id = r.id AND s.session_type = 'race'
                        GROUP BY r.season_year
                        ORDER BY r.season_year DESC
                        """)
                .query((rs, n) -> new SeasonDto(rs.getInt("year"), rs.getInt("races"), rs.getInt("sprints"),
                        rs.getObject("first_race_date", LocalDate.class),
                        rs.getObject("last_race_date", LocalDate.class)))
                .list();
    }

    /** Gare di una stagione in ordine di round, con circuito e vincitore. */
    public List<RaceSummaryDto> findRacesBySeason(int year) {
        return jdbc.sql("""
                        SELECT r.id, r.season_year, r.round, r.name, s.session_date,
                               %s,
                               EXISTS (SELECT 1 FROM sessions sp
                                       WHERE sp.race_id = r.id AND sp.session_type = 'sprint') AS has_sprint,
                               w.*
                        FROM races r
                        JOIN sessions s ON s.race_id = r.id AND s.session_type = 'race'
                        JOIN circuits ci ON ci.id = r.circuit_id
                        LEFT JOIN LATERAL (
                            SELECT %s, %s
                            FROM results res
                            JOIN drivers d ON d.id = res.driver_id
                            JOIN constructors c ON c.id = res.constructor_id
                            WHERE res.race_id = r.id AND res.session_type = 'race' AND res.position = 1
                            ORDER BY res.position_order, res.id
                            LIMIT 1
                        ) w ON true
                        WHERE r.season_year = :year
                        ORDER BY r.round
                        """.formatted(RowMappers.CIRCUIT_COLUMNS, RowMappers.DRIVER_COLUMNS, RowMappers.TEAM_COLUMNS))
                .param("year", year)
                .query(RaceRepository::raceSummary)
                .list();
    }

    private static RaceSummaryDto raceSummary(ResultSet rs, int n) throws SQLException {
        rs.getInt("driver_id");
        WinnerDto vincitore = rs.wasNull() ? null : new WinnerDto(RowMappers.driver(rs), RowMappers.team(rs));
        return new RaceSummaryDto(rs.getInt("id"), rs.getInt("season_year"), rs.getInt("round"),
                rs.getString("name"), rs.getObject("session_date", LocalDate.class), RowMappers.circuit(rs),
                rs.getBoolean("has_sprint"), vincitore);
    }

    public boolean raceExists(int raceId) {
        return jdbc.sql("SELECT EXISTS (SELECT 1 FROM races WHERE id = :id)")
                .param("id", raceId).query(Boolean.class).single();
    }

    public boolean sessionExists(int raceId, String sessionType) {
        return jdbc.sql("SELECT EXISTS (SELECT 1 FROM sessions WHERE race_id = :id AND session_type = :type)")
                .param("id", raceId).param("type", sessionType).query(Boolean.class).single();
    }

    /** Dettaglio di una gara con le sessioni del weekend. */
    public Optional<RaceDto> findRace(int raceId) {
        List<SessionDto> sessioni = jdbc.sql("""
                        SELECT s.session_type, s.session_date, s.start_time_utc,
                               EXISTS (SELECT 1 FROM results x
                                       WHERE x.race_id = s.race_id AND x.session_type = s.session_type) AS has_results,
                               EXISTS (SELECT 1 FROM laps x
                                       WHERE x.race_id = s.race_id AND x.session_type = s.session_type) AS has_laps
                        FROM sessions s
                        WHERE s.race_id = :id
                        ORDER BY array_position(
                                     ARRAY['fp1', 'fp2', 'fp3', 'qualifying', 'sprint', 'race'], s.session_type)
                        """)
                .param("id", raceId)
                .query((rs, n) -> new SessionDto(rs.getString("session_type"),
                        rs.getObject("session_date", LocalDate.class),
                        rs.getObject("start_time_utc", LocalTime.class),
                        rs.getBoolean("has_results"), rs.getBoolean("has_laps")))
                .list();

        return jdbc.sql("""
                        SELECT r.id, r.season_year, r.round, r.name, r.wikipedia_url,
                               s.session_date, s.start_time_utc,
                               %s
                        FROM races r
                        JOIN sessions s ON s.race_id = r.id AND s.session_type = 'race'
                        JOIN circuits ci ON ci.id = r.circuit_id
                        WHERE r.id = :id
                        """.formatted(RowMappers.CIRCUIT_COLUMNS))
                .param("id", raceId)
                .query((rs, n) -> new RaceDto(rs.getInt("id"), rs.getInt("season_year"), rs.getInt("round"),
                        rs.getString("name"), rs.getObject("session_date", LocalDate.class),
                        rs.getObject("start_time_utc", LocalTime.class), rs.getString("wikipedia_url"),
                        RowMappers.circuit(rs),
                        sessioni.stream().anyMatch(x -> x.type().equals("sprint")), sessioni))
                .optional();
    }

    /** Classifica di una sessione ({@code race} o {@code sprint}) in ordine di arrivo. */
    public List<ResultDto> findResults(int raceId, String sessionType) {
        return jdbc.sql("""
                        SELECT res.position, res.position_order, res.points, st.name AS status, res.outcome,
                               res.laps_completed, res.grid_position, res.car_number, res.time_ms,
                               res.time_ms - min(res.time_ms) OVER () AS gap_ms,
                               res.fastest_lap_number, res.fastest_lap_rank, res.fastest_lap_time_ms,
                               res.fastest_lap_speed_kph,
                               %s, %s
                        FROM results res
                        JOIN drivers d ON d.id = res.driver_id
                        JOIN constructors c ON c.id = res.constructor_id
                        JOIN statuses st ON st.id = res.status_id
                        WHERE res.race_id = :raceId AND res.session_type = :sessionType
                        ORDER BY res.position_order, res.id
                        """.formatted(RowMappers.DRIVER_COLUMNS, RowMappers.TEAM_COLUMNS))
                .param("raceId", raceId)
                .param("sessionType", sessionType)
                .query(RaceRepository::result)
                .list();
    }

    private static ResultDto result(ResultSet rs, int n) throws SQLException {
        Integer giro = RowMappers.intero(rs, "fastest_lap_number");
        Integer rango = RowMappers.intero(rs, "fastest_lap_rank");
        Integer tempo = RowMappers.intero(rs, "fastest_lap_time_ms");
        Double velocita = RowMappers.decimale(rs, "fastest_lap_speed_kph");
        FastestLapDto giroVeloce = giro == null && rango == null && tempo == null && velocita == null
                ? null : new FastestLapDto(giro, rango, tempo, velocita);
        return new ResultDto(RowMappers.intero(rs, "position"), rs.getInt("position_order"),
                rs.getDouble("points"), rs.getString("status"), rs.getString("outcome"),
                rs.getInt("laps_completed"), RowMappers.intero(rs, "grid_position"),
                RowMappers.intero(rs, "car_number"), RowMappers.intero(rs, "time_ms"),
                RowMappers.intero(rs, "gap_ms"), giroVeloce, RowMappers.driver(rs), RowMappers.team(rs));
    }

    /** Giri di un pilota nella gara, in ordine di giro. */
    public List<LapDto> findLaps(int raceId, int driverId) {
        return jdbc.sql("""
                        SELECT lap_number, position, time_ms
                        FROM laps
                        WHERE race_id = :raceId AND session_type = 'race' AND driver_id = :driverId
                        ORDER BY lap_number
                        """)
                .param("raceId", raceId)
                .param("driverId", driverId)
                .query((rs, n) -> new LapDto(rs.getInt("lap_number"), RowMappers.intero(rs, "position"),
                        rs.getInt("time_ms")))
                .list();
    }
}
