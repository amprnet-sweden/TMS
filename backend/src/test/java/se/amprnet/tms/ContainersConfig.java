package se.amprnet.tms;

import dasniko.testcontainers.keycloak.KeycloakContainer;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.springframework.test.context.DynamicPropertyRegistrar;
import org.testcontainers.containers.MariaDBContainer;
import org.testcontainers.utility.DockerImageName;

@TestConfiguration(proxyBeanMethods = false)
public class ContainersConfig {

    static String MARIADB_IMAGE = "mariadb:10.11.15";
    static String POSTGRES_IMAGE = "postgres:16-alpine";
    static String KEYCLOAK_IMAGE = "quay.io/keycloak/keycloak:26.4.7";
    static String realmName = "amprnet";
    static String realmImportFile = realmName + "-realm.json";

    @Bean
    @ServiceConnection
    public MariaDBContainer<?> mariadb() {
        return new MariaDBContainer<>(DockerImageName.parse(MARIADB_IMAGE)).withDatabaseName("tms").withUsername("root").withPassword("");
    }

    /*
    @Bean
    @ServiceConnection
    public PostgreSQLContainer<?> postgres() {
        return new PostgreSQLContainer<>(POSTGRES_IMAGE);
    }
    */

    @Bean
    public DynamicPropertyRegistrar oauth2Properties(KeycloakContainer keycloak) {
        String url = keycloak.getAuthServerUrl() + "/realms/" + realmName;
        System.out.println("URL: " + url);
        return (registry) -> registry.add("spring.security.oauth2.resourceserver.jwt.issuer-uri", () -> url);
    }

    @Bean
    public KeycloakContainer keycloak() {
        return new KeycloakContainer(KEYCLOAK_IMAGE).withRealmImportFile(realmImportFile);
    }
}
