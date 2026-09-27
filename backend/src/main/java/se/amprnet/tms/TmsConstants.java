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

package se.amprnet.tms;

public final class TmsConstants {
    private TmsConstants() {
    }

    public static final String SUPERUSER_ROLE = "tms-superuser";
    public static final String OPERATOR_ROLE = "tms-operator";
    //public static final String RESOURCE_ACCESS_NAME = "tms-backend";
    public static final String TMS_MISSION_HEADER = "x-tms-mission";
}
