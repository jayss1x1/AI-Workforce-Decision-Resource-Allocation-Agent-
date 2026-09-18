"""
Seed script: Populates realistic workforce data.
- 4 cities
- 30 employees (freshers, juniors, mid-level, seniors, leads across software and hardware)
- 5 realistic projects (Software and Hardware) with module dependencies
- Realistic historical performance snapshots, daily updates, approvals, skills
"""

from datetime import datetime, timedelta
import random
from sqlmodel import Session, select, SQLModel
from app.database import engine, init_db
from app.models import (
    Location, Skill, Employee, EmployeeSkill, Project, Module,
    DailyUpdate, Approval, AssessmentResult, PerformanceSnapshot,
    Config, EmployeeStatus, ProjectType, Priority, RiskLevel,
    ModuleStatus, SlaStatus, UpdateStatus
)
from app.config import settings

def seed_database(custom_engine=None):
    target_engine = custom_engine or engine
    SQLModel.metadata.create_all(target_engine)
    with Session(target_engine) as session:
        # Check if already seeded
        existing_emp = session.exec(select(Employee)).first()
        if existing_emp:
            print("Database already contains employees. Skipping seed.")
            return

        print("Seeding database...")

        # 1. Seed Config
        configs = [
            Config(key="WORKLOAD_BUFFER_RATIO", value="0.15", description="Mandatory free capacity buffer ratio (15%)"),
            Config(key="WEIGHT_TEST_RESULT", value="0.35", description="Performance score weight for technical assessments"),
            Config(key="WEIGHT_PAST_PROJECTS", value="0.20", description="Performance score weight for past project delivery"),
            Config(key="WEIGHT_DAILY_CONSISTENCY", value="0.15", description="Performance score weight for daily updates"),
            Config(key="WEIGHT_SLA_RECORD", value="0.15", description="Performance score weight for SLA adherence"),
            Config(key="WEIGHT_APPROVALS", value="0.10", description="Performance score weight for Team Lead approvals"),
            Config(key="WEIGHT_EXPERIENCE", value="0.05", description="Performance score weight for domain experience"),
        ]
        session.add_all(configs)

        # 2. Seed 4 Locations
        loc_sf = Location(city="San Francisco", country="USA", can_handle_hardware=True)
        loc_austin = Location(city="Austin", country="USA", can_handle_hardware=True)
        loc_ny = Location(city="New York", country="USA", can_handle_hardware=False)
        loc_seattle = Location(city="Seattle", country="USA", can_handle_hardware=False)
        session.add_all([loc_sf, loc_austin, loc_ny, loc_seattle])
        session.commit()

        # 3. Seed Skills
        software_skills = [
            Skill(name="Python & FastAPI", category="Software"),
            Skill(name="React & TypeScript", category="Software"),
            Skill(name="Distributed Systems", category="Software"),
            Skill(name="Machine Learning & Data", category="Software"),
            Skill(name="Cloud DevOps & CI/CD", category="Software"),
            Skill(name="Cyber Security & Auth", category="Software"),
        ]
        hardware_skills = [
            Skill(name="Embedded C / Firmware", category="Hardware"),
            Skill(name="PCB Design & KiCad", category="Hardware"),
            Skill(name="IoT Sensor Integration", category="Hardware"),
            Skill(name="RF Telemetry & Comms", category="Hardware"),
            Skill(name="FPGA / Verilog", category="Hardware"),
        ]
        all_skills = software_skills + hardware_skills
        session.add_all(all_skills)
        session.commit()

        # Helper mapping
        s_map = {s.name: s.id for s in all_skills}

        # 4. Seed 30 Employees
        # Levels: Fresher (<1y), Junior (1-2y), Mid (3-5y), Senior (6-9y), Lead (10+y)
        employees_data = [
            # Leads & Seniors (Software)
            ("Sarah Chen", "sarah.chen@company.com", "Team Lead", "Lead", 11.0, loc_sf.id, 40.0, 10.0, [("Python & FastAPI", 5), ("Distributed Systems", 5), ("Cyber Security & Auth", 4)]),
            ("Alex Rivera", "alex.rivera@company.com", "Principal Architect", "Lead", 12.5, loc_seattle.id, 40.0, 15.0, [("Distributed Systems", 5), ("Cloud DevOps & CI/CD", 5), ("Python & FastAPI", 4)]),
            ("Marcus Brody", "marcus.brody@company.com", "Senior Backend Engineer", "Senior", 8.0, loc_ny.id, 40.0, 12.0, [("Python & FastAPI", 5), ("Cloud DevOps & CI/CD", 4)]),
            ("Elena Rostova", "elena.rostova@company.com", "Senior Frontend Engineer", "Senior", 7.0, loc_sf.id, 40.0, 14.0, [("React & TypeScript", 5), ("Python & FastAPI", 3)]),
            ("Devon Lee", "devon.lee@company.com", "Staff ML Engineer", "Senior", 9.0, loc_seattle.id, 40.0, 12.0, [("Machine Learning & Data", 5), ("Python & FastAPI", 4)]),

            # Hardware Seniors & Leads
            ("Vikram Patel", "vikram.patel@company.com", "Hardware Lead", "Lead", 10.5, loc_austin.id, 40.0, 12.0, [("Embedded C / Firmware", 5), ("PCB Design & KiCad", 5), ("IoT Sensor Integration", 4)]),
            ("Rachel Adams", "rachel.adams@company.com", "Senior Hardware Engineer", "Senior", 7.5, loc_sf.id, 40.0, 10.0, [("PCB Design & KiCad", 5), ("RF Telemetry & Comms", 4)]),
            ("Kenji Sato", "kenji.sato@company.com", "Staff Firmware Engineer", "Senior", 8.5, loc_austin.id, 40.0, 14.0, [("Embedded C / Firmware", 5), ("FPGA / Verilog", 5)]),

            # Mid-Level Software Engineers
            ("Priya Sharma", "priya.sharma@company.com", "Backend Engineer", "Mid", 4.0, loc_sf.id, 40.0, 16.0, [("Python & FastAPI", 4), ("Distributed Systems", 3)]),
            ("Liam O'Connor", "liam.oconnor@company.com", "Fullstack Engineer", "Mid", 3.5, loc_ny.id, 40.0, 12.0, [("React & TypeScript", 4), ("Python & FastAPI", 4)]),
            ("Jessica Wu", "jessica.wu@company.com", "Cloud Engineer", "Mid", 4.5, loc_seattle.id, 40.0, 10.0, [("Cloud DevOps & CI/CD", 4), ("Cyber Security & Auth", 4)]),
            ("Carlos Mendez", "carlos.mendez@company.com", "Data Engineer", "Mid", 3.8, loc_sf.id, 40.0, 14.0, [("Machine Learning & Data", 4), ("Python & FastAPI", 4)]),
            ("Amina Idris", "amina.idris@company.com", "Security Engineer", "Mid", 4.0, loc_ny.id, 40.0, 12.0, [("Cyber Security & Auth", 4), ("Python & FastAPI", 3)]),

            # Mid-Level Hardware Engineers
            ("Tomislav Horvat", "tomislav.horvat@company.com", "Firmware Engineer", "Mid", 4.2, loc_austin.id, 40.0, 12.0, [("Embedded C / Firmware", 4), ("IoT Sensor Integration", 4)]),
            ("Chloe Bennett", "chloe.bennett@company.com", "Hardware Design Engineer", "Mid", 3.5, loc_sf.id, 40.0, 14.0, [("PCB Design & KiCad", 4), ("IoT Sensor Integration", 3)]),
            ("Daniel Novak", "daniel.novak@company.com", "RF Systems Engineer", "Mid", 4.8, loc_austin.id, 40.0, 10.0, [("RF Telemetry & Comms", 4), ("Embedded C / Firmware", 3)]),

            # Juniors (1-2 years)
            ("Zoe Martinez", "zoe.martinez@company.com", "Junior Software Engineer", "Junior", 1.8, loc_sf.id, 40.0, 8.0, [("Python & FastAPI", 3), ("React & TypeScript", 3)]),
            ("Hannah Green", "hannah.green@company.com", "Junior Frontend Engineer", "Junior", 1.5, loc_ny.id, 40.0, 10.0, [("React & TypeScript", 3)]),
            ("Tariq Al-Mansoor", "tariq.almansoor@company.com", "Junior Cloud Engineer", "Junior", 1.9, loc_seattle.id, 40.0, 8.0, [("Cloud DevOps & CI/CD", 3)]),
            ("Grace Kim", "grace.kim@company.com", "Junior Hardware Engineer", "Junior", 1.7, loc_austin.id, 40.0, 8.0, [("PCB Design & KiCad", 3), ("Embedded C / Firmware", 3)]),
            ("Leo Rossi", "leo.rossi@company.com", "Junior Systems Engineer", "Junior", 1.6, loc_sf.id, 40.0, 10.0, [("Embedded C / Firmware", 3), ("IoT Sensor Integration", 3)]),

            # Freshers (< 1 year experience)
            ("Maya Lin", "maya.lin@company.com", "Associate Software Engineer", "Fresher", 0.5, loc_sf.id, 40.0, 6.0, [("Python & FastAPI", 3), ("React & TypeScript", 2)]),
            ("Noah Taylor", "noah.taylor@company.com", "Associate Cloud Engineer", "Fresher", 0.7, loc_seattle.id, 40.0, 4.0, [("Cloud DevOps & CI/CD", 2), ("Python & FastAPI", 2)]),
            ("Sophia Dupont", "sophia.dupont@company.com", "Associate Frontend Engineer", "Fresher", 0.4, loc_ny.id, 40.0, 6.0, [("React & TypeScript", 3)]),
            ("Ethan Wright", "ethan.wright@company.com", "Associate Firmware Engineer", "Fresher", 0.6, loc_austin.id, 40.0, 4.0, [("Embedded C / Firmware", 2), ("IoT Sensor Integration", 2)]),
            ("Olivia Jackson", "olivia.jackson@company.com", "Associate ML Engineer", "Fresher", 0.8, loc_sf.id, 40.0, 6.0, [("Machine Learning & Data", 3), ("Python & FastAPI", 2)]),

            # Star Fresher (Unlocked harder work through top test scores)
            ("Lucas Vance", "lucas.vance@company.com", "Associate Software Engineer (Star)", "Fresher", 0.9, loc_ny.id, 40.0, 4.0, [("Python & FastAPI", 4), ("Distributed Systems", 3)]),

            # Dedicated Testing & Support Engineers
            ("Deepak Nair", "deepak.nair@company.com", "QA Automation Engineer", "Mid", 3.6, loc_seattle.id, 40.0, 8.0, [("Python & FastAPI", 4), ("Cloud DevOps & CI/CD", 3)]),
            ("Ananya Roy", "ananya.roy@company.com", "Hardware Lab Specialist", "Junior", 1.8, loc_austin.id, 40.0, 10.0, [("PCB Design & KiCad", 3), ("IoT Sensor Integration", 3)]),
            ("Felix Weber", "felix.weber@company.com", "Embedded Systems Specialist", "Mid", 4.1, loc_sf.id, 40.0, 8.0, [("Embedded C / Firmware", 4), ("FPGA / Verilog", 4)]),
        ]

        created_employees = []
        for name, email, role, level, y_exp, loc_id, cap, curr_w, skills_list in employees_data:
            emp = Employee(
                name=name,
                email=email,
                role=role,
                level=level,
                years_experience=y_exp,
                location_id=loc_id,
                weekly_capacity_hours=cap,
                current_workload_hours=curr_w,
                is_available=True,
                status=EmployeeStatus.ACTIVE.value
            )
            session.add(emp)
            session.commit()
            created_employees.append(emp)

            # Add EmployeeSkills
            for skill_name, prof in skills_list:
                es = EmployeeSkill(
                    employee_id=emp.id,
                    skill_id=s_map[skill_name],
                    proficiency=prof,
                    verified=True
                )
                session.add(es)

            # Historical assessment score baseline
            is_star = "Star" in role
            base_score = 92.0 if is_star else min(98.0, 70.0 + (y_exp * 2.5) + random.uniform(0, 8))
            test_res = AssessmentResult(
                assessment_id=1,
                employee_id=emp.id,
                mcq_score=round(base_score, 1),
                debug_score=round(base_score - 2, 1),
                programming_score=round(base_score + 1, 1),
                accuracy_score=round(base_score, 1),
                speed_score=round(base_score - 3, 1),
                total_score=round(base_score, 1),
                passed=True,
                graded_at=datetime.utcnow() - timedelta(days=14)
            )
            session.add(test_res)

            # Historical daily updates & approvals for realism
            for day_offset in range(1, 4):
                du = DailyUpdate(
                    module_id=1,
                    employee_id=emp.id,
                    date=datetime.utcnow() - timedelta(days=day_offset),
                    work_done=f"Routine tasks and code review for sprint {day_offset}.",
                    hours_spent=4.0,
                    blockers="None",
                    sla_status=SlaStatus.ON_TRACK.value,
                    consistency_score_delta=1.0,
                    status=UpdateStatus.APPROVED.value
                )
                session.add(du)
                session.commit()

                appr = Approval(
                    daily_update_id=du.id,
                    team_lead_id=created_employees[0].id,
                    approved=True,
                    comments="Good consistent progress."
                )
                session.add(appr)

            # Performance Snapshot
            perf_snap = PerformanceSnapshot(
                employee_id=emp.id,
                test_score=round(base_score, 1),
                past_projects_score=round(85.0 if is_star else min(95.0, 65.0 + y_exp * 3.0), 1),
                consistency_score=92.0,
                sla_record_score=95.0,
                approval_score=90.0,
                experience_score=min(100.0, round(y_exp * 10.0, 1)),
                overall_score=round(88.0 if is_star else min(96.0, 68.0 + y_exp * 2.8), 1),
                recorded_at=datetime.utcnow()
            )
            session.add(perf_snap)

        session.commit()

        # 5. Seed 5 Projects with Modules
        # Project 1: Apollo Cloud Gateway (Software, P1)
        p1 = Project(
            name="Apollo Cloud Gateway",
            description="Mission-critical cloud ingress routing with high throughput and zero-trust authentication.",
            project_type=ProjectType.SOFTWARE.value,
            priority=Priority.P1.value,
            status="Active",
            start_date=datetime.utcnow(),
            deadline=datetime.utcnow() + timedelta(days=30)
        )
        # Project 2: Titan Edge Sensor Hub (Hardware, P2)
        p2 = Project(
            name="Titan Edge Sensor Hub",
            description="Industrial IoT multi-sensor telemetry collection unit with ruggedized PCB and RF link.",
            project_type=ProjectType.HARDWARE.value,
            priority=Priority.P2.value,
            status="Active",
            start_date=datetime.utcnow(),
            deadline=datetime.utcnow() + timedelta(days=45)
        )
        # Project 3: Chronos Analytics Engine (Software, P2)
        p3 = Project(
            name="Chronos Analytics Engine",
            description="Real-time aggregation pipeline and interactive metric visualizer.",
            project_type=ProjectType.SOFTWARE.value,
            priority=Priority.P2.value,
            status="Active",
            start_date=datetime.utcnow(),
            deadline=datetime.utcnow() + timedelta(days=25)
        )
        # Project 4: Zephyr Drone Controller (Hardware, P1)
        p4 = Project(
            name="Zephyr Drone Controller",
            description="High-precision autonomous aerial flight controller with real-time stabilization firmware.",
            project_type=ProjectType.HARDWARE.value,
            priority=Priority.P1.value,
            status="Active",
            start_date=datetime.utcnow(),
            deadline=datetime.utcnow() + timedelta(days=60)
        )
        # Project 5: Helios Internal Ops Portal (Software, P3)
        p5 = Project(
            name="Helios Internal Ops Portal",
            description="Internal employee administration, staffing board, and weekly resource reporting.",
            project_type=ProjectType.SOFTWARE.value,
            priority=Priority.P3.value,
            status="Active",
            start_date=datetime.utcnow(),
            deadline=datetime.utcnow() + timedelta(days=15)
        )
        session.add_all([p1, p2, p3, p4, p5])
        session.commit()

        # Add Modules with dependencies
        # P1: Apollo Cloud Gateway Modules
        m_auth = Module(
            project_id=p1.id,
            name="Zero-Trust Authentication Engine",
            description="OAuth2/OIDC token verification and RBAC permission enforcement service.",
            required_skill_id=s_map["Cyber Security & Auth"],
            complexity=RiskLevel.HIGH.value,
            risk_level=RiskLevel.HIGH.value,
            estimated_hours=18.0,
            priority=Priority.P1.value,
            is_urgent=True,
            deadline=datetime.utcnow() + timedelta(days=12)
        )
        session.add(m_auth)
        session.commit()

        m_pipeline = Module(
            project_id=p1.id,
            name="High-Throughput Stream Router",
            description="Asynchronous packet ingestion with backpressure management.",
            required_skill_id=s_map["Distributed Systems"],
            complexity=RiskLevel.HIGH.value,
            risk_level=RiskLevel.HIGH.value,
            estimated_hours=20.0,
            priority=Priority.P1.value,
            is_urgent=True,
            dependency_module_id=m_auth.id,  # Stream router depends on Auth
            deadline=datetime.utcnow() + timedelta(days=20)
        )
        session.add(m_pipeline)

        m_fastapi = Module(
            project_id=p1.id,
            name="Gateway API Orchestrator",
            description="REST & GraphQL endpoint dispatch and proxy service layer.",
            required_skill_id=s_map["Python & FastAPI"],
            complexity=RiskLevel.MEDIUM.value,
            risk_level=RiskLevel.MEDIUM.value,
            estimated_hours=14.0,
            priority=Priority.P1.value,
            deadline=datetime.utcnow() + timedelta(days=22)
        )
        session.add(m_fastapi)

        # P2: Titan Edge Sensor Hub Modules (Hardware)
        m_pcb = Module(
            project_id=p2.id,
            name="Sensor Board PCB Layout",
            description="Schematic design, trace routing, and EMI shielding for 8-layer board.",
            required_skill_id=s_map["PCB Design & KiCad"],
            complexity=RiskLevel.MEDIUM.value,
            risk_level=RiskLevel.MEDIUM.value,
            estimated_hours=16.0,
            priority=Priority.P2.value,
            location_requirement_id=loc_austin.id,  # Austin Hardware lab
            deadline=datetime.utcnow() + timedelta(days=30)
        )
        session.add(m_pcb)
        session.commit()

        m_firmware = Module(
            project_id=p2.id,
            name="Low-Power Sensor Firmware",
            description="Interrupt-driven sensor sampling and sleep-state battery conservation.",
            required_skill_id=s_map["Embedded C / Firmware"],
            complexity=RiskLevel.MEDIUM.value,
            risk_level=RiskLevel.MEDIUM.value,
            estimated_hours=18.0,
            priority=Priority.P2.value,
            dependency_module_id=m_pcb.id,  # Firmware needs PCB specs
            location_requirement_id=loc_austin.id,
            deadline=datetime.utcnow() + timedelta(days=35)
        )
        session.add(m_firmware)

        # P3: Chronos Analytics Engine Modules
        m_chronos_ui = Module(
            project_id=p3.id,
            name="Realtime Metric Canvas UI",
            description="Dynamic chart dashboard with responsive live metric streaming.",
            required_skill_id=s_map["React & TypeScript"],
            complexity=RiskLevel.LOW.value,
            risk_level=RiskLevel.LOW.value,
            estimated_hours=12.0,
            priority=Priority.P2.value,
            deadline=datetime.utcnow() + timedelta(days=18)
        )
        session.add(m_chronos_ui)

        # P4: Zephyr Drone Controller (P1 Hardware)
        m_drone_rf = Module(
            project_id=p4.id,
            name="RF Long-Range Telemetry Link",
            description="Ultra-reliable 915MHz telemetry link with frequency hopping.",
            required_skill_id=s_map["RF Telemetry & Comms"],
            complexity=RiskLevel.HIGH.value,
            risk_level=RiskLevel.HIGH.value,
            estimated_hours=16.0,
            priority=Priority.P1.value,
            location_requirement_id=loc_sf.id,  # SF Hardware lab
            deadline=datetime.utcnow() + timedelta(days=40)
        )
        session.add(m_drone_rf)

        # P5: Helios Ops (P3 Software - Low risk for freshers)
        m_ops_reports = Module(
            project_id=p5.id,
            name="Automated Shift Report Exporter",
            description="Generates daily markdown and PDF activity digests.",
            required_skill_id=s_map["Python & FastAPI"],
            complexity=RiskLevel.LOW.value,
            risk_level=RiskLevel.LOW.value,
            estimated_hours=8.0,
            priority=Priority.P3.value,
            deadline=datetime.utcnow() + timedelta(days=10)
        )
        session.add(m_ops_reports)

        session.commit()
        print("Seed completed successfully! 30 employees, 4 locations, 11 skills, 5 projects initialized.")

if __name__ == "__main__":
    seed_database()
