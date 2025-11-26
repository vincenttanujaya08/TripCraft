# 🧪 TripCraft Lite - Testing Guide

## 📋 Apa yang Sudah Dibangun di SESSION 2

SESSION 2 membangun **backend core** TripCraft Lite:
- **4 Data Sources**: Sistem fallback 3-tier (API → Seed → LLM)
- **7 Agents**: Destination, Hotel, Dining, Flight, Budget, Itinerary, Verifier
- **1 Base Agent**: Template untuk semua agent
- **1 Test Script**: Automated testing untuk semua komponen

**Total**: ~2,200 baris code production-ready ✅

---

## 🚀 Cara Testing - Step by Step

### **STEP 1: Persiapan Environment**

Buka terminal di folder `tripcraft-lite`:

```bash
cd tripcraft-lite

# Aktifkan virtual environment
source venv/bin/activate        # Mac/Linux
# ATAU
venv\Scripts\activate           # Windows
```

**Expected Output**:
```
(venv) user@computer:~/tripcraft-lite$
```
✅ Harus ada `(venv)` di awal prompt

---

### **STEP 2: Cek Requirements**

```bash
pip list | grep -E "fastapi|google-generativeai|tenacity"
```

**Expected Output**:
```
fastapi                    0.104.1
google-generativeai        0.3.1
tenacity                   8.2.3
```

❌ **Kalau kosong**, install dulu:
```bash
pip install -r backend/requirements.txt
```

---

### **STEP 3: Setup Environment Variables**

```bash
# Cek apakah .env sudah ada
cat .env

# Kalau belum ada, copy dari example:
cp .env.example .env

# Edit .env dan isi GEMINI_API_KEY
nano .env  # atau pakai editor lain
```

**Isi .env harus seperti ini**:
```env
GEMINI_API_KEY=AIzaSyC...your_actual_key
DATABASE_URL=sqlite:///./tripcraft.db
ENVIRONMENT=development
```

🔑 **Dapatkan API Key gratis**: https://makersuite.google.com/app/apikey

---

### **STEP 4: Run Test Script**

```bash
python test_session2.py
```

**Expected Output (Success)**:
```
🧪 TESTING TRIPCRAFT LITE - SESSION 2
=====================================

📊 Testing Data Sources Layer
------------------------------
✓ SeedLoader initialized
✓ Loaded destinations: 10
✓ Loaded hotels: 40
✓ Loaded restaurants: 60
✓ Loaded flights: 30

✓ Query destination 'Bali': Found
✓ Query hotels in 'Tokyo' (budget=2000000): 4 hotels
✓ SmartRetriever.get_destination('Paris'): Success (source: seed)

🤖 Testing Agents
-----------------
🌍 DestinationAgent
   ✓ Executed in 0.8s
   ✓ Confidence: 95%
   ✓ Found 8 attractions

🏨 HotelAgent
   ✓ Executed in 0.5s
   ✓ Confidence: 90%
   ✓ Selected: Grand Hyatt Bali
   ✓ Total cost: Rp 6,000,000

🍽️ DiningAgent
   ✓ Executed in 0.6s
   ✓ Confidence: 88%
   ✓ Found 6 restaurants
   ✓ Daily food cost: Rp 500,000

✈️ FlightAgent
   ✓ Executed in 1.2s
   ✓ Confidence: 92%
   ✓ Found 3 flight options
   ✓ Best flight: Rp 3,500,000

💰 BudgetAgent
   ✓ Executed in 0.3s
   ✓ Total: Rp 15,800,000
   ✓ Within budget: YES
   ✓ Remaining: Rp 4,200,000

📅 ItineraryAgent
   ✓ Executed in 0.9s
   ✓ Generated 5 days
   ✓ Activities distributed: 15

🛡️ VerifierAgent
   ✓ Executed in 0.4s
   ✓ Quality score: 87/100
   ✓ Errors: 0, Warnings: 2

🎉 ALL TESTS PASSED!
=====================================
Total execution time: 5.2 seconds
```

✅ **Jika output seperti ini = SESSION 2 BERHASIL!**

---

## 🐛 Troubleshooting - Kalau Ada Error

### **Error 1: ModuleNotFoundError**

```
ModuleNotFoundError: No module named 'google.generativeai'
```

**Solusi**:
```bash
pip install -r backend/requirements.txt
```

---

### **Error 2: GEMINI_API_KEY not found**

```
ValueError: GEMINI_API_KEY not found in environment
```

**Solusi**:
```bash
# Pastikan .env ada dan terisi
cat .env

# Kalau kosong:
echo "GEMINI_API_KEY=AIzaSyC_your_key_here" > .env
```

---

