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

package se.amprnet.tms.messaging;

import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.stereotype.Controller;

import java.io.Serializable;
import java.util.Date;

@Controller
@EnableScheduling
public class NotificationsController {

    private final SimpMessagingTemplate template;

    public NotificationsController(SimpMessagingTemplate template) {
        this.template = template;
    }

    @MessageMapping("/notifications")
    public String sendNotification(String message) {
        return message;
    }

    //@Scheduled(fixedRate = 10000, initialDelay = 15000)
    public void sendNotifications() {
        template.convertAndSend("/topic/notifications",
                new OutputMessage("NOTICE", "Meddelande", "Hello World at " + new Date(), "green"));
    }

    record OutputMessage(String category, String subject, String message, String color) implements Serializable {
    }
}
