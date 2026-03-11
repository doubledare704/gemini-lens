from fastapi import Request
import os
import uuid
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv
from gtts import gTTS
from settings import settings
import re
import json

load_dotenv()

app = FastAPI(title="GeminiLens: The Interactive Educational Explainer")

# Ensure static and images directories exist
os.makedirs("static/images", exist_ok=True)
os.makedirs("static/audio", exist_ok=True)
os.makedirs("static/videos", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")
# Initialize genai client. Explicitly stripping quotes helps avoid common Docker env issues.
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    api_key = api_key.strip("\"'")

client = genai.Client(
    api_key=api_key, http_options={"api_version": settings.API_VERSION}
)


def generate_educational_diagram(prompt: str) -> str:
    """
    Generates an educational diagram or image based on the given prompt using Google's Imagen model.
    Call this tool when you need to visually explain a concept to the user.
    """
    print(f"DEBUG: Generating image for prompt: {prompt}")
    try:
        # Call Imagen model
        result = client.models.generate_images(
            model=settings.IMAGEN_MODEL_ID,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1, aspect_ratio="16:9", person_generation="DONT_ALLOW"
            ),
        )

        if not result.generated_images:
            return "Failed to generate image."

        generated_image = result.generated_images[0]

        # Save image locally
        image_filename = f"diagram_{uuid.uuid4().hex[:8]}.png"
        image_path = os.path.join("static", "images", image_filename)

        with open(image_path, "wb") as f:
            f.write(generated_image.image.image_bytes)

        return f"/static/images/{image_filename}"
    except Exception as e:
        print(f"Error generating image: {e}")
        return f"Error generating image: {str(e)}"


# Global in-memory presentations store
presentations_store = {}


def create_presentation_deck(slides_json: str) -> str:
    """
    Creates a presentation deck given a JSON string of slides.
    slides_json must be a list of objects: {"title": str, "content": str, "media_type": "image"|"video"|"none", "media_url": str}.
    Returns a URL to the newly created presentation.
    """
    try:
        slides = json.loads(slides_json)
        presentation_id = str(uuid.uuid4())
        presentations_store[presentation_id] = slides
        return f"/presentation/{presentation_id}"
    except Exception as e:
        print(f"Error creating presentation deck: {e}")
        return f"Error creating presentation deck: {str(e)}"


# Register the tool functions
tool_generate_diagram = generate_educational_diagram
tool_create_presentation = create_presentation_deck


class QueryRequest(BaseModel):
    query: str


@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r") as f:
        return f.read()


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/models")
async def get_models():
    return {"models": [m.name for m in client.models.list()]}


@app.get("/presentation/{presentation_id}", response_class=HTMLResponse)
async def get_presentation(request: Request, presentation_id: str):
    if presentation_id not in presentations_store:
        return HTMLResponse("<h1>Presentation not found.</h1>", status_code=404)

    slides = presentations_store[presentation_id]

    return templates.TemplateResponse(
        "presentation.html", {"request": request, "slides_data": slides}
    )


system_instruction = (
    "You are the GeminiLens Academic Mentor. "
    "Explain complex concepts clearly, utilizing text, and whenever helpful, generate educational diagrams to illustrate your points. "
    "Use the `generate_educational_diagram` tool to create visuals. "
    "When a user asks to summarize a lesson or create a deck, use the `create_presentation_deck` tool. Map complex concepts to slides. "
    "Use previously generated Imagen diagrams or Veo video URLs in the media_url field to make the slides visual. "
    "CRITICAL: You MUST ALWAYS include a detailed textual explanation in your responses. Never return only an image or diagram without accompanying text. "
    "Return your final explanation in Markdown format, embedding the generated image URLs where appropriate like ![Diagram Description](/static/images/...).\n"
    "At the very end of your response, you MUST provide exactly two suggested follow-up questions for the student related to the current topic. Format them EXACTLY like this on a new line:\n"
    'SUGGESTED_QUESTIONS: ["question 1", "question 2"]'
)

# Global chat session to keep history across requests
global_chat = client.chats.create(
    model=settings.MAIN_MODEL_ID,
    config=types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[tool_generate_diagram, tool_create_presentation],
        temperature=0.7,
    ),
)


