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

package se.amprnet.tms.auth;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import se.amprnet.tms.keycloak.KeycloakAdminService;
import se.amprnet.tms.mission.MissionService;
import se.amprnet.tms.model.MissionDTO;
import se.amprnet.tms.model.ResultModel;
import se.amprnet.tms.model.UserDTO;

import java.util.Collection;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/user")
public class AuthController {

    private static final Logger log = LoggerFactory.getLogger(AuthController.class);

    private final MissionService missionService;
    private final KeycloakAdminService keycloakService;

    public AuthController(MissionService missionService, KeycloakAdminService keycloakService) {
        this.missionService = missionService;
        this.keycloakService = keycloakService;
    }

    @GetMapping
    public ResponseEntity<UserDTO> getUser(@AuthenticationPrincipal Jwt jwt) {
        if (jwt == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        final String username = jwt.getClaim("preferred_username");
        log.debug("Received request to get user with username {}", username);
        log.debug("User {} {} {}", jwt.getSubject(), jwt.getClaim("given_name"), jwt.getClaim("family_name"));

        return ResponseEntity.ok(keycloakService.getUserByUsername(username)
                .map(user -> {
                    final var realmAccess = (Map<String, Object>) jwt.getClaims().getOrDefault("realm_access", Map.of());
                    final var webClientRoles = (Collection<String>) realmAccess.getOrDefault("roles", List.of());
                    final List<String> tmsRoles = webClientRoles.stream().filter(role -> role.startsWith("tms-")).toList();
                    return new UserDTO(user.id(), user.username(), user.email(), user.firstName(), user.lastName(), tmsRoles);
                })
                .orElseThrow(() -> new UsernameNotFoundException("User not found: " + username))
        );
    }

    @GetMapping("/missions")
    public ResponseEntity<ResultModel<List<MissionDTO>>> getMissions(@AuthenticationPrincipal Jwt jwt) {
        if (jwt == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        return ResponseEntity.ok(ResultModel.success(missionService.getMemberMissions(jwt.getSubject())));
    }
}
