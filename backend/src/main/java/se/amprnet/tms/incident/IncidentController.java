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
import org.springframework.http.HttpStatus;
import org.springframework.lang.Nullable;
import org.springframework.security.authentication.AuthenticationCredentialsNotFoundException;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import se.amprnet.tms.TmsContext;
import se.amprnet.tms.keycloak.KeycloakAdminService;
import se.amprnet.tms.model.CommentDTO;
import se.amprnet.tms.model.IncidentDTO;
import se.amprnet.tms.model.ResultModel;
import se.amprnet.tms.model.UserDTO;

import java.util.*;
import java.util.stream.Collectors;

import static se.amprnet.tms.TmsConstants.TMS_MISSION_HEADER;

@RestController
@RequestMapping("/incidents")
public class IncidentController {

    private final IncidentService incidentService;
    private final KeycloakAdminService keycloakService;

    public IncidentController(IncidentService incidentService, KeycloakAdminService keycloakService) {
        this.incidentService = incidentService;
        this.keycloakService = keycloakService;
    }

    private UserDTO getUser(@AuthenticationPrincipal Jwt jwt) {
        final String username = jwt.getClaim("preferred_username");
        return keycloakService.getUserByUsername(username).orElseThrow(() -> new AuthenticationCredentialsNotFoundException("User not logged in"));
    }

    private IncidentFilter parseQuery(Map<String, String> query) {
        if (query == null) {
            return null;
        }
        return new IncidentFilter(Optional.ofNullable(query.get("service")).map(this::stringToLong).orElse(Collections.emptyList()),
                Optional.ofNullable(query.get("status")).map(this::stringToLong).orElse(Collections.emptyList()),
                Optional.ofNullable(query.get("priority")).map(this::stringToLong).orElse(Collections.emptyList()));
    }

    private List<CUID> stringToLong(String s) {
        if (s != null) {
            return Arrays.stream(s.split(",")).map(CUID::fromString).collect(Collectors.toList());
        }
        return Collections.emptyList();
    }

    @GetMapping
    public ResultModel<List<IncidentDTO>> getIncidents(@AuthenticationPrincipal Jwt jwt, @RequestHeader(TMS_MISSION_HEADER) @NotNull CUID missionId, @Nullable @RequestParam(required = false) Map<String, String> query) {
        return new ResultModel<>(incidentService.getIncidents(new TmsContext(missionId), parseQuery(query), getUser(jwt)));
    }

    @GetMapping("/{id}")
    public ResultModel<IncidentDTO> getIncident(@AuthenticationPrincipal Jwt jwt, @RequestHeader(TMS_MISSION_HEADER) @NotNull CUID missionId, @PathVariable CUID id) {
        return incidentService.getIncident(new TmsContext(missionId), id, getUser(jwt))
                .map(ResultModel::success)
                .orElseGet(() -> ResultModel.error(HttpStatus.NOT_FOUND, "Incident with id " + id + " not found"));
    }

    @GetMapping("/{id}/comments")
    public ResultModel<List<CommentDTO>> getComments(@AuthenticationPrincipal Jwt jwt, @RequestHeader(TMS_MISSION_HEADER) @NotNull CUID missionId, @PathVariable CUID id) {
        return ResultModel.success(incidentService.getComments(new TmsContext(missionId), id, getUser(jwt)));
    }

    @GetMapping("/{id}/comments/{cid}")
    public Optional<ResultModel<CommentDTO>> getComment(@AuthenticationPrincipal Jwt jwt, @RequestHeader(TMS_MISSION_HEADER) @NotNull CUID missionId, @PathVariable CUID id, @PathVariable CUID cid) {
        return incidentService.getComment(new TmsContext(missionId), cid, getUser(jwt)).map(ResultModel::success);
    }

    @PostMapping("/{id}/comments")
    public ResultModel<CommentDTO> saveComment(@AuthenticationPrincipal Jwt jwt, @RequestHeader(TMS_MISSION_HEADER) @NotNull CUID missionId, @PathVariable CUID id, @RequestBody CommentDTO comment) {
        return ResultModel.success(incidentService.saveComment(new TmsContext(missionId), id, comment, getUser(jwt)));
    }

    @DeleteMapping("/{id}/comments/{cid}")
    public Optional<ResultModel<CommentDTO>> deleteComment(@AuthenticationPrincipal Jwt jwt, @RequestHeader(TMS_MISSION_HEADER) @NotNull CUID missionId, @PathVariable CUID id, @PathVariable CUID cid) {
        return incidentService.getComment(new TmsContext(missionId), cid, getUser(jwt))
                .map(comment -> {
                    incidentService.deleteComment(new TmsContext(missionId), comment.id());
                    return comment;
                })
                .map(ResultModel::success);
    }

    @PostMapping
    public ResultModel<IncidentDTO> createIncident(@AuthenticationPrincipal Jwt jwt, @RequestHeader(TMS_MISSION_HEADER) @NotNull CUID missionId, @RequestBody IncidentDTO incident) {
        return ResultModel.success(incident.id() != null ? incidentService.updateIncident(new TmsContext(missionId), incident.id(), incident, getUser(jwt)).orElseThrow() : incidentService.createIncident(new TmsContext(missionId), incident, getUser(jwt)));
    }

    @PutMapping("/{id}")
    public ResultModel<IncidentDTO> updateIncident(@AuthenticationPrincipal Jwt jwt, @RequestHeader(TMS_MISSION_HEADER) @NotNull CUID missionId, @PathVariable CUID id, @RequestBody IncidentDTO incident) {
        return incidentService.updateIncident(new TmsContext(missionId), id, incident, getUser(jwt)).map(ResultModel::success)
                .orElse(ResultModel.error(HttpStatus.NOT_FOUND, "Incident with id " + id + " not found"));
    }

    @DeleteMapping("/{id}")
    public ResultModel<IncidentDTO> deleteIncident(@AuthenticationPrincipal Jwt jwt, @RequestHeader(TMS_MISSION_HEADER) @NotNull CUID missionId, @PathVariable CUID id) {
        return incidentService.deleteIncident(new TmsContext(missionId), id, getUser(jwt))
                .map(ResultModel::success)
                .orElse(ResultModel.error(HttpStatus.NOT_FOUND, "Incident with id " + id + " not found"));
    }
}
