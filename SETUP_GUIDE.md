# Power BI Chatbot - Setup Guide for New Machine

## Prerequisites
- **Node.js** (v14+): [Download](https://nodejs.org/)
- **Python** (3.8+): [Download](https://www.python.org/)
- **Power BI Desktop**: [Download](https://powerbi.microsoft.com/en-us/desktop/)
- **Git**: [Download](https://git-scm.com/)
- **Groq API Key**: [Get free key](https://console.groq.com)

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/Power-BI-Bot.git
cd Power-BI-Bot
```

---

## Step 2: Setup Backend (Python)

### 2.1 Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**Key packages installed:**
- fastapi - Web server
- uvicorn - ASGI server
- groq - LLM API client
- pydantic - Data validation
- python-dotenv - Environment variables

### 2.2 Configure Environment

Create `.env` file in `backend/` directory:

```bash
# backend/.env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=mixtral-8x7b-32768
DEBUG=True
BACKEND_PORT=8000
CORS_ORIGINS=["*"]
```

**Get your Groq API Key:**
1. Go to https://console.groq.com
2. Sign up/login
3. Copy your API key
4. Paste in `.env` file

---

## Step 3: Setup Frontend (Power BI Visual)

### 3.1 Install Node Dependencies

```bash
cd PowerBIBotVisual
npm install
```

### 3.2 Build the Visual

```bash
npm run package
```

This creates: `dist/powerBIBotVisual99999999999999999999.1.0.0.1.pbiviz`

---

## Step 4: Setup Power BI Desktop

### 4.1 Open Your Hospital Dashboard

1. Open Power BI Desktop
2. Open your existing `.pbix` file or create new dashboard
3. Ensure you have these fields available:
   - `department`
   - `patient_condition`
   - `admission_status`
   - `hospital_cost`
   - `length_of_stay`

### 4.2 Import Custom Visual

1. In Power BI Desktop: **Home** → **Get More Visuals** → **From a file**
2. Navigate to: `PowerBIBotVisual\dist\powerBIBotVisual99999999999999999999.1.0.0.1.pbiviz`
3. Click **Open** → **Import**
4. Add the visual to your dashboard

### 4.3 Bind Data to Visual (CRITICAL!)

1. Click on the chatbot visual
2. In **Fields pane** (right side), drag any field into the visual
3. Example: Drag `department` field into the visual
4. This connects the visual to your data model

---

## Step 5: Run the System

### 5.1 Start Backend Server

```bash
cd backend
python -m uvicorn main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 5.2 Register Schema (Optional - Auto-loads default)

If you need to register a custom schema:

```bash
cd ..
python register_schema.py
```

### 5.3 Use the Chatbot

1. Power BI Desktop should show the chatbot visual
2. Type queries like:
   - "Show ICU critical patients"
   - "Emergency department"
   - "Cardiology and Surgery patients"
   - "Stable patients"

---

## Step 6: Verify Everything Works

✅ Backend running on http://localhost:8000  
✅ Visual imported in Power BI  
✅ Data field bound to visual  
✅ Charts update when you type queries  

---

## File Structure

```
Power-BI-Bot/
├── backend/
│   ├── main.py                 # FastAPI server
│   ├── config.py               # Configuration
│   ├── requirements.txt         # Python dependencies
│   ├── modules/
│   │   ├── intent_parser.py     # LLM query parsing
│   │   ├── filter_applier.py    # Filter formatting
│   │   ├── semantic_resolver.py # Entity resolution
│   │   └── ...
│   ├── schemas/
│   │   └── hospital_schema.json # Default schema
│   └── .env                     # API keys (GITIGNORE)
│
├── PowerBIBotVisual/
│   ├── src/
│   │   ├── visual.ts            # Main visual code
│   │   └── ...
│   ├── capabilities.json        # Visual capabilities
│   ├── package.json             # Node dependencies
│   ├── pbiviz.json              # Visual config
│   └── dist/
│       └── *.pbiviz             # Packaged visual
│
├── sample_data/
│   └── hospital_data.csv        # Sample dataset
│
├── Hospital_Dashboard.pbix      # Example dashboard
├── register_schema.py           # Schema registration script
├── SETUP_GUIDE.md              # This file
└── README.md
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'fastapi'"
**Solution:**
```bash
pip install -r backend/requirements.txt
```

### Issue: "Groq API Key not found"
**Solution:**
1. Check `.env` file exists in `backend/` folder
2. Verify `GROQ_API_KEY=your_key` is set
3. Restart backend server

### Issue: "Filters not applying to charts"
**Solution:**
1. Ensure data field is bound to visual (drag field into visual)
2. Restart Power BI Desktop
3. Clear Power BI cache: `C:\Users\{USERNAME}\AppData\Local\Microsoft\Power BI Desktop\Cache`

### Issue: "Backend unavailable" in chatbot
**Solution:**
1. Verify backend running: http://localhost:8000/health
2. Check firewall allows localhost:8000
3. Restart backend with: `python -m uvicorn main:app --reload`

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| GROQ_API_KEY | - | Your Groq API key (required) |
| GROQ_MODEL | mixtral-8x7b-32768 | LLM model to use |
| BACKEND_PORT | 8000 | Backend server port |
| DEBUG | True | Enable debug logging |
| CORS_ORIGINS | ["*"] | Allowed CORS origins |

---

## Key Configuration Files

### `backend/config.py`
- Backend settings and API configuration

### `PowerBIBotVisual/capabilities.json`
- Visual data bindings and filter permissions

### `PowerBIBotVisual/pbiviz.json`
- Visual metadata and GUID

### `backend/schemas/hospital_schema.json`
- Default data schema (can be customized)

---

## Customization

### Change Backend Port
Edit `backend/config.py`:
```python
BACKEND_PORT = 9000  # Change from 8000
```

Then update `visual.ts`:
```typescript
private backendUrl: string = "http://localhost:9000";
```

### Add Custom Schema
Run:
```bash
python register_schema.py
```

Or modify `backend/schemas/hospital_schema.json`

### Customize Chatbot UI
Edit `PowerBIBotVisual/src/visual.ts` lines 38-150

---

## Common Queries

| Query | Expected Result |
|-------|-----------------|
| "Show ICU critical patients" | Filters: department=ICU, patient_condition=Critical |
| "Emergency department" | Filters: department=Emergency |
| "Stable patients" | Filters: patient_condition=Stable |
| "Cardiology and Surgery patients" | Filters: department=[Cardiology, Surgery] |
| "ICU Patients" | Filters: department=ICU |

---

## Support & Documentation

- **Groq API Docs**: https://console.groq.com/docs
- **Power BI Visuals API**: https://learn.microsoft.com/en-us/power-bi/developer/visuals/
- **FastAPI Docs**: http://localhost:8000/docs (when running)

---

## Next Steps

1. ✅ Clone repository
2. ✅ Install dependencies (Python + Node)
3. ✅ Configure `.env` with Groq API key
4. ✅ Build visual (`npm run package`)
5. ✅ Import visual in Power BI
6. ✅ Bind data field to visual
7. ✅ Start backend (`python -m uvicorn main:app --reload`)
8. ✅ Test queries in chatbot

**You're ready to go!** 🚀
