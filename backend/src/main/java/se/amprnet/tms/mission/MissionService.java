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

package se.amprnet.tms.mission;

import io.github.thibaultmeyer.cuid.CUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import se.amprnet.tms.data.*;
import se.amprnet.tms.keycloak.KeycloakAdminService;
import se.amprnet.tms.model.MissionDTO;
import se.amprnet.tms.model.MissionMemberDTO;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

@Service
public class MissionService {

    private final MissionRepository missionRepository;
    private final MissionMemberRepository memberRepository;
    private final ServiceTypeRepository serviceTypeRepository;
    private final StatusRepository statusRepository;
    private final PriorityRepository priorityRepository;
    private final KeycloakAdminService keycloakService;

    public MissionService(MissionRepository missionRepository,
                          MissionMemberRepository memberRepository,
                          ServiceTypeRepository serviceTypeRepository,
                          StatusRepository statusRepository,
                          PriorityRepository priorityRepository,
                          KeycloakAdminService keycloakService) {
        this.missionRepository = missionRepository;
        this.memberRepository = memberRepository;
        this.serviceTypeRepository = serviceTypeRepository;
        this.statusRepository = statusRepository;
        this.priorityRepository = priorityRepository;
        this.keycloakService = keycloakService;
    }

    @Transactional(readOnly = true)
    public List<MissionDTO> getMissions(MissionStatus status) {
        final List<MissionDTO> result = new ArrayList<>();
        if (status != null) {
            missionRepository.findAllByStatusOrderByNameAsc(status.name()).forEach(p -> result.add(toDTO(p)));
        } else {
            missionRepository.findAllByOrderByNameAsc().forEach(p -> result.add(toDTO(p)));
        }
        return result;
    }

    @Transactional(readOnly = true)
    public Optional<MissionDTO> getMission(CUID id) {
        return missionRepository.findById(id)
                .map(this::toDTO);
    }

    @Transactional
    public MissionDTO createMission(MissionDTO mission) {
        return toDTO(bootstrap(missionRepository.save(new Mission(null, 0, mission.name(), mission.description(),
                mission.status() != null ? mission.status().name() : MissionStatus.ACTIVE.name(),
                mission.icon(), mission.color(), null, null))));
    }

    @Transactional
    public Optional<MissionDTO> updateMission(CUID id, MissionDTO mission) {
        return missionRepository.findById(id)
                .map(entity -> new Mission(entity.id(), entity.version(),
                        mission.name() != null ? mission.name() : entity.name(), mission.description(),
                        mission.status() != null ? mission.status().name() : entity.status(),
                        mission.icon(), mission.color(), entity.ctime(), null))
                .map(missionRepository::save)
                .map(this::toDTO);
    }

    @Transactional
    public Optional<MissionDTO> deleteMission(CUID id) {
        return missionRepository.findById(id)
                .map(entity -> {
                    missionRepository.delete(entity);
                    return toDTO(entity);
                });
    }

    private MissionDTO toDTO(Mission mission) {
        return new MissionDTO(mission.id(), mission.version(), mission.name(), mission.description(), MissionStatus.valueOf(mission.status()), mission.icon(), mission.color());
    }

    private MissionMemberDTO toDTO(MissionMember entity) {
        return keycloakService.getUser(entity.sub())
                .map(user -> new MissionMemberDTO(user.id(), user.firstName(), user.lastName(), user.email(), entity.role()))
                .orElseGet(() -> new MissionMemberDTO(entity.sub(), "", "", "", entity.role()));
    }

