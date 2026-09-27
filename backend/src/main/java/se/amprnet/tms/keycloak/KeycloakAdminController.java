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

package se.amprnet.tms.keycloak;

import io.micrometer.common.util.StringUtils;
import org.springframework.lang.Nullable;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import se.amprnet.tms.model.UserDTO;

import java.util.List;

@RestController
@RequestMapping("/keycloak/admin")
public class KeycloakAdminController {

    private final KeycloakAdminService keycloakAdminService;

    public KeycloakAdminController(KeycloakAdminService keycloakAdminService) {
        this.keycloakAdminService = keycloakAdminService;
    }

    @GetMapping("/users")
    public List<UserDTO> getUsers(@Nullable @RequestParam(required = false) String q) {
        if (StringUtils.isBlank(q)) {
            return keycloakAdminService.getUsers();
        }
        return keycloakAdminService.findUsers(q);
    }

    @GetMapping("/groups")
    public List<Group> getGroups() {
        return keycloakAdminService.getGroups();
    }

    @GetMapping("/roles")
    public List<Role> getRoles() {
        return keycloakAdminService.getRoles();
    }
}
