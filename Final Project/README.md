# AI Career Coach

A Streamlit application that turns resume text into a structured career profile, a recommended career path, and an actionable development plan. The app provides a polished dashboard for the results; model inference runs in a separate Kaggle-hosted API.

## Highlights

- Upload a PDF resume or paste resume text.
- Extract selectable PDF text locally with `pypdf`, preview it, and show its character count before analysis.
- Send the resume to a FastAPI `/generate` endpoint hosted from the Kaggle notebook.
- Authenticate with the API key as a Bearer token.
- View candidate details, career recommendation, match score, relevant and missing skills, skill priorities, roadmap, project ideas, job titles, education, and experience.
- Parse JSON returned directly or embedded in the model's generated text.
- Use a responsive dark dashboard with connection status, loading feedback, and request/error messages.

## Project layout

| File | Purpose |
| --- | --- |
| `app.py` | Streamlit interface, PDF extraction, API request, response parsing, and results dashboard. |
| `requirements.txt` | Python packages required to run the local Streamlit app. |
| `run_app.bat` | Windows double-click launcher for the local app. |
| `tips-final-project-kaggle.ipynb` | Kaggle notebook that loads the language model and exposes the FastAPI service through an ngrok tunnel. |

## Architecture and data flow

1. Start and run the Kaggle notebook. It loads `mistralai/Mistral-Nemo-Instruct-2407`, prepares the structured-output prompt, starts a FastAPI service, and publishes it through ngrok.
2. Copy the public ngrok base URL printed by the notebook.
3. Run the Streamlit app locally and provide the backend URL and API key in the sidebar.
4. Choose either PDF upload or pasted text. For PDFs, `app.py` extracts selectable text on the local computer; it does not upload the PDF file itself.
5. On Analyze, the app sends a JSON request to `<backend URL>/generate`:

   ```json
   {
     "prompt": "Extracted or pasted resume text",
     "max_length": 2048
   }
   ```

   The API key is sent in the `Authorization` header using the `Bearer <API_KEY>` format.
6. The Kaggle API validates the key, formats the career-coach prompt, runs model inference, and returns a response containing generated text.
7. The app extracts the JSON object from that generated text and displays the structured dashboard.

The app appends `/generate` to the URL automatically. Enter either the ngrok base URL or its `/generate` endpoint; the suffix will not be duplicated.

## Response schema

The dashboard follows the response schema defined in the Kaggle notebook:

```text
{
  "full_name": string,
  "email": string,
  "education": list[object],
  "skills": list[string],
  "experience": list[object],
  "career_recommendation": {
    "career_name": string,
    "match_score": string,
    "reason": string,
    "current_relevant_skills": list[string],
    "missing_skills": list[string],
    "skill_priorities": list[string],
    "roadmap": list[string],
    "suggested_projects": list[string],
    "suggested_job_titles": list[string]
  }
}
```

The UI renders the candidate name, email, recommended career, and match score in the career snapshot. It then displays the recommendation details and the education and experience returned by the model.

## Run locally on Windows

### Requirements

- Windows with Python installed.
- A Kaggle notebook session running the API and its ngrok tunnel.
- The Python packages in `requirements.txt`.

### First-time setup

Open PowerShell or Command Prompt in this folder and install the app dependencies:

```powershell
python -m pip install -r requirements.txt
```

### Start the app

Double-click **`run_app.bat`**, or run either command from this folder:

```powershell
python -m streamlit run app.py
```

```powershell
streamlit run app.py
```

Streamlit prints a local address (usually `http://localhost:8501`) and may open it in your browser.

### Connect the running Kaggle API

1. Run the Kaggle notebook cells in order and keep the notebook session alive.
2. Copy the currently active public ngrok URL printed by the notebook.
3. Paste that URL into **Backend API URL** in the app sidebar.
4. Enter the same API key configured for the Kaggle API. Enter only the key; the app adds the `Bearer ` prefix.
5. Confirm the sidebar shows **Ready to connect**, add a resume, and select **Analyze Career Path**.

The ngrok URL is tied to the active tunnel and can change when the Kaggle session restarts. Copy the new URL into the app after restarting the notebook. The ngrok authentication token is used by the notebook to create the tunnel; it is not needed in the Streamlit app.

## Dependencies

The local Streamlit app declares these dependencies in `requirements.txt`:

- **Streamlit** — web interface and interactive dashboard.
- **pypdf** — text extraction from uploaded PDF files.
- **Requests** — HTTP communication with the Kaggle API.

The Kaggle notebook has its own inference dependencies, including **PyTorch**, **Transformers**, **LangChain**, **FastAPI**, **Uvicorn**, and **pyngrok**. Those notebook packages are not needed to launch the local Streamlit UI.

## Performance notes

PDF extraction runs locally before the request is sent. It is generally a small part of the work for a text-based resume; image-only/scanned PDFs may have no extractable text. The slow part is usually model inference in Kaggle, which depends on model loading, GPU availability, prompt size, and generated output length. The app uses a longer read timeout to accommodate inference, but response time cannot be guaranteed to be a few seconds.

## Security notes

- Do not commit API keys or ngrok tokens to source control or include them in screenshots or shared notebooks.
- Keep the Kaggle API key and ngrok authentication token separate; they serve different purposes.
- If a credential has been exposed, revoke/rotate it and update the Kaggle configuration.
- The API key is entered in a password field and used for the request; the app does not save it to a project configuration file.
- Resume text is sent to the configured backend for analysis. Avoid submitting information you are not authorized to share with that service.
