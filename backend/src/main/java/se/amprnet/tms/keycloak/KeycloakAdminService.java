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

import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import jakarta.validation.constraints.NotBlank;
import org.keycloak.admin.client.Keycloak;
import org.keycloak.admin.client.KeycloakBuilder;
import org.keycloak.admin.client.resource.UserResource;
import org.keycloak.representations.idm.UserRepresentation;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import se.amprnet.tms.TmsConfiguration;
import se.amprnet.tms.model.UserDTO;

import java.util.Collections;
import java.util.List;
import java.util.Optional;

@Service
public class KeycloakAdminService {

    private final TmsConfiguration.KeycloakConfiguration configuration;
    private Keycloak keycloak;

    public KeycloakAdminService(TmsConfiguration.KeycloakConfiguration configuration) {
        this.configuration = configuration;
    }

    @PostConstruct
    public void init() {
        this.keycloak = KeycloakBuilder.builder()
                .serverUrl(configuration.getUri())
                .realm("master")
                .clientId(configuration.getClientId())
                .grantType("password")
                .username(configuration.getUsername())
                .password(configuration.getPassword())
                .build();
    }

    @PreDestroy
    public void closeKeycloak() {
        keycloak.close();
    }

    @Cacheable("users")
    public List<UserDTO> getUsers() {
        return keycloak.realm(configuration.getRealm()).users().list().stream().map(this::map).toList();
    }

    @Cacheable("users")
    public List<UserDTO> findUsers(@NotBlank String username) {
        return keycloak.realm(configuration.getRealm()).users().search(username).stream().map(this::map).toList();
    }

    @Cacheable("users")
    public Optional<UserDTO> getUserByUsername(@NotBlank String username) {
        final List<UserRepresentation> result = keycloak.realm(configuration.getRealm()).users().search(username, true);
        if (result.isEmpty()) {
            return Optional.empty();
        }
        return Optional.of(map(result.get(0)));
    }

    @Cacheable("users")
    public Optional<UserDTO> getUser(@NotBlank String sub) {
        final UserResource user = keycloak.realm(configuration.getRealm()).users().get(sub);
        if (user != null) {
            return Optional.of(map(user.toRepresentation()));
        }
        return Optional.empty();
    }

    @Cacheable("roles")
    public List<Role> getRoles() {
        return keycloak.realm(configuration.getRealm()).roles().list().stream().map(kcRole -> new Role(kcRole.getId(), kcRole.getName(), kcRole.getDescription())).toList();
    }

    @Cacheable("groups")
    public List<Group> getGroups() {
        return keycloak.realm(configuration.getRealm()).groups().groups().stream().map(kcGroup -> new Group(kcGroup.getId(), kcGroup.getName())).toList();
    }

    private UserDTO map(UserRepresentation kcUser) {
        return new UserDTO(kcUser.getId(), kcUser.getUsername(), kcUser.getEmail(), kcUser.getFirstName(), kcUser.getLastName(), kcUser.getRealmRoles() != null ? kcUser.getRealmRoles() : Collections.emptyList());
    }
}