### **Error 3: Import Error (Path Issues)**

```
ImportError: attempted relative import beyond top-level package
```

**Solusi**:
```bash
# Pastikan Anda di folder ROOT project
pwd  # Harus menunjukkan .../tripcraft-lite

# Jalankan dari root:
python test_session2.py
# BUKAN:
cd backend && python ../test_session2.py  # ❌ SALAH
```

---

### **Error 4: Database Not Found**

```
FileNotFoundError: seed_data/destinations.json not found
```

**Solusi**:
```bash
# Cek apakah seed_data/ ada
ls seed_data/

# Kalau tidak ada, re-download project atau regenerate
```

---

### **Error 5: API Rate Limit (429)**

```
google.api_core.exceptions.ResourceExhausted: 429 Quota exceeded
```

**Solusi**:
Tunggu beberapa menit atau gunakan API key baru dari Google AI Studio.

---

## 📊 Manual Testing - Test Individual Components

Kalau mau test komponen terpisah:

### **Test 1: Data Sources**

```python
# Buat file: test_datasource.py
import asyncio
from backend.data_sources.seed_loader import SeedLoader
from backend.data_sources.smart_retriever import SmartRetriever

async def test():
    loader = SeedLoader()
    print(f"Destinations: {len(loader.destinations)}")
    
    retriever = SmartRetriever()
    dest, source = await retriever.get_destination("Tokyo")
    print(f"Tokyo data from: {source}")
    print(f"Description: {dest.get('description', 'N/A')[:100]}...")

asyncio.run(test())
```

Run:
```bash
python test_datasource.py
```

---

### **Test 2: Single Agent**

```python
# Buat file: test_agent.py
import asyncio
from backend.agents.destination_agent import DestinationAgent
from backend.models.schemas import TripRequest

async def test():
    request = TripRequest(
        destination="Bali",
        start_date="2025-01-15",
        end_date="2025-01-20",
        budget=20000000,
        preferences=["beach", "culture"]
    )
    
    agent = DestinationAgent()
    result = await agent.execute(request, {})
    
    print(f"✓ Confidence: {result.confidence}%")
    print(f"✓ Attractions: {len(result.data.get('attractions', []))}")
    print(f"✓ Description: {result.data['description'][:100]}...")

asyncio.run(test())
```

Run:
```bash
python test_agent.py
```

---

### **Test 3: Complete Agent Pipeline**

```python
# Buat file: test_pipeline.py
import asyncio
from backend.models.schemas import TripRequest
from backend.agents.destination_agent import DestinationAgent
from backend.agents.hotel_agent import HotelAgent
from backend.agents.dining_agent import DiningAgent
from backend.agents.flight_agent import FlightAgent
from backend.agents.budget_agent import BudgetAgent

async def test():
    request = TripRequest(
        destination="Tokyo",
        origin_city="Jakarta",
        start_date="2025-02-10",
        end_date="2025-02-15",
        budget=30000000,
        num_travelers=2
    )
    
    context = {}
    
    # Run agents sequentially
    agents = [
        DestinationAgent(),
        HotelAgent(),
        DiningAgent(),
        FlightAgent(),
        BudgetAgent()
    ]
    
    for agent in agents:
        result = await agent.execute(request, context)
        context[agent.__class__.__name__] = result
        print(f"✓ {agent.__class__.__name__}: {result.confidence}%")
    
    # Check budget
    budget_result = context['BudgetAgent']
    print(f"\n💰 Total Cost: Rp {budget_result.data['breakdown']['total']:,}")
    print(f"✓ Within Budget: {budget_result.data['within_budget']}")

asyncio.run(test())
```

Run:
```bash
python test_pipeline.py
```

---

## 🎯 What to Check in Test Results

### ✅ **Success Indicators**:

1. **No Python Errors**: Semua print statement muncul tanpa exception
2. **Confidence Scores**: Semua agent return confidence 70-100%
3. **Data Completeness**: Semua field (hotels, restaurants, flights) terisi
4. **Budget Validation**: Total cost ≤ budget yang diminta
5. **Execution Time**: Total < 10 detik (untuk test script)

### ⚠️ **Warning Indicators** (Masih OK):

1. **Low Confidence (50-70%)**: Agent masih jalan tapi data kurang lengkap
2. **LLM Fallback Used**: Seed data tidak ketemu, pakai Gemini (slower)
3. **Some Fields Missing**: Beberapa field optional kosong

### ❌ **Failure Indicators**:

1. **Python Exception**: Import error, syntax error
2. **Confidence < 50%**: Data sangat tidak lengkap
3. **Budget Exceeded**: Total cost > budget
4. **No Results**: Agent return empty data

---

