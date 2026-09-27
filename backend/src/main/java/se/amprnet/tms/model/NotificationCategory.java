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

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum NotificationCategory {
    /**
     * A command is used when the recipient is a machine, not a human.
     * Intended to be consumed by some application logic.
     */
    COMMAND("command"),

    /**
     * Event sent when record was created.
     */
    CREATED("created"),

    /**
     * Event sent when record was updated.
     */
    UPDATED("updated"),

    /**
     * Event sent when record was deleted.
     */
    DELETED("deleted"),

    /**
     * A notice is a short-lived notification, for example "Your export is ready to download".
     * Intended to be consumed and dismissed within the current user session
     */
    NOTICE("notice"),

    /**
     * A message is a notification that typically stays visible in the user's inbox until its handled.
     */
    MESSAGE("message");

    private final String text;

    @JsonCreator
    private NotificationCategory(final String text) {
        this.text = text.toUpperCase();
    }

    @Override
    @JsonValue
    public String toString() {
        return text;
    }
}
