# AI Workforce Allocation Agent

An adaptive, multi-agent AI workforce task allocation and continuous dynamic reallocation engine powered by **FastAPI**, **SQLModel**, **SQLite**, **Google OR-Tools (CP-SAT)**, **Streamlit**, and **Gemini 2.5 Flash**.

---

## Setup in 5 Commands or Fewer

```bash
# 1. Clone & enter repository
git clone <repo-url> && cd workforce-agent

# 2. Configure environment
cp .env.example .env

# 3. Install dependencies
pip install -r requirements.txt

# 4. Seed initial workforce & project database
python seed.py

# 5. Run test suite or launch application
pytest tests/ -v
# streamlit run ui/app.py --server.port=8501
```

---

## System Architecture

```mermaid
flowchart TD
    subgraph UI ["User Interface (Streamlit)"]
        M[Manager Portal]
        TL[Team Lead Portal]
        E[Employee Portal]
        SE[Simulate Event Panel]
        EM[Sent Emails Page]
    end

    subgraph Agent ["Agent Core (Observe - Think - Act - Reflect - Log)"]
        Trace[(AgentTrace Feed)]
        Loop[Agent ReAct Loop]
        Gemini[Gemini 2.5 Flash]
    end

    subgraph Tools ["Agent Tool Registry"]
        T1[classify_and_decompose_project]
        T2[shortlist_employees]
        T3[generate_assessment]
        T4[grade_assessment & code_runner]
        T5[compute_performance_score]
        T6[run_allocation: Google OR-Tools CP-SAT]
        T7[send_assignment_email]
        T8[analyze_daily_update]
        T9[create_handover_packet]
        T10[reallocate_after_event]
        T11[escalate]
        T12[notify]
    end

    subgraph Storage ["Persistent State (SQLite + SQLModel)"]
        DB[(workforce.db)]
        DB_Emp[30 Employees / 4 Cities]
        DB_Proj[5 Projects / Modules]
        DB_Audit[AllocationEvent Audit]
    end

    M & TL & E & SE --> Loop
    Loop <--> Gemini
    Loop --> Trace
    Loop --> Tools
    Tools --> T6
    T6 --> DB
    Tools <--> Storage
    Tools --> EM
```

---

## Database Tables (20 Models)

1. **Employee**: Core workforce members with roles, experience, city location, availability, and capacity.
2. **Skill**: Technical skills categorized into Software and Hardware.
3. **EmployeeSkill**: Verified proficiency (1-5) linking employee to skills.
4. **Location**: Physical hubs (San Francisco, Austin, New York, Seattle) with hardware lab indicators.
5. **Project**: Software and Hardware projects with P1-P4 priorities and deadlines.
6. **Module**: Discrete tasks with skill requirements, risk levels, complexity, dependencies, and owners.
7. **Assignment**: Active and historical assignments with CP-SAT fit score, score breakdown, and runner-up explanation.
8. **Assessment**: Generated technical test packets (10 MCQs, 1 debug task, 1 code task).
9. **AssessmentResult**: Graded assessments with test scores, code runner output, and accuracy/speed metrics.
10. **DailyUpdate**: Work progress, hours spent, blockers, SLA status, and consistency deltas.
11. **Approval**: Team Lead sign-offs on daily updates.
12. **LeaveRecord**: Active and historical planned leaves, medical emergencies, and resignations.
13. **PerformanceSnapshot**: 0-100 composite scores across tests, past projects, consistency, SLA, and approvals.
14. **AllocationEvent**: Complete audit trail (before, after, reason) for all initial allocations and reallocations.
15. **ReassignmentRequest**: Formal employee task rejection / reassignment requests with mandatory justifications.
16. **HandoverPacket**: Auto-generated transition summaries between old and new module owners.
17. **Notification**: In-app notifications for task owners, leads, and managers.
18. **Email**: Outbound communications with support for both live SMTP and the mock mailer page.
19. **AgentTrace**: Step-by-step logs for OBSERVE, THINK, ACT, REFLECT, LOG live feed.
20. **Config**: Tunable performance weights, CP-SAT objective weights, and buffer ratios.
