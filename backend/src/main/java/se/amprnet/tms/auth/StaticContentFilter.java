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

import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.springframework.http.HttpStatus.NOT_FOUND;

@Component
public class StaticContentFilter implements Filter {

    private static final List<String> fileExtensions = List.of(".html", ".js", ".json", ".csv", ".css", ".png", ".svg", ".ttf", ".woff", ".woff2", ".jpg", ".jpeg", ".gif", ".ico");

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain) throws IOException, ServletException {
        doFilter((HttpServletRequest) request, (HttpServletResponse) response, chain);
    }

    private void doFilter(HttpServletRequest request, HttpServletResponse response, FilterChain chain) throws IOException, ServletException {
        final String path = request.getServletPath();
        final boolean isApi = !path.startsWith("/tms/");
        final boolean isResourceFile = !isApi && fileExtensions.stream().anyMatch(path::contains);

        if (isApi) {
            chain.doFilter(request, response);
        } else if (isResourceFile) {
            resourceToResponse("static" + path, response);
        } else {
            resourceToResponse("static/tms/index.html", response);
        }
    }

    private void resourceToResponse(String resourcePath, HttpServletResponse response) throws IOException {
        try (InputStream inputStream = Thread.currentThread().getContextClassLoader().getResourceAsStream(resourcePath)) {
            if (inputStream != null) {
                response.setContentType(Files.probeContentType(Path.of(resourcePath)));
                inputStream.transferTo(response.getOutputStream());
            } else {
                response.sendError(NOT_FOUND.value(), NOT_FOUND.getReasonPhrase());
            }
        }
    }
}
