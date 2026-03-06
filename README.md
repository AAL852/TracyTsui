# 🧹 PaperWiper

Remove student handwriting from scanned exam papers automatically.
Supports Chinese + English papers, all question types.

---

## 📁 Project Structure

```
paper_wiper/
├── app.py              ← Flask backend
├── engine.py           ← Handwriting detection + removal
├── requirements.txt    ← Python dependencies
├── render.yaml         ← Render.com deployment config
├── static/
│   └── index.html      ← PWA frontend
├── uploads/            ← Temp uploaded PDFs (auto-created)
└── outputs/            ← Temp cleaned PDFs (auto-created)
```

---

## 🖥️ Run Locally (Windows)

### Step 1 — Install Python dependencies
Open Git Bash or PowerShell:
```bash
cd path/to/paper_wiper
pip install -r requirements.txt
```

### Step 2 — Start the server
```bash
python app.py
```

### Step 3 — Open in browser
```
http://localhost:5000
```

---

## 🌐 Deploy Free Online (Render.com)

### Step 1 — Push to GitHub
1. Create a free account at github.com
2. Create a new repository called `paper-wiper`
3. Upload all files in this folder to the repository

### Step 2 — Deploy on Render
1. Create a free account at render.com
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Render auto-detects render.yaml — click "Deploy"
5. Wait ~3 minutes for first deploy

### Step 3 — Share with teachers
Your app will be live at:
```
https://paper-wiper.onrender.com
```
(or whatever name you chose)

---

## 📱 Install on iPhone (PWA)

1. Open the app URL in **Safari**
2. Tap the **Share** button (box with arrow)
3. Scroll down and tap **"Add to Home Screen"**
4. Tap **"Add"**

The app now appears on your home screen like a native app!

---

## ⚙️ Tuning Accuracy

Edit `engine.py` constants at the top:

| Constant | Default | Effect |
|---|---|---|
| `HANDWRITE_THRESHOLD` | 127 | Lower = detect lighter pencil |
| `MIN_STROKE_AREA` | 8 | Lower = detect smaller marks |
| `DILATE_KERNEL` | 3 | Higher = wipe wider around strokes |
| `INPAINT_RADIUS` | 5 | Higher = better line restoration |

---

## 📋 Supported Paper Types

- ✅ Fill-in-the-blank on lines
- ✅ Multiple choice (filled/ticked bubbles)
- ✅ Open answer boxes (calculation work)
- ✅ Circled answers
- ✅ Chinese handwriting
- ✅ English handwriting
- ✅ Numbers and symbols
