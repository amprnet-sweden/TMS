package se.amprnet.tms;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.ActiveProfiles;

import static org.junit.jupiter.api.Assertions.assertEquals;

@SpringBootTest
@ActiveProfiles("test")
@Import(ContainersConfig.class)
class TmsApplicationTests {

    @Autowired
    TmsConfiguration configuration;

    @Test
    void configurationLoads() {
        assertEquals("http://localhost:8080/auth", configuration.getKeycloak().getUri());
        assertEquals("test", configuration.getKeycloak().getRealm());
        assertEquals("admin-cli", configuration.getKeycloak().getUsername());
        assertEquals("password", configuration.getKeycloak().getPassword());
        assertEquals(15, configuration.getFrontend().getMap().getZoom());
    }
}
