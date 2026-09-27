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
import org.springframework.data.repository.CrudRepository;
import org.springframework.data.repository.RepositoryDefinition;

import java.util.Optional;

@RepositoryDefinition(domainClass = Priority.class, idClass = CUID.class)
public interface PriorityRepository extends CrudRepository<Priority, CUID> {
    Optional<Priority> findByMissionIdAndName(CUID missionId, String name);
    Optional<Priority> findByMissionIdAndId(CUID missionId, CUID id);
    Iterable<Priority> findAllByMissionIdOrderByNameAsc(CUID missionId);
}
