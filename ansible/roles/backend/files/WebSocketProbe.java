import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.WebSocket;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.TimeUnit;

/** Verify a real STOMP CONNECT through NGINX; token is read only from stdin. */
class WebSocketProbe implements WebSocket.Listener {
    private final CompletableFuture<Void> connected = new CompletableFuture<>();
    private final StringBuilder frame = new StringBuilder();

    public void onOpen(WebSocket socket) { socket.request(1); }

    public CompletionStage<?> onText(WebSocket socket, CharSequence data, boolean last) {
        frame.append(data);
        if (last) {
            String message = frame.toString().stripLeading();
            if (message.startsWith("CONNECTED\n") || message.startsWith("CONNECTED\r\n")) {
                connected.complete(null);
            } else if (message.startsWith("ERROR")) {
                connected.completeExceptionally(new IllegalStateException("STOMP rejected authentication"));
            }
            frame.setLength(0);
        }
        socket.request(1);
        return null;
    }

    public void onError(WebSocket socket, Throwable error) {
        connected.completeExceptionally(new IllegalStateException("WebSocket failed"));
    }

    public CompletionStage<?> onClose(WebSocket socket, int code, String reason) {
        connected.completeExceptionally(new IllegalStateException("WebSocket closed before CONNECTED"));
        return null;
    }

    public static void main(String[] args) {
        WebSocket socket = null;
        try {
            String token = new String(System.in.readAllBytes(), StandardCharsets.UTF_8).trim();
            if (token.isEmpty() || token.contains("\n") || token.contains("\r")) {
                throw new IllegalArgumentException("Invalid token input");
            }
            String origin = args[0];
            var listener = new WebSocketProbe();
            socket = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(30)).build()
                    .newWebSocketBuilder().header("Origin", origin)
                    .subprotocols("v12.stomp").connectTimeout(Duration.ofSeconds(30))
                    .buildAsync(URI.create(origin.replaceFirst("^https://", "wss://") + "/api/ws"), listener)
                    .get(40, TimeUnit.SECONDS);
            socket.sendText("CONNECT\naccept-version:1.2\nhost:" + URI.create(origin).getHost() + "\nauthorization:Bearer "
                    + token + "\nheart-beat:0,0\n\n\0", true).get(30, TimeUnit.SECONDS);
            listener.connected.get(45, TimeUnit.SECONDS);
            socket.sendText("DISCONNECT\n\n\0", true).get(10, TimeUnit.SECONDS);
            System.out.println("STOMP CONNECTED");
        } catch (Exception error) {
            System.err.println("Verified WSS/STOMP connection failed or timed out");
            System.exit(1);
        } finally {
            if (socket != null) socket.abort();
        }
    }
}
