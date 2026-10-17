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

package se.amprnet.tms;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

import java.util.ArrayList;
import java.util.List;

@Validated
@ConfigurationProperties("tms")
public class TmsConfiguration {

    private String tenant;
    private boolean demo = false;
    private List<String> allowedOrigins = new ArrayList<>();
    @Valid
    private final KeycloakConfiguration keycloak = new KeycloakConfiguration();
    @Valid
    private final FrontendConfiguration frontend = new FrontendConfiguration();

    public String getTenant() {
        return tenant;
    }

    public void setTenant(String tenant) {
        this.tenant = tenant;
    }

    public boolean isDemo() {
        return demo;
    }

    public void setDemo(boolean demo) {
        this.demo = demo;
    }

    public List<String> getAllowedOrigins() {
        return allowedOrigins;
    }

    public void setAllowedOrigins(List<String> allowedOrigins) {
        this.allowedOrigins = allowedOrigins;
    }

    public KeycloakConfiguration getKeycloak() {
        return keycloak;
    }

    public FrontendConfiguration getFrontend() {
        return frontend;
    }

    public static class KeycloakConfiguration {
        @NotBlank
        private String uri = "https://host.docker.internal:9003/auth";
        @NotBlank
        private String realm = "amprnet";
        @NotBlank
        private String clientId = "admin-cli";
        @NotBlank
        private String username = "tms";
        @NotBlank
        private String password = "secret";

        public String getUri() {
            return uri;
        }

        public void setUri(String uri) {
            this.uri = uri;
        }

        public String getRealm() {
            return realm;
        }

        public void setRealm(String realm) {
            this.realm = realm;
        }

        public String getClientId() {
            return clientId;
        }

        public void setClientId(String clientId) {
            this.clientId = clientId;
        }

        public String getUsername() {
            return username;
        }

        public void setUsername(String username) {
            this.username = username;
        }

        public String getPassword() {
            return password;
        }

        public void setPassword(String password) {
            this.password = password;
        }
    }

    public static class FrontendConfiguration {

        @Valid
        private final MapConfiguration map = new MapConfiguration();

        public MapConfiguration getMap() {
            return map;
        }

        public static class MapConfiguration {
            @NotBlank
            private String tiles = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
            @Min(1)
            @Max(20)
            private int zoom = 12;
            @Min(1)
            @Max(25)
            private int maxZoom = 19;
            private LatLng center = new LatLng(59.328893326719275, 18.16224786713087);

            public String getTiles() {
                return tiles;
            }

            public void setTiles(String tiles) {
                this.tiles = tiles;
            }

            public int getZoom() {
                return zoom;
            }

            public void setZoom(int zoom) {
                this.zoom = zoom;
            }

            public int getMaxZoom() {
                return maxZoom;
            }

            public void setMaxZoom(int maxZoom) {
                this.maxZoom = maxZoom;
            }

            public LatLng getCenter() {
                return center;
            }

            public void setCenter(LatLng center) {
                this.center = center;
            }

            public record LatLng(double lat, double lng) {
            }
        }
    }
}
