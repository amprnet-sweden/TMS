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

package se.amprnet.tms.incident;

import io.github.thibaultmeyer.cuid.CUID;
import jakarta.validation.constraints.NotNull;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import se.amprnet.tms.TmsContext;
import se.amprnet.tms.model.*;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;
import java.util.function.Predicate;

import static se.amprnet.tms.TmsConstants.SUPERUSER_ROLE;
import static se.amprnet.tms.TmsConstants.TMS_MISSION_HEADER;

@RestController
@RequestMapping("/metadata")
public class MetadataController {

    private final IncidentService incidentService;

    public MetadataController(IncidentService incidentService) {
        this.incidentService = incidentService;
    }

    @GetMapping
    public ResultModel<Composite> getAll(@AuthenticationPrincipal Jwt jwt, @RequestHeader(TMS_MISSION_HEADER) @NotNull CUID missionId) {
        final TmsContext context = new TmsContext(missionId);
        return ResultModel.success(new Composite(getAvailableServices(context, jwt), incidentService.getStatuses(context), incidentService.getPriorities(context)));
    }

    @GetMapping("/services")
    public ResultModel<List<ServiceDTO>> getServices(@AuthenticationPrincipal Jwt jwt, @RequestHeader(TMS_MISSION_HEADER) @NotNull CUID missionId) {
        return ResultModel.success(getAvailableServices(new TmsContext(missionId), jwt));
    }

    @PostMapping("/services")
    public ResultModel<ServiceDTO> saveService(@AuthenticationPrincipal Jwt jwt, @RequestHeader(TMS_MISSION_HEADER) @NotNull CUID missionId, @RequestBody ServiceDTO service) {
        return ResultModel.success(incidentService.saveServiceType(new TmsContext(missionId), service));
    }

    @DeleteMapping("/services/{id}")
    public ResultModel<ServiceDTO> deleteService(@AuthenticationPrincipal Jwt jwt, @RequestHeader(TMS_MISSION_HEADER) @NotNull CUID missionId, @PathVariable CUID id) {
        incidentService.deleteServiceType(new TmsContext(missionId), id);
        return ResultModel.success(new ServiceDTO(null, null, null, null, null, null));
    }

    @GetMapping("/statuses")
    public ResultModel<List<StatusDTO>> getStatuses(@AuthenticationPrincipal Jwt jwt, @RequestHeader(TMS_MISSION_HEADER) @NotNull CUID missionId) {
        return ResultModel.success(incidentService.getStatuses(new TmsContext(missionId)));
    }

    @PostMapping("/statuses")
    public ResultModel<StatusDTO> saveStatus(@AuthenticationPrincipal Jwt jwt, @RequestHeader(TMS_MISSION_HEADER) @NotNull CUID missionId, @RequestBody StatusDTO status) {
        return ResultModel.success(incidentService.saveStatus(new TmsContext(missionId), status));
    }

    @DeleteMapping("/statuses/{id}")
    public ResultModel<StatusDTO> deleteStatus(@AuthenticationPrincipal Jwt jwt, @RequestHeader(TMS_MISSION_HEADER) @NotNull CUID missionId, @PathVariable CUID id) {
        incidentService.deleteStatus(new TmsContext(missionId), id);
        return ResultModel.success(new StatusDTO(null, null, null, null, null));
    }

    @GetMapping("/priorities")
    public ResultModel<List<PriorityDTO>> getPriorities(@AuthenticationPrincipal Jwt jwt, @RequestHeader(TMS_MISSION_HEADER) @NotNull CUID missionId) {
        return ResultModel.success(incidentService.getPriorities(new TmsContext(missionId)));
    }

    @PostMapping("/priorities")
    public ResultModel<PriorityDTO> savePriority(@AuthenticationPrincipal Jwt jwt, @RequestHeader(TMS_MISSION_HEADER) @NotNull CUID missionId, @RequestBody PriorityDTO priority) {
        return ResultModel.success(incidentService.savePriority(new TmsContext(missionId), priority));
    }

    @DeleteMapping("/priorities/{id}")
    public ResultModel<PriorityDTO> deletePriority(@AuthenticationPrincipal Jwt jwt, @RequestHeader(TMS_MISSION_HEADER) @NotNull CUID missionId, @PathVariable CUID id) {
        incidentService.deletePriority(new TmsContext(missionId), id);
        return ResultModel.success(new PriorityDTO(null, null, null, null, null));
    }

    private Predicate<ServiceDTO> hasClientRole(Function<Roles, Set<String>> roleExtractor, Collection<String> roles) {
        return (service) -> {
            if (roles.contains(SUPERUSER_ROLE)) {
                return true;
            }
            Set<String> claims = roleExtractor.apply(service.roles());
            return claims.isEmpty() || claims.stream().anyMatch(roles::contains);
        };
    }

    @SuppressWarnings("unchecked")
    private List<ServiceDTO> getAvailableServices(TmsContext context, Jwt jwt) {
        final var realmAccess = (Map<String, Object>) jwt.getClaims().getOrDefault("realm_access", Map.of());
        final var webClientRoles = (Collection<String>) realmAccess.getOrDefault("roles", List.of());

        return incidentService.getServiceTypes(context)
                .stream()
                .filter(hasClientRole(Roles::readRoles, webClientRoles))
                .toList();
    }

    /*
        private List<ServiceDTO> getAvailableServices(Jwt jwt) {
            final var resourceAccess = (Map<String, Object>) jwt.getClaims().getOrDefault("resource_access", Map.of());
            final var webClientAccess = (Map<String, Object>) resourceAccess.getOrDefault(RESOURCE_ACCESS_NAME, Map.of());
            final var webClientRoles = (Collection<String>) webClientAccess.getOrDefault("roles", List.of());

            return incidentService.getServiceTypes()
                    .stream()
                    .filter(hasClientRole(Roles::readRoles, webClientRoles))
                    .toList();
        }
      */
    public record Composite(List<ServiceDTO> services, List<StatusDTO> statuses, List<PriorityDTO> priorities) {
    }
}
