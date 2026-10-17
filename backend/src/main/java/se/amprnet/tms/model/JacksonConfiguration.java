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
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import tools.jackson.databind.JacksonModule;
import tools.jackson.databind.module.SimpleModule;

@Configuration
public class JacksonConfiguration {

    @Bean
    public JacksonModule cuidModule() {
        SimpleModule module = new SimpleModule("cuid-module");
        module.addSerializer(CUID.class, new CuidSerializer());
        module.addDeserializer(CUID.class, new CuidDeserializer());
        return module;
    }
}
