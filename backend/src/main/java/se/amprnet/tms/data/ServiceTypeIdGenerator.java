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
import org.springframework.data.relational.core.mapping.event.BeforeConvertCallback;
import org.springframework.stereotype.Component;

@Component
public class ServiceTypeIdGenerator implements BeforeConvertCallback<ServiceType> {
    @Override
    public ServiceType onBeforeConvert(ServiceType entity) {
        if (entity.id() == null) {
            return new ServiceType(CUID.randomCUID2(), entity.version(), entity.missionId(), entity.name(), entity.icon(), entity.color(), entity.createRoles(), entity.readRoles(), entity.updateRoles(), entity.deleteRoles(), entity.ctime(), entity.ctime());
        }
        return entity;
    }
}
