# 🧹 PaperWiper

A Flask-based tool for automated removal of student handwriting from scanned exam papers via image processing. Handles mixed Chinese/English content across all standard question formats.

---

## 📁 Project Structure

```
paper_wiper/
├── app.py              # Flask backend
├── engine.py           # CV pipeline: detection, masking, inpainting
├── requirements.txt    # Python dependencies
├── render.yaml         # Render.com deployment config
├── static/
│   └── index.html      # PWA frontend
├── uploads/            # Ephemeral PDF intake (auto-created)
└── outputs/            # Processed PDF output (auto-created)
```

---

## 🖥️ Local Development

```bash
git clone https://github.com/your-username/paper-wiper.git
cd paper-wiper
pip install -r requirements.txt
python app.py
```

Server runs at `http://localhost:5000`.

---

## 🌐 Deployment (Render.com)

The repo includes a `render.yaml` configuration for zero-config deployment.

1. Push the repository to GitHub
2. In Render, create a new **Web Service** and connect the repo
3. Render auto-detects `render.yaml` and builds the service
4. App is live at `https://paper-wiper.onrender.com` (or your chosen subdomain)

> First cold boot may take ~3 minutes on the free tier.

---

## 📱 PWA Installation (iOS)

Open the app in **Safari** → Share → **Add to Home Screen**.

---

## ⚙️ Engine Configuration

Detection behaviour is controlled by four constants at the top of `engine.py`:

| Constant              | Default | Notes                                      |
|-----------------------|---------|--------------------------------------------|
| `HANDWRITE_THRESHOLD` | `127`   | Binarisation threshold — lower picks up lighter pencil |
| `MIN_STROKE_AREA`     | `8`     | Minimum contour area to classify as a stroke |
| `DILATE_KERNEL`       | `3`     | Dilation kernel size for mask expansion    |
| `INPAINT_RADIUS`      | `5`     | Inpainting neighbourhood radius            |

Tune `HANDWRITE_THRESHOLD` and `MIN_STROKE_AREA` together — lowering both increases recall but raises false positives on pre-printed content.

---

## 📋 Supported Input Types

- Fill-in-the-blank (lined)
- Multiple choice (bubbles, ticks, circles)
- Open-answer and calculation boxes
- Chinese and English handwriting
- Numerals and mathematical symbols
