# Kaleido - Micro Language Learning App

✨ Turn Curiosity Into Language Skills

## Setup & Running Locally

### Environment Variables
Create a `.env` file in the root directory with:

```bash
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
FAL_KEY=your_fal_ai_key
TAVILY_API_KEY=your_tavily_api_key
```

### Installation

1. Clone the repository
```bash
git clone https://github.com/nolanvo5894/kaleido.git
cd kaleido
```

2. Create and activate virtual environment

```bash
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

### Running the App

1. Start the FastAPI server
```bash
uvicorn app:app --reload
```

2. Open your browser and navigate to the localhost url given by the app 


### Development

- Frontend files are in the `static` directory
- Backend API is in `app.py`
- Database models are in `models.py`
- Exercise generation workflow is in `workflow.py`

### Features
- Generate reading exercises from any topic
- AI-generated illustrations
- Text-to-speech audio generation
- Interactive question answering
- Score tracking
