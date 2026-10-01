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

package se.amprnet.tms.messaging;

import org.springframework.security.authentication.AuthenticationCredentialsNotFoundException;
import org.springframework.security.authentication.AbstractAuthenticationToken;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtException;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import se.amprnet.tms.auth.AmprnetClaimsConverter;

@Service
public class WebSocketAuthenticatorService {

    private final JwtDecoder jwtDecoder;
    private final AmprnetClaimsConverter claimsConverter;

    public WebSocketAuthenticatorService(JwtDecoder jwtDecoder, AmprnetClaimsConverter claimsConverter) {
        this.jwtDecoder = jwtDecoder;
        this.claimsConverter = claimsConverter;
    }

    public AbstractAuthenticationToken getAuthenticatedOrFail(String token) {
        try {
            // Use the same signature, issuer and expiry validation as HTTP requests.
            Jwt jwt = jwtDecoder.decode(token);
            if (!StringUtils.hasText(jwt.getClaimAsString("preferred_username"))) {
                throw new AuthenticationCredentialsNotFoundException("Missing WebSocket user identity");
            }
            return claimsConverter.convert(jwt);
        } catch (JwtException | IllegalArgumentException e) {
            throw new AuthenticationCredentialsNotFoundException("Invalid WebSocket access token");
        }
    }
}
