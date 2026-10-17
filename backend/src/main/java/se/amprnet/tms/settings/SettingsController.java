package se.amprnet.tms.settings;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import se.amprnet.tms.TmsConfiguration;
import se.amprnet.tms.TmsSettings;
import se.amprnet.tms.model.ResultModel;

@RestController
@RequestMapping("/settings")
public class SettingsController {
    private final TmsConfiguration configuration;

    public SettingsController(TmsConfiguration configuration) {
        this.configuration = configuration;
    }

    @GetMapping
    public ResultModel<TmsSettings> getSettings() {
        final var config = configuration.getFrontend().getMap();
        final var frontend = new TmsSettings.Frontend(new TmsSettings.Frontend.Map(config.getTiles(), config.getZoom(), config.getMaxZoom(), config.getCenter().lat(), config.getCenter().lng()));
        return ResultModel.success(new TmsSettings(frontend));
    }
}
