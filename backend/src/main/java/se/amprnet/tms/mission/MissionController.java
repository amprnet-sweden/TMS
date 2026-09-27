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

package se.amprnet.tms.mission;

import io.github.thibaultmeyer.cuid.CUID;
import org.springframework.http.HttpStatus;
import org.springframework.lang.Nullable;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import se.amprnet.tms.model.MissionDTO;
import se.amprnet.tms.model.MissionMemberDTO;
import se.amprnet.tms.model.ResultModel;

import java.util.Collection;
import java.util.List;
import java.util.Map;

import static se.amprnet.tms.TmsConstants.SUPERUSER_ROLE;

@RestController
@RequestMapping("/missions")
public class MissionController {

    private final MissionService missionService;

    public MissionController(MissionService missionService) {
        this.missionService = missionService;
    }

    private Collection<String> getRoles(Jwt jwt) {
        final var realmAccess = (Map<String, Object>) jwt.getClaims().getOrDefault("realm_access", Map.of());
        return (Collection<String>) realmAccess.getOrDefault("roles", List.of());
    }

    private void checkPermission(Jwt jwt) {
        if (!getRoles(jwt).contains(SUPERUSER_ROLE)) {
            throw new AccessDeniedException("User not authorized to view missions");
        }
    }

    @GetMapping
    public ResultModel<List<MissionDTO>> getMissions(@AuthenticationPrincipal Jwt jwt, @Nullable @RequestParam("status") MissionStatus status) {
        checkPermission(jwt);
        return ResultModel.success(missionService.getMissions(status));
    }

    @PostMapping
    public ResultModel<MissionDTO> createMission(@AuthenticationPrincipal Jwt jwt, @RequestBody MissionDTO mission) {
        checkPermission(jwt);
        return ResultModel.success(missionService.createMission(mission));
    }

    @PutMapping("/{id}")
    public ResultModel<MissionDTO> updateMission(@AuthenticationPrincipal Jwt jwt, @PathVariable CUID id, @RequestBody MissionDTO mission) {
        checkPermission(jwt);
        return missionService.updateMission(id, mission)
                .map(ResultModel::success)
                .orElse(ResultModel.error(HttpStatus.NOT_FOUND, "Mission not found: " + id));
    }

    @GetMapping("/{id}")
    public ResultModel<MissionDTO> getMission(@AuthenticationPrincipal Jwt jwt, @PathVariable CUID id) {
        // TODO Check that current user is member of this mission. If not, return 403.
        //checkPermission(jwt);
        return missionService.getMission(id)
                .map(ResultModel::success)
                .orElse(ResultModel.error(HttpStatus.NOT_FOUND, "Mission not found: " + id));
    }

    @DeleteMapping("/{id}")
    public ResultModel<MissionDTO> deleteMission(@AuthenticationPrincipal Jwt jwt, @PathVariable CUID id) {
        checkPermission(jwt);
        return missionService.deleteMission(id)
                .map(ResultModel::success)
                .orElse(ResultModel.error(HttpStatus.NOT_FOUND, "Mission not found: " + id));
    }

    @GetMapping("/{id}/members")
    public ResultModel<List<MissionMemberDTO>> getMissionMembers(@AuthenticationPrincipal Jwt jwt, @PathVariable CUID id) {
        // TODO Check that current user is member of this mission. If not, return 403.
        //checkPermission(jwt);
        return ResultModel.success(missionService.getMissionMembers(id));
    }

    @PostMapping("/{id}/members")
    public ResultModel<MissionMemberDTO> saveMissionMember(@AuthenticationPrincipal Jwt jwt, @PathVariable CUID id, @RequestBody MissionMemberDTO member) {
        checkPermission(jwt);
        return missionService.saveMissionMember(id, member)
                .map(ResultModel::success)
                .orElse(ResultModel.error(HttpStatus.NOT_FOUND, "Mission not found: " + id));
    }

    @DeleteMapping("/{id}/members/{userId}")
    public ResultModel<MissionMemberDTO> deleteMissionMember(@AuthenticationPrincipal Jwt jwt, @PathVariable CUID id, @PathVariable CUID userId) {
        checkPermission(jwt);
        return missionService.deleteMissionMember(id, userId)
                .map(ResultModel::success)
                .orElse(ResultModel.error(HttpStatus.NOT_FOUND, "Member " + userId + " not found on mission " + id));
    }
}