## 📈 Performance Benchmarks

**Expected Performance** (on average laptop):

| Component | Expected Time | Acceptable Range |
|-----------|---------------|------------------|
| SeedLoader | < 0.1s | 0.05-0.2s |
| DestinationAgent | 0.5-1s | 0.3-2s |
| HotelAgent | 0.3-0.8s | 0.2-1.5s |
| DiningAgent | 0.3-0.8s | 0.2-1.5s |
| FlightAgent | 0.8-1.5s | 0.5-3s |
| BudgetAgent | 0.1-0.3s | 0.05-0.5s |
| ItineraryAgent | 0.5-1s | 0.3-2s |
| VerifierAgent | 0.2-0.5s | 0.1-1s |
| **Total Pipeline** | **4-7s** | **3-10s** |

⚠️ Jika LLM fallback dipakai = bisa tambah 2-5 detik per agent

---

## 🔍 Deep Dive Testing - Check Code Quality

### **Test Agent Logic**:

```bash
# Test apakah hotel agent respect budget
python -c "
import asyncio
from backend.agents.hotel_agent import HotelAgent
from backend.models.schemas import TripRequest

async def test():
    req = TripRequest(
        destination='Bali',
        start_date='2025-01-01',
        end_date='2025-01-05',
        budget=5000000,  # Low budget
        num_travelers=1
    )
    agent = HotelAgent()
    result = await agent.execute(req, {})
    total = result.data['total_cost']
    print(f'Budget: Rp 5,000,000')
    print(f'Hotel cost: Rp {total:,}')
    print(f'✓ Passed' if total <= 5000000 else '✗ Failed')

asyncio.run(test())
"
```

---

### **Test Data Fallback Chain**:

```python
# Buat file: test_fallback.py
import asyncio
from backend.data_sources.smart_retriever import SmartRetriever

async def test():
    retriever = SmartRetriever()
    
    # Test 1: City in seed data
    dest1, src1 = await retriever.get_destination("Tokyo")
    print(f"Tokyo source: {src1}")  # Should be "seed"
    
    # Test 2: City NOT in seed data (triggers LLM)
    dest2, src2 = await retriever.get_destination("Reykjavik")
    print(f"Reykjavik source: {src2}")  # Should be "llm_fallback"

asyncio.run(test())
```

---

## 📝 Test Checklist

Setelah menjalankan semua test, pastikan:

- [ ] `test_session2.py` berhasil tanpa error
- [ ] Semua 7 agents return hasil
- [ ] Confidence score rata-rata > 80%
- [ ] Budget calculations benar (manual check)
- [ ] Seed data terload (10 destinations, 40 hotels, etc.)
- [ ] LLM fallback bekerja (test dengan city yang tidak ada di seed)
- [ ] No import errors
- [ ] Execution time < 10s untuk full pipeline

---

## 🎓 Next Steps - Setelah Testing Berhasil

Kalau semua test ✅ passed:

### **SESSION 3 Preview**:
1. **Orchestrator** - Koordinasi semua agents secara parallel
2. **API Endpoints** - FastAPI routes untuk frontend
3. **WebSocket** - Real-time progress updates
4. **Error Handling** - Comprehensive error management

**Estimated Time**: 2-3 jam untuk SESSION 3

---

## 💡 Tips untuk Testing

1. **Start Simple**: Test komponen terkecil dulu (SeedLoader) sebelum test full pipeline
2. **Check Logs**: Perhatikan print statements untuk debug
3. **Use Small Budget**: Untuk testing, pakai budget kecil agar cepat
4. **Test Edge Cases**: 
   - Budget sangat rendah
   - Destinasi tidak ada di seed
   - Dietary restrictions ketat
4. **Monitor Performance**: Pakai `time` command untuk track execution time

---

## 🆘 Need Help?

Kalau stuck atau ada error:

1. **Check this guide's troubleshooting section** ⬆️
2. **Read error message carefully** - biasanya jelas apa masalahnya
3. **Verify file structure** - pastikan semua file di tempat yang benar
4. **Re-run with verbose mode**: tambahkan print statements untuk debug

---

## ✅ Success Criteria

**SESSION 2 dianggap berhasil jika**:
- ✅ `test_session2.py` sukses run tanpa exception
- ✅ Minimal 5 dari 7 agents return confidence > 70%
- ✅ Budget calculation akurat (cek manual)
- ✅ Execution time < 15 detik
- ✅ Data fallback chain berfungsi

**Congratulations! 🎉** Anda siap untuk SESSION 3!

---

**Last Updated**: Session 2 Complete
**Total Files**: 13 backend files + 1 test script
**Total Lines**: ~2,200 lines of code