    @Transactional
    public Mission bootstrap(Mission mission) {
        final CUID missionId = mission.id();

        final List<ServiceType> serviceTypes = new ArrayList<>();
        serviceTypes.add(ServiceType.of(missionId, "Ledning", "mdi-account", null));
        serviceTypes.add(ServiceType.of(missionId, "Samband", "mdi-phone-classic", null));
        serviceTypes.add(ServiceType.of(missionId, "Sjukvård", "mdi-ambulance", null));
        serviceTypes.add(ServiceType.of(missionId, "Transport", "mdi-car", null));
        serviceTypes.add(ServiceType.of(missionId, "Dricksvatten", "mdi-water", null));
        serviceTypes.add(ServiceType.of(missionId, "Mat", "mdi-silverware-fork-knife", null));
        serviceTypes.add(ServiceType.of(missionId, "Snöröjning", "mdi-snowflake", null));
        serviceTypes.add(ServiceType.of(missionId, "Räddningstjänst", "mdi-fire", null));
        serviceTypes.add(ServiceType.of(missionId, "Reservkraft", "mdi-battery-60", null));
        for (ServiceType serviceType : serviceTypes) {
            if (serviceTypeRepository.findByMissionIdAndName(missionId, serviceType.name()).isEmpty()) {
                serviceTypeRepository.save(serviceType);
            }
        }

        final List<Status> statuses = new ArrayList<>();
        statuses.add(Status.of(missionId, "Ny", "mdi-alert", "#AA0000"));
        statuses.add(Status.of(missionId, "Behandlas", "mdi-account", "#0000AA"));
        statuses.add(Status.of(missionId, "Klar", "mdi-check-bold", "#00AA00"));
        for (Status status : statuses) {
            if (statusRepository.findByMissionIdAndName(missionId, status.name()).isEmpty()) {
                statusRepository.save(status);
            }
        }

        final List<Priority> priorities = new ArrayList<>();
        priorities.add(Priority.of(missionId, "Hög", "mdi-arrow-up-bold-box", "#AA0000"));
        priorities.add(Priority.of(missionId, "Normal", "mdi-arrow-right-bold-box", "#0000AA"));
        priorities.add(Priority.of(missionId, "Låg", "mdi-arrow-down-bold-box", "#00AA00"));
        for (Priority priority : priorities) {
            if (priorityRepository.findByMissionIdAndName(missionId, priority.name()).isEmpty()) {
                priorityRepository.save(priority);
            }
        }

        return mission;
    }

    @Transactional(readOnly = true)
    public List<MissionMemberDTO> getMissionMembers(CUID id) {
        return memberRepository.findByMissionIdOrderByCtime(id)
                .stream()
                .flatMap(entity -> keycloakService.getUser(entity.sub())
                        .stream()
                        .map(user -> new MissionMemberDTO(entity.sub(), user.firstName(), user.lastName(), user.email(), entity.role())))
                .toList();
    }

    @Transactional
    public Optional<MissionMemberDTO> saveMissionMember(CUID id, MissionMemberDTO member) {
        return missionRepository.findById(id)
                .map(mission -> {
                    final MissionMember entity = memberRepository.findByMissionIdAndSub(mission.id(), member.id())
                            .map(existing -> new MissionMember(existing.id(), existing.version(), mission.id(), existing.sub(), member.role(), existing.ctime(), existing.mtime()))
                            .orElseGet(() -> new MissionMember(null, 0, mission.id(), member.id(), member.role(), null, null));
                    return memberRepository.save(entity);
                })
                .map(this::toDTO);
    }

    @Transactional
    public Optional<MissionMemberDTO> deleteMissionMember(CUID id, CUID userId) {
        return missionRepository.findById(id)
                .flatMap(mission -> memberRepository.findById(userId))
                .filter(entity -> entity.missionId().equals(id))
                .map(entity -> {
                    final MissionMemberDTO tombstone = toDTO(entity);
                    memberRepository.delete(entity);
                    return tombstone;
                });
    }

    @Transactional(readOnly = true)
    public List<MissionDTO> getMemberMissions(String sub) {
        return memberRepository.findBySub(sub)
                .stream()
                .map(MissionMember::missionId)
                .flatMap(id -> missionRepository.findById(id).stream())
                .map(this::toDTO)
                .toList();
    }
}
