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

import org.springframework.core.convert.converter.Converter;
import org.springframework.security.authentication.AbstractAuthenticationToken;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.stream.Collectors;

@Component
public class AmprnetClaimsConverter implements Converter<Jwt, AbstractAuthenticationToken> {
    @Override
    public AbstractAuthenticationToken convert(Jwt jwt) {
        return new JwtAuthenticationToken(jwt, extractRoles(jwt), getPrincipalFromClaim(jwt));
    }

    private String getPrincipalFromClaim(Jwt jwt) {
        return jwt.getClaim("preferred_username");
    }

    private Collection<GrantedAuthority> extractRoles(Jwt jwt) {
        Set<GrantedAuthority> roles = new HashSet<>();
        roles.addAll(extractRealmRoles(jwt));
        roles.addAll(extractResourceRoles(jwt));
        return roles;
    }

    private Collection<GrantedAuthority> extractRealmRoles(Jwt jwt) {
        Map<String, Object> resource = jwt.getClaim("realm_access");
        if (resource != null) {
            Collection<String> roles = (Collection<String>) resource.get("roles");
            if (roles != null) {
                return roles.stream()
                        .map(role -> new SimpleGrantedAuthority("ROLE_" + role))
                        .collect(Collectors.toSet());
            }
        }
        return Collections.emptySet();
    }

    private Collection<GrantedAuthority> extractResourceRoles(Jwt jwt) {
        Map<String, Object> resource = jwt.getClaim("resource_access");
        if (resource != null) {
            Map<String, Object> backend = (Map<String, Object>) resource.get("tms-backend");
            if (backend != null) {
                Collection<String> roles = (Collection<String>) backend.get("roles");
                if (roles != null) {
                    return roles.stream()
                            .map(role -> new SimpleGrantedAuthority("ROLE_" + role))
                            .collect(Collectors.toSet());
                }
            }
        }
        return Collections.emptySet();
    }
}
