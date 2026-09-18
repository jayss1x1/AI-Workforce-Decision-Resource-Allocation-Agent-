"""
Streamlit Application: AI Workforce Allocation Agent
Provides interactive portals for:
- Manager: Project Decompositions, Capacity Tracking, Emergency Leave Trigger, Task Urgency Escalation
- Team Lead: Reassignment Request Decisions, Team Workload Tracking
- Employee: Assigned Modules with "Why this person?" Justifications, Reassignment Requests, Daily Updates with Gemini Blocker Analysis, Skills Assessment
- Sent Emails: Mock Mailer Audit Trail
"""

import streamlit as st
from datetime import datetime
from sqlmodel import Session, select
import json
import pandas as pd

from app.database import engine
from app.models import (
    Employee, Skill, EmployeeSkill, Location, Project, Module,
    Assignment, Assessment, AssessmentResult, DailyUpdate, Approval,
    LeaveRecord, PerformanceSnapshot, AllocationEvent, ReassignmentRequest,
    HandoverPacket, Notification, Email, Config,
    EmployeeStatus, Priority, RiskLevel, ModuleStatus
)
from app.services.scorer import compute_performance_score
from app.services.cpsat_allocator import run_cp_sat_allocation
from app.services.agent_loop import (
    trigger_adaptive_allocation,
    apply_leave_and_reallocate,
    escalate_task_urgency,
    handle_reassignment_request,
    refresh_employee_workloads
)
from app.services.gemini_service import (
    classify_and_decompose_project,
    generate_assessment,
    grade_assessment,
    analyze_daily_update
)

st.set_page_config(
    page_title="AI Workforce Allocation Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🤖 AI Workforce Allocation Agent")
st.markdown("Autonomous workforce optimization engine powered by **Google OR-Tools CP-SAT** and **Gemini AI**.")

# Sidebar Navigation
st.sidebar.header("Navigation")
role = st.sidebar.selectbox(
    "Select Portal View",
    ["Executive Overview", "Manager Portal", "Team Lead Portal", "Employee Workspace", "Mock Mailer (Sent Emails)", "Audit Trace Log"]
)

