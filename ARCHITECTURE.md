# GeminiLens System Architecture

The following diagram illustrates the flow of data and control within the GeminiLens platform, from the user's initial query to the generation of multimodal educational content.

```mermaid
graph TB
    subgraph Frontend ["Frontend HTML5/JS/CSS"]
        UI["Chat Interface index.html"]
        RP["Reveal.js Engine presentation.html"]
    end

    subgraph Backend ["Backend FastAPI & Python 3.13"]
        API["API Layer /api/explain, etc."]
        Agent["Gemini Academic Mentor Orchestrator"]
        Store["In-Memory Presentation Store UUID based"]
        Jinja["Jinja2 Templating Engine"]
    end

    subgraph GoogleCloud ["Google Gemini & AI Services"]
        Flash["Gemini 3 Flash Multimodal Reasoning"]
        Imagen["Imagen 4 Educational Diagrams"]
        Veo["Veo Animated Explainer Videos"]
        G_Audio["gTTS / Audio Modality"]
    end

    %% Interactions
    UI <-->|"JSON over HTTP"| API
    API <--> Agent
    Agent <-->|"SDK / Tool Calling"| Flash
    
    %% Tool specific flows
    Flash -->|"Function Call: generate_diagram"| Imagen
    Flash -->|"Function Call: create_presentation"| Store
    Flash -->|"Trigger: generate_video"| Veo
    
    %% Presentation flow
    UI -->|"Redirect /presentation/id"| API
    API -->|"Fetch Slides"| Store
    API -->|"Render Template"| Jinja
    Jinja -->|"Serve HTML"| RP
    
    %% Static Asset Flow
    Imagen -->|"Save .png"| Static["Static Directory: images/audio/videos"]
    Veo -->|"Save .mp4"| Static
    Static -->|"Serve Assets"| UI
    Static -->|"Serve Assets"| RP

    style Frontend fill:#f0f7ff,stroke:#0056b3,stroke-width:2px
    style Backend fill:#fff5f0,stroke:#d9480f,stroke-width:2px
    style GoogleCloud fill:#f3f0ff,stroke:#5f3dc4,stroke-width:2px
    style Static fill:#f8f9fa,stroke:#adb5bd,stroke-dasharray: 5 5
```

## Key Technical Components:
1.  **FastAPI (Backend Orchestrator)**: Manages all API endpoints, handles the asynchronous generation cycles for video, and serves both the main chat and the dynamic presentation pages.
2.  **Gemini 3 Flash**: Acts as the brain of the system, determining when a student needs a diagram, a video, or an audio summary.
3.  **Tool Calling Pipeline**: 
    -   `generate_educational_diagram`: Real-time creation of diagrams using Imagen 4.
    -   `create_presentation_deck`: Aggregates conversation context into a structured JSON for Reveal.js.
4.  **Jinja2 + Reveal.js**: Modern stack for turning AI-generated JSON into highly interactive, web-based slide decks.
5.  **`uv` Deployment**: Using the `uv` package manager for lightning-fast container builds and deployment on **Google Cloud Run**.
