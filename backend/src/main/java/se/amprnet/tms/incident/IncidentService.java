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
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import se.amprnet.tms.TmsConfiguration;
import se.amprnet.tms.TmsContext;
import se.amprnet.tms.data.*;
import se.amprnet.tms.keycloak.KeycloakAdminService;
import se.amprnet.tms.model.*;

import java.util.*;
import java.util.function.Predicate;
import java.util.stream.Collectors;

import static se.amprnet.tms.data.DataUtils.cuid;

@Service
public class IncidentService {

    private static final Logger log = LoggerFactory.getLogger(IncidentService.class);

    private final TmsConfiguration configuration;
    private final IncidentRepository incidentRepository;
    private final ServiceTypeRepository serviceTypeRepository;
    private final StatusRepository statusRepository;
    private final PriorityRepository priorityRepository;
    private final CommentRepository commentRepository;
    private final JdbcTemplate jdbcTemplate;
    private final SimpMessagingTemplate messageTemplate;
    private final KeycloakAdminService keycloakService;

    public IncidentService(TmsConfiguration configuration,
                           IncidentRepository incidentRepository,
                           ServiceTypeRepository serviceTypeRepository,
                           StatusRepository statusRepository,
                           PriorityRepository priorityRepository,
                           CommentRepository commentRepository,
                           JdbcTemplate jdbcTemplate,
                           SimpMessagingTemplate messageTemplate,
                           KeycloakAdminService keycloakService) {
        this.configuration = configuration;
        this.incidentRepository = incidentRepository;
        this.serviceTypeRepository = serviceTypeRepository;
        this.statusRepository = statusRepository;
        this.priorityRepository = priorityRepository;
        this.commentRepository = commentRepository;
        this.keycloakService = keycloakService;
        this.jdbcTemplate = jdbcTemplate;
        this.messageTemplate = messageTemplate;
    }

    public void sendNotification(Notification notification) {
        messageTemplate.convertAndSend("/topic/notifications", notification);
    }

    @Transactional(readOnly = true)
    public List<IncidentDTO> getIncidents(TmsContext context, IncidentFilter filter, UserDTO user) {
        final List<IncidentDTO> result = new ArrayList<>();
        final Predicate<Incident> serviceFilter = filter == null || filter.service().isEmpty() ? (i) -> true : (i) -> filter.service().contains(i.serviceId());
        final Predicate<Incident> statusFilter = filter == null || filter.status().isEmpty() ? (i) -> true : (i) -> filter.status().contains(i.statusId());
        final Predicate<Incident> priorityFilter = filter == null || filter.priority().isEmpty() ? (i) -> true : (i) -> filter.priority().contains(i.priorityId());
        incidentRepository.findAllByMissionIdOrderByName(context.mission()).forEach(record -> {
            if (serviceFilter.test(record) && statusFilter.test(record) && priorityFilter.test(record)) {
                result.add(toDTO(context, record));
            }
        });
        return result;
    }

    @Transactional(readOnly = true)
    public Optional<IncidentDTO> getIncident(TmsContext context, CUID id, UserDTO user) {
        return incidentRepository.findByMissionIdAndId(context.mission(), id).map(i -> toDTO(context, i));
    }

    @Transactional
    public IncidentDTO createIncident(TmsContext context, IncidentDTO incident, UserDTO user) {
        final Incident entity = mapIncident(context.mission(), incident, user);
        final IncidentDTO created = toDTO(context, incidentRepository.save(entity));
        sendNotification(new Notification(configuration.getTenant(),
                user.email(), created.assignedTo() != null ? created.assignedTo().email() : null,
                NotificationDomain.INCIDENT, NotificationCategory.CREATED, NotificationSeverity.INFO,
                "tms.incident.created.message", created.name(), created.id()));
        return created;
    }

    @Transactional
    public Optional<IncidentDTO> updateIncident(TmsContext context, CUID id, IncidentDTO incident, UserDTO user) {
        int rows = jdbcTemplate.update("UPDATE incident SET name = ?, description = ?, latitude = ?, longitude = ?, service_id = ?, status_id = ?, priority_id = ?, assigned_to = ?, mtime = CURRENT_TIMESTAMP, version = version + 1 WHERE version = ? AND mission_id = ? AND id = ?",
                incident.name(),
                incident.description(),
                incident.latitude(),
                incident.longitude(),
                cuid(incident.service().id()),
                cuid(incident.status().id()),
                cuid(incident.priority().id()),
                incident.assignedTo() != null ? incident.assignedTo().id() : null,
                incident.version(),
                cuid(context.mission()),
                cuid(id));
        if (rows == 0) {
            return Optional.empty();
        }
        return getIncident(context, id, user)
                .map(updated -> {
                    sendNotification(new Notification(configuration.getTenant(),
                            user.email(), updated.assignedTo() != null ? updated.assignedTo().email() : null,
                            NotificationDomain.INCIDENT, NotificationCategory.UPDATED, NotificationSeverity.INFO,
                            "tms.incident.updated.message", updated.name(), updated.id()));
                    return updated;
                });
    }