@app.post("/api/explain")
async def explain_concept(request: QueryRequest):
    query = request.query

    if not query:
        return {"error": "Query is required"}

    try:
        # Send message through the global chat to maintain history
        response = global_chat.send_message(query)

        text = response.text or ""
        suggestions = []

        # Parse suggested questions out if they exist
        import json

        match = re.search(r"SUGGESTED_QUESTIONS:\s*(\[.*?\])", text, re.DOTALL)
        if match:
            try:
                suggestions_str = match.group(1)
                suggestions = json.loads(suggestions_str)
                # Remove from display text
                text = text[: match.start()].strip()
            except Exception as e:
                print("Failed to parse suggestions:", e)

        return {"text": text, "suggestions": suggestions}

    except Exception as e:
        import traceback

        traceback.print_exc()
        return {"error": str(e)}


@app.post("/api/generate_audio")
async def generate_audio(request: QueryRequest):
    query = request.query
    if not query:
        return {"error": "Query is required"}

    try:
        # Step 1: Generate a summary for 5-20yo
        prompt = f"Summarize the following topic for an audience between 5 and 20 years old. Make it engaging, simple, and very short (max 3 sentences):\n\nTopic: {query}"
        response = client.models.generate_content(
            model=settings.MAIN_MODEL_ID, contents=prompt
        )
        summary_text = response.text

        # Step 2: Generate TTS using gTTS
        tts = gTTS(text=summary_text, lang="en", slow=False)
        audio_filename = f"audio_{uuid.uuid4().hex[:8]}.mp3"
        audio_path = os.path.join("static", "audio", audio_filename)
        tts.save(audio_path)

        return {"audio_url": f"/static/audio/{audio_filename}", "summary": summary_text}
    except Exception as e:
        import traceback

        traceback.print_exc()
        return {"error": str(e)}


# In-memory store for operations
video_operations = {}


@app.post("/api/generate_video")
async def generate_video(request: QueryRequest):
    query = request.query
    if not query:
        return {"error": "Query is required"}

    try:
        # Create a prompt for the video model based on the query
        prompt = f"A short, engaging, educational, animated video visualizing the concept of: {query}. Bright colors, cinematic lighting."

        # We use the preview fast version
        op = client.models.generate_videos(
            model=settings.VEO_MODEL_ID,
            prompt=prompt,
            config=types.GenerateVideosConfig(
                number_of_videos=1,
                aspect_ratio="16:9",
                duration_seconds=6,
                generate_audio=False,
            ),
        )
        op_name = op.name
        video_operations[op_name] = op
        return {"operation_id": op_name, "status": "running"}
    except Exception as e:
        import traceback

        traceback.print_exc()
        return {"error": str(e)}


@app.get("/api/video_status/{operation_id:path}")
async def video_status(operation_id: str):
    try:
        operation: types.GenerateVideosOperation | None = video_operations.get(
            operation_id
        )
        if not operation:
            return {"status": "error", "error": "Operation not found"}

        op = client.operations.get(operation=operation)

        if op.done:
            if op.error:
                return {"status": "error", "error": str(op.error)}

            result: types.GenerateVideosResponse = op.response
            if result:
                print("Result: ", result)
                if result.generated_videos:
                    gen_video: types.GeneratedVideo = result.generated_videos[0]
                    video_blob: types.Video = gen_video.video

                    video_filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
                    video_path = os.path.join("static", "videos", video_filename)

                    if video_blob.video_bytes is not None:
                        with open(video_path, "wb") as f:
                            f.write(video_blob.video_bytes)
                    elif video_blob.uri is not None:
                        # The URI is an authenticated Google API endpoint, so we download it locally
                        import urllib.request

                        api_key = os.getenv("GOOGLE_API_KEY")
                        req = urllib.request.Request(
                            video_blob.uri, headers={"x-goog-api-key": api_key}
                        )
                        with urllib.request.urlopen(req) as response:
                            content = response.read()
                            with open(video_path, "wb") as f:
                                f.write(content)
                        # We don't return here but fall-through to the generic video_url return
                    else:
                        return {
                            "status": "error",
                            "error": "No video bytes found in response.",
                        }

                    return {
                        "status": "done",
                        "video_url": f"/static/videos/{video_filename}",
                    }
                else:
                    error_msg = "No videos found in operation."
                    if result.rai_media_filtered_reasons:
                        error_msg = "Blocked by safety filters: " + ", ".join(
                            result.rai_media_filtered_reasons
                        )
                    return {"status": "error", "error": error_msg}
            else:
                return {
                    "status": "error",
                    "error": "Operation complete but no response.",
                }
        else:
            return {"status": "running"}
    except Exception as e:
        import traceback

        traceback.print_exc()
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
