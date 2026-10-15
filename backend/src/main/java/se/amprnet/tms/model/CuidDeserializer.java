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

import io.github.thibaultmeyer.cuid.CUID;
import tools.jackson.core.JsonParser;
import tools.jackson.core.JsonToken;
import tools.jackson.databind.DeserializationContext;
import tools.jackson.databind.deser.std.StdScalarDeserializer;

public class CuidDeserializer extends StdScalarDeserializer<CUID> {

    public CuidDeserializer() {
        super(CUID.class);
    }

    @Override
    public CUID deserialize(JsonParser p, DeserializationContext ctx) {
        if (!p.hasToken(JsonToken.VALUE_STRING)) {
            return (CUID) ctx.handleUnexpectedToken(CUID.class, p);
        }
        String text = p.getString();
        try {
            return CUID.fromString(text);
        } catch (IllegalArgumentException e) {
            return (CUID) ctx.handleWeirdStringValue(CUID.class, text, e.getMessage());
        }
    }
}
