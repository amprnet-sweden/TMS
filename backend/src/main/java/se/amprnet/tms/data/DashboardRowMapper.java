/*
 * Copyright (C) 2026 AMPRnet Sverige
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 *  GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <https://www.gnu.org/licenses/>.
 */

package se.amprnet.tms.data;

import io.github.thibaultmeyer.cuid.CUID;
import org.springframework.jdbc.core.RowMapper;

import java.sql.ResultSet;
import java.sql.SQLException;

public class DashboardRowMapper implements RowMapper<DashboardData> {
    @Override
    public DashboardData mapRow(ResultSet rs, int rowNum) throws SQLException {
        return new DashboardData(CUID.fromString(rs.getString("service_id")), CUID.fromString(rs.getString("status_id")), CUID.fromString(rs.getString("priority_id")), rs.getLong("n"));
    }
}
