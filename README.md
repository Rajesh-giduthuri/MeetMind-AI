# MeetMind AI
MeetMind AI is an AI-powered meeting intelligence application. It helps users turn meeting recordings and supported meeting links into timestamped transcripts, structured summaries, key points, decisions, and action items. Users can also review meeting history, play stored media, and ask questions about a selected meeting.

## Application Workflow
1. A user registers or logs in using email/password or Google sign-in.
2. The user uploads meeting media, submits a supported link, or uploads a supported document.
3. The frontend sends the request to the FastAPI backend using JavaScript `fetch()`.
4. Files are sent using `FormData`; structured request data is sent as JSON where appropriate.
5. FFmpeg/FFprobe are used for media processing, and `yt-dlp` is used for supported online video sources.
6. The application sends audio for transcription through the configured Groq API.
7. The transcript is processed by the configured Groq chat-completion model to generate structured meeting information.
8. Meeting details, transcript, summary, and related questions are stored in the database.
9. The user can review the transcript and summary, play the meeting media, and ask questions about that meeting.
10. The user can view, rename, or delete their meetings.

### Frontend–Backend Communication
The frontend uses HTML, CSS, and JavaScript. JavaScript's `fetch()` function sends HTTP requests to FastAPI REST endpoints.

- **JSON:** Used for structured request and response data.
- **FormData:** Used for file uploads.
- **FastAPI:** Receives and processes requests.
- **Database and AI services:** The backend communicates with PostgreSQL and the configured Groq services.
- **Response:** The backend returns JSON or a media stream; JavaScript updates the user interface.
```text
Browser (HTML / CSS / JavaScript)
              |
       JavaScript fetch()
        JSON or FormData
              |
        FastAPI REST API
              |
       ------------------
       |        |       |
   PostgreSQL  Groq   FFmpeg /
      Aiven     API    yt-dlp
       |
  JSON response or media stream
              |
         Browser UI
```
## Technology Stack

| Area | Technologies | Purpose |
|---|---|---|
| Frontend | HTML5, CSS3, JavaScript | User interface and API integration |
| Backend | Python, FastAPI, Uvicorn | REST APIs and application logic |
| Validation | Pydantic | Request validation |
| Database access | SQLAlchemy | ORM and database queries |
| Database | PostgreSQL, Aiven | Persistent application data |
| Local database option | SQLite | Local development fallback, if configured |
| PostgreSQL driver | psycopg | PostgreSQL connectivity |
| Transcription | Groq API (Whisper transcription service) | Speech-to-text |
| AI summarization | Groq chat-completion API | Meeting summary and information extraction |
| Media processing | FFmpeg, FFprobe | Audio/video processing and inspection |
| Online media | yt-dlp | Supported online video retrieval |
| Authentication | Authlib, Google OAuth 2.0 | Google sign-in |
| Password security | pwdlib with Argon2 | Password hashing |
| Sessions | Starlette SessionMiddleware, itsdangerous | Session-based authentication |
| Documents | pypdf, python-docx | PDF and DOCX processing |
| Deployment | Docker, Render | Containerized hosting |
| Version control | Git, GitHub | Source control and deployment |

## Architecture
The application contains these logical layers:

1. **Presentation layer:** HTML pages, CSS, and JavaScript.
2. **API layer:** FastAPI routes receive requests and return responses.
3. **Authentication layer:** Email/password authentication, Google OAuth, and session management.
4. **Processing layer:** Media preparation, transcription, and AI summarization.
5. **Data layer:** SQLAlchemy models and PostgreSQL persistence.
6. **Media storage layer:** Meeting media is stored in PostgreSQL and streamed in chunks.
7. **Hosting layer:** Docker packages the application, and Render runs the container.

## Requirements
- Python 3.11
- Git
- FFmpeg and FFprobe available on the system `PATH`
- Groq API credentials for the AI features
- Google OAuth credentials if Google sign-in is required
- A PostgreSQL connection URL for Aiven, or the configured SQLite local fallback

## Run Locally
The following commands use Windows PowerShell. Run them from the project root.

### 1. Clone the repository
```powershell
git clone https://github.com/Rajesh-giduthuri/MeetMind-AI.git
cd MeetMind-AI
```
### 2. Create and activate a virtual environment
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```
If PowerShell blocks activation, use Command Prompt:

```bat
.venv\Scripts\activate.bat
```
### 3. Install Python dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```
### 4. Install FFmpeg
Install FFmpeg and add its `bin` directory to your system `PATH`. Verify both commands:

```powershell
ffmpeg -version
ffprobe -version
```
### 5. Create the environment file
Create a `.env` file in the project root. The following is a template; use the exact variable names read by your current source code.

```env
# PostgreSQL connection string.
# Leave unset/empty only if your local configuration is set to use SQLite.
DATABASE_URL=

# Groq API key
GROQ_API_KEY=

# Long, random, private session-signing secret
SESSION_SECRET=

# Google OAuth credentials (only required for Google sign-in)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Use false for local HTTP development.
SESSION_HTTPS_ONLY=false
```
Do not commit `.env`. Never put real API keys, database passwords, OAuth secrets, or session secrets in this README or frontend JavaScript.

### 6. Start the application
```powershell
uvicorn main:app --reload
```

Open the application:

```text
http://127.0.0.1:8000
```

The project also defines a `/health` route. FastAPI's `/docs` page is available if the application exposes the default OpenAPI documentation route.

### 7. Test the main workflow
1. Register a test account.
2. Log in and verify that the session is maintained.
3. Upload a small supported audio/video file.
4. Confirm that transcription and summary generation complete.
5. Open the meeting and check its transcript, summary, and media playback.
6. Test meeting history, rename, and delete.
7. If Google sign-in is configured, test its OAuth callback.

## Environment Variables
| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string. The application may use SQLite if this is not set. |
| `GROQ_API_KEY` | API key for configured Groq services. |
| `SESSION_SECRET` | Secret used to sign session cookies. |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID. |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret. |
| `SESSION_HTTPS_ONLY` | Set to `true` for HTTPS production; use `false` for local HTTP. |

Configure production values in Render's environment-variable settings. Do not commit secrets.

## Run with Docker
Build the Docker image:

```powershell
docker build -t meetmind-ai .
```
Run the container:

```powershell
docker run --env-file .env -p 10000:10000 meetmind-ai
```
Open:

```text
http://localhost:10000
```
The container needs valid environment variables and network access to the configured database and external AI services.

## Deployment
The discussed deployment architecture is:

- **GitHub:** source code repository.
- **Render:** builds and runs the Dockerized FastAPI application.
- **Aiven PostgreSQL:** production database.
- **Groq:** configured transcription and AI services.
- **Google Cloud Console:** Google OAuth client and callback configuration.
