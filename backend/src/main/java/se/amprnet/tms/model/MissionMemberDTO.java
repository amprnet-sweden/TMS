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

package se.amprnet.tms.model;

import org.apache.commons.lang3.StringUtils;

public record MissionMemberDTO(String id, String firstName, String lastName, String email, String role) {
    public String getName() {
        final StringBuilder sb = new StringBuilder();
        if (firstName != null) {
            sb.append(firstName);
        }
        if (lastName != null) {
            if (!sb.isEmpty()) {
                sb.append(" ");
            }
            sb.append(lastName);
        }
        return sb.toString();
    }

    public String getInitials() {
        final StringBuilder s = new StringBuilder();
        if (StringUtils.isNotEmpty(firstName())) {
            s.append(firstName().substring(0, 1).toUpperCase());
        }
        if (StringUtils.isNotEmpty(lastName())) {
            s.append(lastName().substring(0, 1).toUpperCase());
        }
        return s.toString();
    }
}
