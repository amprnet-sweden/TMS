package se.amprnet.tms.messaging;

import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.JWSHeader;
import com.nimbusds.jose.crypto.RSASSASigner;
import com.nimbusds.jose.jwk.RSAKey;
import com.nimbusds.jose.jwk.gen.RSAKeyGenerator;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.SignedJWT;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.oauth2.jwt.JwtValidators;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import se.amprnet.tms.auth.AmprnetClaimsConverter;

import java.time.Instant;
import java.util.Date;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class WebSocketAuthenticatorServiceTests {
    private static final String ISSUER = "https://identity.example/auth/realms/amprnet";
    private static RSAKey signingKey;
    private static WebSocketAuthenticatorService service;

    @BeforeAll
    static void setup() throws Exception {
        signingKey = new RSAKeyGenerator(2048).generate();
        NimbusJwtDecoder decoder = NimbusJwtDecoder.withPublicKey(signingKey.toRSAPublicKey()).build();
        decoder.setJwtValidator(JwtValidators.createDefaultWithIssuer(ISSUER));
        service = new WebSocketAuthenticatorService(decoder, new AmprnetClaimsConverter());
    }

    private String token(RSAKey key, String issuer, String username, Instant expires) throws Exception {
        JWTClaimsSet claims = new JWTClaimsSet.Builder().issuer(issuer).subject("test-user")
                .issueTime(Date.from(Instant.now().minusSeconds(600))).expirationTime(Date.from(expires))
                .claim("preferred_username", username)
                .claim("realm_access", Map.of("roles", List.of("tms-superuser"))).build();
        SignedJWT jwt = new SignedJWT(new JWSHeader(JWSAlgorithm.RS256), claims);
        jwt.sign(new RSASSASigner(key));
        return jwt.serialize();
    }

    @Test
    void authenticatesSignedJwtWithoutCreatingAPasswordBasedUser() throws Exception {
        var authentication = service.getAuthenticatedOrFail(
                token(signingKey, ISSUER, "appuser", Instant.now().plusSeconds(300)));
        assertTrue(authentication.isAuthenticated());
        assertEquals("appuser", authentication.getName());
        assertTrue(authentication.getAuthorities().stream()
                .anyMatch(a -> a.getAuthority().equals("ROLE_tms-superuser")));
    }

    @Test
    void rejectsExpiredToken() throws Exception {
        String token = token(signingKey, ISSUER, "appuser", Instant.now().minusSeconds(300));
        assertThrows(AuthenticationException.class, () -> service.getAuthenticatedOrFail(token));
    }

    @Test
    void rejectsWrongIssuerAndSignature() throws Exception {
        String wrongIssuer = token(signingKey, "https://other.example", "appuser", Instant.now().plusSeconds(300));
        String wrongSignature = token(new RSAKeyGenerator(2048).generate(), ISSUER, "appuser", Instant.now().plusSeconds(300));
        assertThrows(AuthenticationException.class, () -> service.getAuthenticatedOrFail(wrongIssuer));
        assertThrows(AuthenticationException.class, () -> service.getAuthenticatedOrFail(wrongSignature));
    }

    @Test
    void rejectsMissingUsernameAndMalformedToken() throws Exception {
        String missingUsername = token(signingKey, ISSUER, null, Instant.now().plusSeconds(300));
        assertThrows(AuthenticationException.class, () -> service.getAuthenticatedOrFail(missingUsername));
        assertThrows(AuthenticationException.class, () -> service.getAuthenticatedOrFail("not-a-jwt"));
    }
}
