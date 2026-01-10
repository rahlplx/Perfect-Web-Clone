# Perfect Web Clone

AI-powered web page extraction and cloning tool. Extract any webpage's structure, styles, and components, then use AI to generate pixel-perfect clones.

## Features

### Web Extractor
- **Full Page Capture**: Extract complete DOM structure, CSS styles, and assets
- **Theme Detection**: Automatically detect and capture both light and dark themes
- **Component Analysis**: AI-powered component boundary detection
- **Tech Stack Analysis**: Identify frameworks and libraries used on the page
- **Asset Extraction**: Download images, fonts, and other resources

### Clone Agent
- **AI Code Generation**: Use Claude to generate code based on extracted data
- **Live Preview**: Real-time code preview with WebContainer
- **Multi-Agent Architecture**: Master agent coordinates worker agents for parallel development
- **Image Handling**: Automatic image URL processing for local development

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Anthropic API Key

### Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Configure environment
cp ../.env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Start the server
python main.py
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp ../.env.example .env.local
# Edit .env.local if needed

# Start development server
npm run dev
```

### Access the Application

Open http://localhost:3000 in your browser.

## Usage

### 1. Extract a Website

1. Go to the **Extractor** page
2. Enter a URL to extract
3. Configure extraction options (viewport, theme, etc.)
4. Click **Extract** to start
5. Once complete, click **Save to Cache** to store the result

### 2. Clone with AI

1. Go to the **Agent** page
2. Click **Sources** button to open the source panel
3. Select a cached extraction
4. Chat with the AI to generate code
5. View live preview as the Agent writes code

## Architecture

```
perfect-web-clone/
├── backend/                 # Python FastAPI backend
│   ├── cache/              # Memory cache for extractions
│   ├── extractor/          # Playwright-based web extractor
│   ├── agent/              # AI agent with Claude integration
│   ├── image_proxy/        # Image proxy for CORS handling
│   └── image_downloader/   # Image download service
│
├── frontend/               # Next.js frontend
│   ├── src/app/           # App router pages
│   ├── src/components/    # React components
│   │   ├── ui/           # Shadcn/UI components
│   │   ├── extractor/    # Extractor tab components
│   │   └── agent/        # Agent components
│   ├── src/hooks/        # Custom React hooks
│   └── src/lib/          # Utilities and API clients
│
└── .env.example           # Environment variables template
```

## Key Technologies

- **Frontend**: Next.js 15, React 19, TailwindCSS 4, Shadcn/UI
- **Backend**: FastAPI, Python 3.11+, Playwright
- **AI**: Claude (Anthropic API)
- **Preview**: WebContainer (StackBlitz)

## API Endpoints

### Extractor API

- `POST /api/extractor/extract` - Start extraction
- `GET /api/extractor/status/{request_id}` - Poll extraction status

### Cache API

- `POST /api/cache/store` - Store extraction to cache
- `GET /api/cache/list` - List cached extractions
- `GET /api/cache/{id}` - Get cached extraction
- `DELETE /api/cache/{id}` - Delete cached extraction

### Agent API

- `WS /api/agent/ws` - WebSocket for AI agent communication

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