with Session(engine) as session:
    # Refresh workloads
    refresh_employee_workloads(session)

    if role == "Executive Overview":
        st.subheader("📊 System Dashboard & Capacity Overview")

        employees = session.exec(select(Employee)).all()
        modules = session.exec(select(Module)).all()
        projects = session.exec(select(Project)).all()
        emails = session.exec(select(Email)).all()
        events = session.exec(select(AllocationEvent)).all()
        pending_requests = session.exec(select(ReassignmentRequest).where(ReassignmentRequest.status == "Pending")).all()

        active_emps = [e for e in employees if e.status == EmployeeStatus.ACTIVE.value and e.is_available]
        on_leave_emps = [e for e in employees if e.status == EmployeeStatus.ON_LEAVE.value or not e.is_available]
        unassigned_mods = [m for m in modules if m.status == ModuleStatus.UNASSIGNED.value]
        assigned_mods = [m for m in modules if m.status in (ModuleStatus.ASSIGNED.value, ModuleStatus.IN_PROGRESS.value)]

        total_buffered_cap = sum(e.weekly_capacity_hours * 0.85 for e in active_emps)
        total_used_workload = sum(e.current_workload_hours for e in active_emps)
        util_pct = (total_used_workload / max(1.0, total_buffered_cap)) * 100

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Active Engineers", len(active_emps), f"{len(on_leave_emps)} on leave")
        col2.metric("Active Projects", len(projects))
        col3.metric("Assigned Tasks", len(assigned_mods), f"{len(unassigned_mods)} unassigned")
        col4.metric("Capacity Buffer", f"{round(util_pct, 1)}%", "Target < 85%")
        col5.metric("Pending Reassignments", len(pending_requests))

        st.divider()

        # Action Trigger
        c_act1, c_act2 = st.columns([2, 1])
        with c_act1:
            st.info("The agent runs autonomous allocation sweeps periodically via APScheduler. You can also trigger an immediate sweep below:")
        with c_act2:
            if st.button("⚡ Run Adaptive Allocation Sweep", type="primary", use_container_width=True):
                with st.spinner("Solving constraint satisfaction model with CP-SAT..."):
                    res = trigger_adaptive_allocation(session, trigger_event="STREAMLIT_UI_TRIGGER")
                    st.success(f"Sweep completed! Status: {res.get('status')}. Assignments made: {res.get('assignments_made')}")
                    st.rerun()

        st.subheader("👥 Workforce Roster & Buffer Adherence")
        emp_data = []
        for e in employees:
            scores = compute_performance_score(session, e.id, persist_snapshot=False)
            emp_data.append({
                "ID": e.id,
                "Name": e.name,
                "Role / Level": e.level,
                "Years Exp": e.years_experience,
                "Status": e.status,
                "Available": "✅ Yes" if e.is_available else "❌ No",
                "Workload (hrs)": e.current_workload_hours,
                "Buffer Limit (85%)": round(e.weekly_capacity_hours * 0.85, 1),
                "Capacity (hrs)": e.weekly_capacity_hours,
                "Perf Score": round(scores["overall_score"], 1),
                "Test Score": round(scores["test_score"], 1)
            })
        st.dataframe(pd.DataFrame(emp_data), use_container_width=True)

    elif role == "Manager Portal":
        st.subheader("🛠️ Manager Control Center")
        tab1, tab2, tab3 = st.tabs(["AI Project Decomposition", "Emergency Leave & Reallocation", "Escalate Task Urgency"])

        with tab1:
            st.markdown("### 🤖 Autonomous Project Decomposer (Gemini AI)")
            st.caption("Classifies project type (Software vs Hardware) and decomposes requirements into constrained modules.")
            
            p_name = st.text_input("Project Name", value="Edge Telemetry Gateway")
            p_desc = st.text_area(
                "Project Description & Functional Goals",
                value="Design and build an embedded high-speed edge telemetry gateway with custom PCB, SPI accelerometer driver, and cloud event streaming backend."
            )

            if st.button("🚀 Decompose with Gemini", type="primary"):
                with st.spinner("Classifying architecture and generating module dependencies..."):
                    decomp = classify_and_decompose_project(session, p_name, p_desc)
                    st.success(f"Classified as: **{decomp.project_type}** (Confidence: {decomp.confidence:.2f})")
                    st.markdown(f"**Architecture Summary:** {decomp.architecture_summary}")
                    
                    st.markdown("#### Generated Work Breakdown Modules:")
                    mod_df = pd.DataFrame(decomp.modules)
                    st.dataframe(mod_df, use_container_width=True)

        with tab2:
            st.markdown("### 🏥 Employee Emergency Leave")
            st.caption("Marks an employee on leave, vacates their assignments, and automatically finds qualified replacements via CP-SAT.")

            active_emps = session.exec(select(Employee).where(Employee.status == EmployeeStatus.ACTIVE.value)).all()
            emp_opts = {f"{e.name} (ID: {e.id}, {e.level})": e.id for e in active_emps}
            
            if emp_opts:
                selected_label = st.selectbox("Select Employee", list(emp_opts.keys()))
                sel_emp_id = emp_opts[selected_label]
                leave_type = st.selectbox("Leave Type", ["Medical / Sick Leave", "Family Emergency", "Sudden Resignation", "Vacation"])
                leave_reason = st.text_input("Reason for Leave", value="Sudden surgery and recovery")

                if st.button("🚨 Apply Leave & Trigger Immediate Reallocation", type="primary"):
                    with st.spinner("Vacating tasks and searching for qualified replacements..."):
                        leave_res = apply_leave_and_reallocate(
                            session=session,
                            employee_id=sel_emp_id,
                            leave_type=leave_type,
                            reason=leave_reason
                        )
                        st.success(f"Leave applied! Vacated {leave_res['displaced_count']} module(s).")
                        st.json(leave_res["reallocation_summary"])
                        st.rerun()
            else:
                st.info("No active employees found.")

        with tab3:
            st.markdown("### ⚡ Task Urgency Escalation")
            st.caption("Escalates a task to P1 Priority. The agent immediately prioritizes top-performing engineers.")

            modules = session.exec(select(Module)).all()
            mod_opts = {f"{m.name} (ID: {m.id}, Priority: {m.priority}, Status: {m.status})": m.id for m in modules}
            
            if mod_opts:
                sel_mod_label = st.selectbox("Select Task to Escalate", list(mod_opts.keys()))
                sel_mod_id = mod_opts[sel_mod_label]
                new_priority = st.selectbox("New Priority", [Priority.P1.value, Priority.P2.value, Priority.P3.value], index=0)
                is_urgent = st.checkbox("Mark Urgent Flag", value=True)

                if st.button("⚡ Escalate Task & Rebalance", type="primary"):
                    with st.spinner("Escalating and running allocation solver..."):
                        esc_res = escalate_task_urgency(
                            session=session,
                            module_id=sel_mod_id,
                            is_urgent=is_urgent,
                            priority=new_priority
                        )
                        st.success(f"Task {sel_mod_id} escalated to {new_priority}! Solver result:")
                        st.json(esc_res["reallocation_result"])
                        st.rerun()

    elif role == "Team Lead Portal":
        st.subheader("👔 Team Lead Portal")
        st.markdown("### 📋 Review Task Reassignment Requests")
        st.caption("When an engineer requests reassignment, Team Leads can review their reason and approve reallocation.")

        requests = session.exec(select(ReassignmentRequest).where(ReassignmentRequest.status == "Pending")).all()

        if not requests:
            st.success("No pending reassignment requests. All tasks are progressing smoothly!")
        else:
            for req in requests:
                assignment = session.get(Assignment, req.assignment_id)
                emp = session.get(Employee, req.employee_id)
                mod = session.get(Module, assignment.module_id) if assignment else None

                with st.expander(f"Request #{req.id}: {emp.name if emp else 'Employee'} on '{mod.name if mod else 'Module'}'", expanded=True):
                    st.write(f"**Submitted by:** {emp.name if emp else 'Unknown'} ({emp.level if emp else ''})")
                    st.write(f"**Module:** {mod.name if mod else 'Unknown'} (Priority: {mod.priority if mod else ''})")
                    st.write(f"**Reason for Reassignment:** {req.reason}")
                    st.write(f"**Timestamp:** {req.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")

                    notes = st.text_input("Decision Notes", key=f"notes_{req.id}", value="Approved. Reassigning to alternative engineer.")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Approve Reassignment", key=f"app_{req.id}", type="primary"):
                            res = handle_reassignment_request(session, req.id, action="Approve", manager_notes=notes)
                            st.success("Request approved! Vacated module reassigned.")
                            st.rerun()
                    with c2:
                        if st.button("❌ Reject Request", key=f"rej_{req.id}"):
                            res = handle_reassignment_request(session, req.id, action="Reject", manager_notes=notes)
                            st.warning("Request rejected.")
                            st.rerun()

    elif role == "Employee Workspace":
        st.subheader("💼 Employee Workspace")

        employees = session.exec(select(Employee).where(Employee.status == EmployeeStatus.ACTIVE.value)).all()
        emp_map = {f"{e.name} (Level: {e.level})": e for e in employees}
        selected_emp_label = st.selectbox("Switch Active Employee Profile", list(emp_map.keys()))
        current_emp = emp_map[selected_emp_label]

        tab_e1, tab_e2, tab_e3 = st.tabs(["My Tasks & Explanations", "Daily Standup Update", "Technical Skills Assessment"])

        with tab_e1:
            st.markdown(f"### Current Assignments for {current_emp.name}")
            my_modules = session.exec(select(Module).where(Module.owner_id == current_emp.id)).all()

            if not my_modules:
                st.info("You currently have no active assignments. Enjoy the buffer capacity!")
            else:
                for m in my_modules:
                    assignment = session.exec(
                        select(Assignment).where(Assignment.module_id == m.id, Assignment.employee_id == current_emp.id)
                    ).first()

                    with st.container(border=True):
                        st.markdown(f"#### 📌 {m.name} ({m.priority})")
                        st.markdown(f"**Description:** {m.description}")
                        st.markdown(f"**Estimated Hours:** {m.estimated_hours}h | **Deadline:** {m.deadline.strftime('%Y-%m-%d') if m.deadline else 'Flexible'}")

                        if assignment and assignment.explanation:
                            st.info(f"💡 **AI Allocation Justification:**\n\n{assignment.explanation}")

                        # Option to request reassignment
                        with st.expander("⚠️ Request Reassignment"):
                            reassign_reason = st.text_area("Justification for Reassignment (Mandatory)", key=f"reason_{m.id}")
                            if st.button("Submit Reassignment Request", key=f"btn_reassign_{m.id}"):
                                if not reassign_reason.strip():
                                    st.error("Please provide a reason.")
                                else:
                                    req = ReassignmentRequest(
                                        assignment_id=assignment.id if assignment else 1,
                                        employee_id=current_emp.id,
                                        reason=reassign_reason,
                                        status="Pending"
                                    )
                                    session.add(req)
                                    session.commit()
                                    st.success("Reassignment request submitted for Team Lead review!")
                                    st.rerun()

        with tab_e2:
            st.markdown("### 📝 Daily Standup Update (AI Risk Analysis)")
            st.caption("Submit your daily progress. Gemini analyzes your update to detect hidden risks and blockers.")

            if not my_modules:
                st.info("You need active tasks to submit a daily update.")
            else:
                sel_task = st.selectbox("Select Task", [m.name for m in my_modules])
                target_mod = next(m for m in my_modules if m.name == sel_task)
                target_assignment = session.exec(
                    select(Assignment).where(Assignment.module_id == target_mod.id)
                ).first()

                hours = st.number_input("Hours Spent Today", min_value=0.5, max_value=12.0, value=4.0, step=0.5)
                work_done = st.text_area("What did you accomplish today?", value="Implemented core module components and completed initial unit tests.")
                blockers = st.text_area("Any blockers, uncertainties, or dependencies?", value="None at this stage.")

                if st.button("Submit Daily Update & Analyze", type="primary"):
                    with st.spinner("Analyzing with Gemini AI..."):
                        analysis = analyze_daily_update(
                            session=session,
                            assignment_id=target_assignment.id if target_assignment else 1,
                            hours_spent=hours,
                            work_done=work_done,
                            blockers=blockers
                        )
                        st.success("Update submitted!")
                        st.markdown(f"**AI Risk Assessment:** `{analysis['risk_level']}`")
                        st.write(analysis["summary"])

        with tab_e3:
            st.markdown("### 🧪 Technical Assessment & Code Runner")
            st.caption("Take a real-time skills assessment. Your Python code is executed in an isolated sandbox with strict timeouts.")

            emp_skills = session.exec(select(EmployeeSkill).where(EmployeeSkill.employee_id == current_emp.id)).all()
            skills = {s.id: s.name for s in session.exec(select(Skill)).all()}
            
            if emp_skills:
                skill_choices = {skills.get(es.skill_id, "Skill"): es.skill_id for es in emp_skills}
                sel_skill_name = st.selectbox("Select Skill to Test", list(skill_choices.keys()))
                
                if st.button("🎯 Generate Assessment Challenge"):
                    with st.spinner("Generating technical assessment challenge..."):
                        test_spec = generate_assessment(session, skill_name=sel_skill_name, target_role=f"{current_emp.level} Engineer")
                        st.session_state["current_assessment"] = test_spec

                if "current_assessment" in st.session_state:
                    ass = st.session_state["current_assessment"]
                    st.markdown(f"#### 📄 {ass['title']}")
                    st.markdown(ass["problem_statement"])
                    st.code(ass["starter_code"], language="python")

                    submitted_code = st.text_area("Your Python Solution Code", value=ass["starter_code"], height=250)

                    if st.button("▶️ Run & Grade Assessment", type="primary"):
                        with st.spinner("Executing solution against test harness with timeout..."):
                            grading = grade_assessment(
                                session=session,
                                assessment_id=ass["id"],
                                employee_id=current_emp.id,
                                submitted_code=submitted_code
                            )
                            st.markdown(f"### Score: **{grading['score']}/100** ({'PASSED ✅' if grading['passed'] else 'NEEDS IMPROVEMENT ⚠️'})")
                            st.write(grading["feedback"])
                            with st.expander("View Raw Test Execution Output"):
                                st.code(grading.get("stdout") or "No output")

    elif role == "Mock Mailer (Sent Emails)":
        st.subheader("📬 Sent Emails (Mock Mailer Outbox)")
        st.caption("Auditable log of all automated notification emails generated by the AI Workforce Allocation Agent.")

        emails = session.exec(select(Email).order_by(Email.sent_at.desc())).all()
        if not emails:
            st.info("No emails sent yet.")
        else:
            st.markdown(f"**Total Dispatched Emails:** {len(emails)}")
            for em in emails:
                with st.expander(f"✉️ [{em.sent_at.strftime('%Y-%m-%d %H:%M:%S')}] To: {em.to_email} — {em.subject}", expanded=False):
                    st.write(f"**From:** {em.from_email}")
                    st.write(f"**To:** {em.to_email}")
                    st.write(f"**Subject:** {em.subject}")
                    st.divider()
                    st.markdown(em.body)

    elif role == "Audit Trace Log":
        st.subheader("📜 Autonomous Allocation Audit Trace")
        st.caption("Chronological ledger of all agent events, reasonings, and state mutations.")

        events = session.exec(select(AllocationEvent).order_by(AllocationEvent.created_at.desc()).limit(100)).all()
        if not events:
            st.info("No events logged.")
        else:
            ev_data = []
            for ev in events:
                ev_data.append({
                    "Timestamp": ev.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    "Event Type": ev.event_type,
                    "Module ID": ev.module_id,
                    "Old Employee ID": ev.old_employee_id,
                    "New Employee ID": ev.new_employee_id,
                    "Reason / Justification": ev.reason
                })
            st.dataframe(pd.DataFrame(ev_data), use_container_width=True)
