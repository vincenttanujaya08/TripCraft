# TripCraft Lite - Agentic Travel Planner

Portfolio-grade web application showcasing multi-agent RAG (Retrieval-Augmented Generation) system for intelligent travel planning.

## 🎯 Features

- **6 Specialized Agents**: Destination, Dining, Hotel, Flight, Budget, and Itinerary agents
- **3-Tier Data Retrieval**: Real APIs → Seed Data → LLM Fallback (Gemini 2.5 Flash)
- **Smart Image Integration**: Unsplash images with confidence scoring
- **Parallel Execution**: Efficient agent orchestration with async/await
- **Verifier System**: Validates itinerary feasibility and budget
- **Real-time Polling**: Frontend polls for agent progress
- **Structured Outputs**: Pydantic models ensure data consistency

## 🏗️ Architecture

```
Frontend (Next.js 14)
    ↓
Backend (FastAPI)
    ↓
┌─────────────────────────┐
│  6 Agents (Parallel)    │
│  ├── Destination        │
│  ├── Dining             │
│  ├── Hotel              │
│  ├── Flight             │
│  ├── Budget             │
│  └── Itinerary          │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│  Data Sources           │
│  ├── OpenTripMap API    │
│  ├── Seed JSON Files    │
│  └── Gemini LLM         │
└─────────────────────────┘
    ↓
SQLite Database
```

## 📋 Prerequisites

- Python 3.10+
- Node.js 18+
- Gemini API Key (required)
- OpenTripMap API Key (optional, recommended)
- Unsplash API Key (optional, recommended)

## 🚀 Setup Instructions

### 1. Clone Repository

```bash
git clone <your-repo>
cd tripcraft-lite
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp ../.env.example .env
```

### 3. Configure Environment Variables

Edit `.env` and add your API keys:

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional (but recommended)
OPENTRIPMAP_API_KEY=your_opentripmap_key
UNSPLASH_ACCESS_KEY=your_unsplash_key
```

**Get API Keys:**

- **Gemini API**: https://ai.google.dev/ (Free tier available)
- **OpenTripMap**: https://opentripmap.io/product (Free: 1000 calls/day)
- **Unsplash**: https://unsplash.com/developers (Free: 50 requests/hour)

### 4. Initialize Database

```bash
python -m models.database
```

You should see: `✅ Database initialized`

### 5. Run Backend

```bash
python main.py
```

Backend will start at: http://localhost:8000

Test it: http://localhost:8000/health

### 6. Frontend Setup (Next Step)

```bash
cd ../frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

Frontend will start at: http://localhost:3000

## 📁 Project Structure

```
tripcraft-lite/
├── backend/
│   ├── agents/              # 6 specialized agents
│   ├── data_sources/        # API clients & data loaders
│   ├── services/            # Image service, etc.
│   ├── models/              # Pydantic schemas & database
│   ├── routers/             # FastAPI routes
│   ├── main.py              # FastAPI app
│   └── requirements.txt
│
├── frontend/
│   ├── app/                 # Next.js pages
│   ├── components/          # React components
│   └── lib/                 # API client
│
├── seed_data/
│   ├── destinations.json    # 10 curated destinations
│   ├── hotels.json          # 40 hotels
│   ├── restaurants.json     # 60 restaurants
│   └── flights.json         # 30 flight routes
│
└── tests/
    ├── test_agents.py
    └── evaluate.py
```

## 🧪 Testing

### Test Individual Agents

```bash
# Once backend is running
curl http://localhost:8000/debug/destination \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "Bali, Indonesia",
    "start_date": "2025-12-01",
    "end_date": "2025-12-05",
    "budget": 15000000,
    "travelers": 2
  }'
```

### Run Evaluation Script

```bash
cd tests
python evaluate.py
```

## 🎨 How It Works

### User Flow

1. **User submits form** with destination, dates, budget, preferences
2. **Backend creates trip_id** and starts agent orchestration
3. **5 agents run in parallel** (Destination, Dining, Hotel, Flight, Budget)
4. **Itinerary agent** aggregates results into day-by-day plan
5. **Verifier agent** validates budget, schedule, and feasibility
6. **Frontend polls** GET /trip/{id} for status updates
7. **Results display** with images, itinerary, and warnings

### Data Retrieval (3-Tier Fallback)

```python
# Example: User requests "Malang, Indonesia"

# Tier 1: Try real API
result = await opentripmap.search("Malang")
if insufficient_data:
    # Tier 2: Check seed data
    result = seed_loader.find("Malang")
    if not_found:
        # Tier 3: LLM fallback
        result = await gemini.generate(
            "Create travel info for Malang",
            search_grounding=True
        )
        # Adds warning: "AI-generated, please verify"
```

### Image Confidence System

```python
# Keyword-based validation (no AI cost!)
image = search_unsplash("Museum Angkut Malang")
score = calculate_confidence(image.description, "Museum Angkut")

if score >= 0.7:
    badge = "✓ Verified"
elif score >= 0.4:
    badge = None  # No badge
else:
    badge = "⚠️ Illustrative"
```

## 🔧 Development

### Add New Destination to Seed Data

Edit `seed_data/destinations.json`:

```json
{
  "city": "Your City",
  "country": "Your Country",
  "description": "...",
  "attractions": [...]
}
```

### Add New Agent

1. Create `backend/agents/your_agent.py`
2. Implement `run()` method returning Pydantic model
3. Add to orchestrator in `routers/trip.py`

## 🚨 Common Issues

### "GEMINI_API_KEY not found"

Make sure `.env` file is in project root and has valid key:

```bash
GEMINI_API_KEY=your_actual_key_here
```

### "Database not found"

Run database initialization:

```bash
cd backend
python -m models.database
```

### "Port 8000 already in use"

Change port in `.env`:

```bash
BACKEND_PORT=8001
```

## 📊 Cost Estimate

With recommended free tier APIs:

- **OpenTripMap**: FREE (1000 calls/day)
- **Unsplash**: FREE (50 requests/hour)
- **Gemini 2.5 Flash**: ~$0.01 per trip (only for unknown destinations)

**Total**: < $1/month for 100 demo trips 🎉

## 🎯 Future Enhancements

- [ ] Real-time updates via WebSocket
- [ ] User authentication & saved trips
- [ ] Export itinerary to PDF
- [ ] Real flight booking integration
- [ ] Multi-language support
- [ ] Mobile app

## 📝 License

MIT License - feel free to use for your portfolio!

## 🤝 Contributing

This is a portfolio project, but suggestions are welcome!

## 📧 Contact

[Vincentius Tanujaya] - [vincenttanujaya08]

---

**Built with ❤️ using FastAPI, Next.js, and Gemini AI**
