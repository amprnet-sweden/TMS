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

import com.nimbusds.jwt.JWT;
import com.nimbusds.jwt.JWTParser;
import org.springframework.security.authentication.AuthenticationCredentialsNotFoundException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.stereotype.Service;

@Service
public class WebSocketAuthenticatorService {

    private final UserDetailsService userDetailsService;

    public WebSocketAuthenticatorService(UserDetailsService userDetailsService) {
        this.userDetailsService = userDetailsService;
    }

    public UsernamePasswordAuthenticationToken getAuthenticatedOrFail(String token) {
        try {
            JWT jwt = JWTParser.parse(token);
            String email = (String) jwt.getJWTClaimsSet().getClaim("preferred_username");
            UserDetails userDetails = userDetailsService.loadUserByUsername(email);

            return new UsernamePasswordAuthenticationToken(
                    userDetails, null,
                    userDetails.getAuthorities()
            );
        } catch (Exception e) {
            throw new AuthenticationCredentialsNotFoundException(e.getMessage());
        }
    }
}
