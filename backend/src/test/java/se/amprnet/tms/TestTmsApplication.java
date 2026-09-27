package se.amprnet.tms;

import org.springframework.boot.SpringApplication;

public class TestTmsApplication {

    public static void main(String[] args) {
        SpringApplication
                .from(TmsApplication::main)
                .with(ContainersConfig.class)
                .run(args);
    }

}
