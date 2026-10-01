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

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.simp.stomp.StompCommand;
import org.springframework.messaging.simp.stomp.StompHeaderAccessor;
import org.springframework.messaging.support.ChannelInterceptor;
import org.springframework.messaging.support.MessageHeaderAccessor;
import org.springframework.security.authentication.AuthenticationCredentialsNotFoundException;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.AuthenticationException;
import org.springframework.stereotype.Component;

import java.util.Locale;

@Component
public class WebSocketAuthChannelInterceptor implements ChannelInterceptor {

    private static final Logger log = LoggerFactory.getLogger(WebSocketAuthChannelInterceptor.class);

    private final WebSocketAuthenticatorService authService;

    public WebSocketAuthChannelInterceptor(WebSocketAuthenticatorService authService) {
        this.authService = authService;
    }

    @Override
    public Message<?> preSend(Message<?> message, MessageChannel channel) {
        StompHeaderAccessor accessor = MessageHeaderAccessor.getAccessor(message, StompHeaderAccessor.class);
        if (accessor != null) {
            log.debug("preSend: {}", accessor.getCommand());
        } else {
            log.debug("preSend: No StompHeaderAccessor");
        }
        if (accessor != null && StompCommand.CONNECT == accessor.getCommand()) {
            String authHeader = accessor.getFirstNativeHeader("authorization");

            if (authHeader != null && authHeader.toLowerCase(Locale.ROOT).startsWith("bearer ")) {
                String jwt = authHeader.substring(7);
                try {
                    Authentication user = authService.getAuthenticatedOrFail(jwt);
                    accessor.setUser(user);
                } catch (AuthenticationException e) {
                    log.error("Authentication failed: {}", e.getMessage());
                    throw e; // Let the STOMP handler report the rejected connection.
                }
            } else {
                log.debug("preSend: No authorization header");
                throw new AuthenticationCredentialsNotFoundException("Missing WebSocket authorization");
            }
        }
        // CONNECT headers contain a bearer token; never log the complete message.
        return message;
    }
}
