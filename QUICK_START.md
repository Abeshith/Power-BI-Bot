# Power BI Bot - Quick Setup Guide

**Time Required:** ~15 minutes (first time)

---

## Prerequisites

- Git installed
- Python 3.8+ installed
- Node.js installed
- Power BI Desktop installed
- Groq API key (free from https://console.groq.com)

---

## Step 1: Clone Repository

```bash
git clone https://github.com/Abeshith/Power-BI-Bot.git
cd Power-BI-Bot
```

---

## Step 2: Setup Backend

```bash
cd backend
pip install -r requirements.txt
```

### Create `.env` File

Create a file named `.env` in the `backend/` folder with:

```
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=mixtral-8x7b-32768
DEBUG=True
BACKEND_PORT=8000
CORS_ORIGINS=["*"]
```

**Get your API Key:**
1. Go to https://console.groq.com
2. Sign up/login
3. Copy your API key
4. Paste in `.env`

---

## Step 3: Start Backend Server

```bash
python -m uvicorn main:app --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

✅ **Leave this terminal running!**

---

## Step 4: Setup Visual (New Terminal)

Open a **new terminal/PowerShell window** and run:

```bash
cd PowerBIBotVisual
npm install
npm run package
```

**Expected output:**
```
done   Build completed successfully
```

Creates `.pbiviz` file at: `PowerBIBotVisual\dist\powerBIBotVisual99999999999999999999.1.0.0.x.pbiviz`

---

## Step 5: Import Visual in Power BI Desktop

1. **Open Power BI Desktop** with your dashboard
2. Go to **Home** tab
3. Click **Get More Visuals** (ribbon)
4. Select **From a file**
5. Navigate to: `PowerBIBotVisual\dist\` folder
6. Select the `.pbiviz` file
7. Click **Open** → **Import**

---

## Step 6: Bind Data Field to Visual

1. Click on the **chatbot visual** in your dashboard
2. Look at **Fields pane** (right side)
3. **Drag any field** from your data into the visual
   - Example: Drag `department` field into the visual

✅ **This step is CRITICAL!** Without it, filters won't work.

---

## Step 7: Test the Bot

In the chatbot, type queries like:

```
Show ICU critical patients
```

```
Emergency department
```

```
Stable patients
```

```
Cardiology and Surgery patients
```

**Expected result:**
- Bot responds with applied filters
- All charts on dashboard update instantly ✅

---

## Troubleshooting

### "Backend unavailable" Error
- Check backend terminal is running: `python -m uvicorn main:app --reload`
- Verify: http://localhost:8000/health in browser
- Restart backend if needed

### "Groq API Key not found"
- Verify `.env` file exists in `backend/` folder
- Check `GROQ_API_KEY=your_key` is set correctly
- Restart backend

### Charts Not Updating
- Ensure data field is **bound to visual** (drag field into visual)
- Restart Power BI Desktop
- Clear cache: `C:\Users\{USERNAME}\AppData\Local\Microsoft\Power BI Desktop\Cache`

### "npm: command not found"
- Node.js not installed: https://nodejs.org/
- Restart terminal after installing

### "pip: command not found"
- Python not installed: https://www.python.org/
- Restart terminal after installing

---

## File Structure

```
Power-BI-Bot/
├── backend/
│   ├── main.py              (FastAPI server)
│   ├── modules/             (Query parsing, filtering logic)
│   ├── requirements.txt      (Python dependencies)
│   └── .env                  (API keys - CREATE THIS)
│
├── powerBIBotVisual/
│   ├── src/
│   │   └── visual.ts         (Chatbot UI)
│   ├── capabilities.json
│   ├── package.json
│   ├── pbiviz.json
│   └── dist/                 (Generated .pbiviz file)
│
├── SETUP_GUIDE.md
└── .gitignore
```

---

## Environment Variables Explained

| Variable | Value | Description |
|----------|-------|-------------|
| `GROQ_API_KEY` | your_key_here | Your Groq API key (required) |
| `GROQ_MODEL` | mixtral-8x7b-32768 | LLM model to use |
| `BACKEND_PORT` | 8000 | Backend server port |
| `DEBUG` | True | Enable debug logging |
| `CORS_ORIGINS` | ["*"] | Allow all origins (dev only) |

---

## Common Queries

Try these queries to test:

```
Show ICU critical patients
```

```
Emergency department
```

```
Stable patients
```

```
Surgery patients
```

```
Cardiology and Surgery patients
```

```
ICU Patients
```

---

## What's Happening (Behind the Scenes)

1. You type query in chatbot
2. Custom visual sends to backend API
3. Backend sends to Groq LLM
4. LLM parses and extracts filters
5. Backend returns filter JSON
6. Custom visual applies filters to all charts
7. Power BI updates dashboard instantly

---

## Support

- **Groq API Docs:** https://console.groq.com/docs
- **Power BI Visuals:** https://learn.microsoft.com/en-us/power-bi/developer/visuals/
- **FastAPI Docs:** http://localhost:8000/docs (when running)

---

## Quick Commands Reference

```bash
# Clone
git clone https://github.com/Abeshith/Power-BI-Bot.git && cd Power-BI-Bot

# Backend setup
cd backend && pip install -r requirements.txt

# Start backend
python -m uvicorn main:app --reload

# Visual setup (new terminal)
cd powerBIBotVisual && npm install && npm run package

# Check backend health
curl http://localhost:8000/health
```

---

## ✅ Checklist

- [ ] Cloned repository
- [ ] Created `.env` with Groq API key
- [ ] Backend running on port 8000
- [ ] Visual packaged (.pbiviz created)
- [ ] Visual imported in Power BI
- [ ] Data field bound to visual
- [ ] Tested with sample query
- [ ] Charts updated successfully

---

## Done! 🎉

Your Power BI Bot is ready to use! Type questions about your data and watch the charts filter instantly.