    @Transactional
    public Optional<IncidentDTO> deleteIncident(TmsContext context, CUID id, UserDTO user) {
        return getIncident(context, id, user)
                .map(deleted -> {
                    incidentRepository.deleteById(id);
                    sendNotification(new Notification(configuration.getTenant(),
                            user.email(), deleted.assignedTo() != null ? deleted.assignedTo().email() : null,
                            NotificationDomain.INCIDENT, NotificationCategory.DELETED, NotificationSeverity.INFO,
                            "tms.incident.deleted.message", deleted.name(), deleted.id()));
                    return deleted;
                });
    }

    @Transactional(readOnly = true)
    public List<ServiceDTO> getServiceTypes(TmsContext context) {
        final List<ServiceDTO> result = new ArrayList<>();
        serviceTypeRepository.findAllByMissionIdOrderByNameAsc(context.mission()).forEach(item -> result.add(toDTO(item)));
        return result;
    }

    @Transactional(readOnly = true)
    public Optional<ServiceDTO> getServiceType(TmsContext context, CUID id) {
        return serviceTypeRepository.findById(id).map(this::toDTO);
    }

    @Transactional
    public ServiceDTO saveServiceType(TmsContext context, ServiceDTO service) {
        return Optional.ofNullable(service.id())
                .flatMap(id -> serviceTypeRepository.findByMissionIdAndId(context.mission(), id))
                .flatMap(entity -> {
                    jdbcTemplate.update("UPDATE service_type SET name = ?, icon = ?, color = ?, create_roles = ?, read_roles = ?, update_roles = ?, delete_roles = ?, mtime = CURRENT_TIMESTAMP, version = version + 1 WHERE version = ? AND mission_id = ? AND id = ?",
                            service.name(),
                            service.icon(),
                            service.color(),
                            parseRoles(service.roles() != null ? service.roles().createRoles() : null),
                            parseRoles(service.roles() != null ? service.roles().readRoles() : null),
                            parseRoles(service.roles() != null ? service.roles().updateRoles() : null),
                            parseRoles(service.roles() != null ? service.roles().deleteRoles() : null),
                            service.version(),
                            cuid(context.mission()),
                            cuid(entity.id()));
                    return serviceTypeRepository.findById(entity.id());
                })
                .or(() -> Optional.of(serviceTypeRepository.save(new ServiceType(null, 0, context.mission(), service.name(), service.icon(), service.color(),
                        parseRoles(service.roles() != null ? service.roles().createRoles() : null),
                        parseRoles(service.roles() != null ? service.roles().readRoles() : null),
                        parseRoles(service.roles() != null ? service.roles().updateRoles() : null),
                        parseRoles(service.roles() != null ? service.roles().deleteRoles() : null),
                        null, null))))
                .map(this::toDTO)
                .orElseThrow();
    }

    private Set<String> parseRoles(String raw) {
        if (StringUtils.isAllBlank(raw)) {
            return Collections.emptySet();
        }
        return new LinkedHashSet<>(Arrays.asList(raw.split(",")));
    }

    private String parseRoles(Set<String> raw) {
        if (raw == null || raw.isEmpty()) {
            return null;
        }
        return raw.stream().map(String::trim).distinct().sorted().collect(Collectors.joining(","));
    }

    @Transactional
    public void deleteServiceType(TmsContext context, CUID id) {
        serviceTypeRepository.findByMissionIdAndId(context.mission(), id).ifPresent(serviceTypeRepository::delete);
    }

    @Transactional(readOnly = true)
    public List<StatusDTO> getStatuses(TmsContext context) {
        final List<StatusDTO> result = new ArrayList<>();
        statusRepository.findAllByMissionIdOrderByNameAsc(context.mission()).forEach(item -> result.add(toDTO(item)));
        return result;
    }

    @Transactional(readOnly = true)
    public Optional<StatusDTO> getStatus(TmsContext context, CUID id) {
        return statusRepository.findByMissionIdAndId(context.mission(), id).map(this::toDTO);
    }


    @Transactional
    public StatusDTO saveStatus(TmsContext context, StatusDTO status) {
        return Optional.ofNullable(status.id())
                .flatMap(id -> statusRepository.findByMissionIdAndId(context.mission(), id))
                .flatMap(entity -> {
                    jdbcTemplate.update("UPDATE incident_status SET name = ?, icon = ?, color = ?, mtime = CURRENT_TIMESTAMP, version = version + 1 WHERE version = ? AND mission_id = ? AND id = ?",
                            status.name(),
                            status.icon(),
                            status.color(),
                            status.version(),
                            cuid(context.mission()),
                            cuid(entity.id()));
                    return statusRepository.findById(entity.id());
                })
                .or(() -> Optional.of(statusRepository.save(new Status(null, 0, context.mission(), status.name(), status.icon(), status.color(), null, null))))
                .map(this::toDTO)
                .orElseThrow();
    }

    @Transactional
    public void deleteStatus(TmsContext context, CUID id) {
        statusRepository.findByMissionIdAndId(context.mission(), id).ifPresent(statusRepository::delete);
    }

