# IntelliPrep — Backend

AI-powered mock interview platform. Users upload their resume and a job description, and the system conducts a full interview using a LangGraph agent —> parsing the resume, scoring candidate fit, generating tailored questions, evaluating answers in real time, and producing a final verdict with improvement tips.

---

## Tech Stack

| Layer            | Technology                            |
| ---------------- | ------------------------------------- |
| API Framework    | FastAPI                               |
| AI Agent         | LangGraph + LangChain OpenAI          |
| Database         | PostgreSQL (async via asyncpg)        |
| ORM / Migrations | SQLModel + SQLAlchemy async + Alembic |
| Auth             | JWT (python-jose) + bcrypt            |
| PDF Parsing      | pdfplumber                            |
| Runtime          | Python 3.12+ / Uvicorn                |

---

## Project Structure

```
app/
├── agents/          # LangGraph interview agent (graph, nodes, schemas, state)
├── api/
│   ├── routes/      # REST API route handlers
│   └── websocket/   # WebSocket interview handler
├── core/            # Config & LLM setup
├── db/              # Database engine & session
├── models/          # SQLModel ORM models
├── schemas/         # Pydantic request/response schemas
├── services/        # Business logic services
└── utils/           # Helpers (security / JWT)
alembic/             # Database migrations
```

---

## How It Works

The interview flow is driven by a LangGraph agent graph:

```
START → resume_parser → jd_analyzer → fit_scorer → question_generator
      → interview_loop → answer_evaluator → follow_up_decider
                              ↙ (more questions)          ↘ (done)
                       interview_loop               final_evaluator → END
```

1. **resume_parser** — Extracts structured data from the uploaded PDF resume.
2. **jd_analyzer** — Parses the job description to identify required skills and criteria.
3. **fit_scorer** — Scores how well the candidate's profile fits the role.
4. **question_generator** — Generates tailored interview questions based on the JD and resume.
5. **interview_loop** — Presents one question at a time to the candidate over a WebSocket.
6. **answer_evaluator** — Evaluates the candidate's answer (runs after each response).
7. **follow_up_decider** — Decides whether to ask a follow-up question or move on.
8. **final_evaluator** — Produces an overall verdict (`HIRE`, `STRONG_HIRE`, `NO_HIRE`, `STRONG_NO_HIRE`, `NO_DECISION`) with per-dimension scores and improvement tips.

---

## API Endpoints

All REST endpoints are prefixed with `/api`. Authentication is via `Authorization: Bearer <token>`.

### Health

| Method | Path      | Auth | Description  |
| ------ | --------- | ---- | ------------ |
| `GET`  | `/health` | No   | Health check |

### Authentication — `/api/auth`

| Method | Path                 | Auth | Description                             |
| ------ | -------------------- | ---- | --------------------------------------- |
| `POST` | `/api/auth/register` | No   | Register a new user                     |
| `POST` | `/api/auth/login`    | No   | Login and receive a JWT token           |
| `PUT`  | `/api/auth/profile`  | Yes  | Update the authenticated user's profile |

### Resumes — `/api/resumes`

| Method   | Path                       | Auth | Description                           |
| -------- | -------------------------- | ---- | ------------------------------------- |
| `POST`   | `/api/resumes/upload`      | Yes  | Upload a resume PDF                   |
| `GET`    | `/api/resumes/`            | Yes  | List all resumes for the current user |
| `GET`    | `/api/resumes/{resume_id}` | Yes  | Get a specific resume by ID           |
| `PUT`    | `/api/resumes/{resume_id}` | Yes  | Replace a resume with a new PDF       |
| `DELETE` | `/api/resumes/{resume_id}` | Yes  | Delete a resume                       |

### Job Applications — `/api/job-applications`

| Method   | Path                                     | Auth | Description                                    |
| -------- | ---------------------------------------- | ---- | ---------------------------------------------- |
| `POST`   | `/api/job-applications/`                 | Yes  | Create a new job application                   |
| `GET`    | `/api/job-applications/`                 | Yes  | List all job applications for the current user |
| `GET`    | `/api/job-applications/{application_id}` | Yes  | Get a specific job application                 |
| `PUT`    | `/api/job-applications/{application_id}` | Yes  | Update a job application                       |
| `DELETE` | `/api/job-applications/{application_id}` | Yes  | Delete a job application                       |

### Interview Sessions — `/api/interview-sessions`

| Method   | Path                                                           | Auth | Description                         |
| -------- | -------------------------------------------------------------- | ---- | ----------------------------------- |
| `POST`   | `/api/interview-sessions/`                                     | Yes  | Create a new interview session      |
| `GET`    | `/api/interview-sessions/job-application/{job_application_id}` | Yes  | List sessions for a job application |
| `GET`    | `/api/interview-sessions/{interview_session_id}`               | Yes  | Get a specific interview session    |
| `DELETE` | `/api/interview-sessions/{interview_session_id}`               | Yes  | Delete an interview session         |

### Interview WebSocket — `/api/ws`

| Type        | Path                             | Description                 |
| ----------- | -------------------------------- | --------------------------- |
| `WebSocket` | `/api/ws/interview/{session_id}` | Real-time interview session |

**WebSocket message protocol:**

Send answers as JSON:

```json
{ "type": "answer", "answer": "Your answer text here" }
```

The server streams back questions and status updates as JSON throughout the session.

---

## Installation & Running

### Prerequisites

- Python 3.12+
- PostgreSQL database (local or cloud, e.g. Neon)
- `uv` package manager (`pip install uv`)

### 1. Clone the repository

```bash
git clone <repo-url>
cd backend
```

### 2. Create and activate a virtual environment

```bash
uv venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
```

### 3. Install dependencies

```bash
uv sync
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
APP_NAME=IntelliPrep
APP_ENV=development
DEBUG=true

DATABASE_URL=postgresql+asyncpg://user:password@host/dbname

SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
SALT_ROUNDS=12

OPENAI_API_KEY=sk-...
```

### 5. Run database migrations

```bash
.venv/bin/alembic upgrade head
```

### 6. Start the server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.  
Interactive API docs: `http://localhost:8000/docs`

---

## Environment Variables Reference

| Variable                      | Required | Description                                            |
| ----------------------------- | -------- | ------------------------------------------------------ |
| `APP_NAME`                    | Yes      | Application name                                       |
| `APP_ENV`                     | No       | `development` or `production` (default: `development`) |
| `DEBUG`                       | Yes      | Enable debug mode (`true`/`false`)                     |
| `DATABASE_URL`                | Yes      | Async PostgreSQL URL (`postgresql+asyncpg://...`)      |
| `SECRET_KEY`                  | Yes      | Secret key for JWT signing                             |
| `ALGORITHM`                   | Yes      | JWT algorithm (e.g. `HS256`)                           |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No       | Token expiry in minutes (default: `30`)                |
| `SALT_ROUNDS`                 | No       | bcrypt salt rounds (default: `12`)                     |
| `OPENAI_API_KEY`              | Yes      | OpenAI API key for LLM inference                       |
