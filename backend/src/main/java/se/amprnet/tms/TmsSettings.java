package se.amprnet.tms;

public record TmsSettings(Frontend frontend) {
    public record Frontend(Map map) {
        public record Map(String tiles, int zoom, int maxZoom, double latitude, double longitude) {
        }
    }
}