    @Transactional(readOnly = true)
    public List<PriorityDTO> getPriorities(TmsContext context) {
        final List<PriorityDTO> result = new ArrayList<>();
        priorityRepository.findAllByMissionIdOrderByNameAsc(context.mission()).forEach(item -> result.add(toDTO(item)));
        return result;
    }

    @Transactional(readOnly = true)
    public Optional<PriorityDTO> getPriority(TmsContext context, CUID id) {
        return priorityRepository.findByMissionIdAndId(context.mission(), id).map(this::toDTO);
    }

    @Transactional
    public PriorityDTO savePriority(TmsContext context, PriorityDTO priority) {
        return Optional.ofNullable(priority.id())
                .flatMap(id -> priorityRepository.findByMissionIdAndId(context.mission(), id))
                .flatMap(entity -> {
                    jdbcTemplate.update("UPDATE incident_priority SET name = ?, icon = ?, color = ?, mtime = CURRENT_TIMESTAMP, version = version + 1 WHERE version = ? AND mission_id = ? AND id = ?",
                            priority.name(),
                            priority.icon(),
                            priority.color(),
                            priority.version(),
                            cuid(context.mission()),
                            cuid(entity.id()));
                    return priorityRepository.findById(entity.id());
                })
                .or(() -> Optional.of(priorityRepository.save(new Priority(null, 0, context.mission(), priority.name(), priority.icon(), priority.color(), null, null))))
                .map(this::toDTO)
                .orElseThrow();
    }

    @Transactional
    public void deletePriority(TmsContext context, CUID id) {
        priorityRepository.findByMissionIdAndId(context.mission(), id).ifPresent(priorityRepository::delete);
    }

    @Transactional(readOnly = true)
    public List<CommentDTO> getComments(TmsContext context, CUID id, UserDTO user) {
        return commentRepository.findByIncidentIdOrderByCtimeDesc(id)
                .stream()
                .map(this::toDTO)
                .toList();
    }

    @Transactional(readOnly = true)
    public Optional<CommentDTO> getComment(TmsContext context, CUID id, UserDTO user) {
        return commentRepository.findByIdAndMissionId(id, context.mission()).map(this::toDTO);
    }

    @Transactional
    public CommentDTO saveComment(TmsContext context, CUID id, CommentDTO comment, UserDTO user) {
        return Optional.ofNullable(comment.id())
                .flatMap(cid -> commentRepository.findByIdAndMissionId(cid, context.mission()))
                .map(entity -> commentRepository.save(new Comment(entity.id(), entity.version(), entity.incidentId(), entity.userId(), comment.text(), entity.ctime(), entity.mtime())))
                .or(() -> Optional.of(commentRepository.save(new Comment(null, 0, id, user.id(), comment.text(), null, null))))
                .map(this::toDTO)
                .orElseThrow();
    }

    @Transactional
    public void deleteComment(TmsContext context, CUID id) {
        commentRepository.findByIdAndMissionId(id, context.mission())
                .ifPresent(commentRepository::delete);
    }

    @Transactional(readOnly = true)
    public List<DashboardData> getDashboardData(TmsContext context) {
        return incidentRepository.findAllIncidentsGroupedByServiceId(context.mission());
    }

    public Incident mapIncident(CUID missionId, IncidentDTO dto, UserDTO user) {
        return new Incident(dto.id(), 0, missionId, dto.name(), dto.description(),
                dto.latitude(), dto.longitude(),
                dto.service().id(), dto.status().id(), dto.priority().id(),
                user.id(),
                dto.assignedTo() != null ? dto.assignedTo().id() : null,
                null, null);
    }

    @Transactional(readOnly = true)
    public IncidentDTO toDTO(TmsContext context, Incident incident) {
        final ServiceDTO service = getServiceType(context, incident.serviceId()).orElse(null);
        final StatusDTO status = getStatus(context, incident.statusId()).orElse(null);
        final PriorityDTO priority = getPriority(context, incident.priorityId()).orElse(null);
        final UserDTO createdBy = keycloakService.getUser(incident.createdBy()).orElse(null);
        final UserDTO assignedTo = Optional.ofNullable(incident.assignedTo()).flatMap(keycloakService::getUser).orElse(null);
        return new IncidentDTO(incident.id(), incident.version(), incident.name(), incident.description(), incident.latitude(), incident.longitude(), service, status, priority, incident.ctime(), createdBy, assignedTo);
    }

    public ServiceDTO toDTO(ServiceType type) {
        return new ServiceDTO(type.id(), type.version(), type.name(), type.icon(), type.color(), new Roles(parseRoles(type.createRoles()), parseRoles(type.readRoles()), parseRoles(type.updateRoles()), parseRoles(type.deleteRoles())));
    }

    public StatusDTO toDTO(Status status) {
        return new StatusDTO(status.id(), status.version(), status.name(), status.icon(), status.color());
    }

    public PriorityDTO toDTO(Priority priority) {
        return new PriorityDTO(priority.id(), priority.version(), priority.name(), priority.icon(), priority.color());
    }

    public CommentDTO toDTO(Comment comment) {
        final UserDTO user = keycloakService.getUser(comment.userId()).orElse(null);
        return new CommentDTO(comment.id(), comment.ctime(), user, comment.text());
    }
}
