package se.amprnet.tms;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
@Import(ContainersConfig.class)
class TmsApplicationTests {

    @Test
    void contextLoads() {
    }
}
