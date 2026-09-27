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

package se.amprnet.tms.incident;

import io.github.thibaultmeyer.cuid.CUID;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import se.amprnet.tms.TmsContext;
import se.amprnet.tms.data.DashboardData;
import se.amprnet.tms.model.ResultModel;

import java.util.List;

import static se.amprnet.tms.TmsConstants.TMS_MISSION_HEADER;

@RestController
@RequestMapping("/dashboard")
public class DashboardController {

    private final IncidentService incidentService;

    public DashboardController(IncidentService incidentService) {
        this.incidentService = incidentService;
    }

    @GetMapping
    public ResultModel<List<DashboardData>> getDashboardData(@AuthenticationPrincipal Jwt jwt, @RequestHeader(TMS_MISSION_HEADER) CUID missionId) {
        final List<DashboardData> data = incidentService.getDashboardData(new TmsContext(missionId));
        return ResultModel.success(data);
    }

}
