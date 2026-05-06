# 🚀 Complete Project Migration Guide

This guide provides step-by-step instructions on how to move your **Face Detection Project** from your current computer to a brand new one, using GitHub for your code, Docker for your database, and Conda for your Python environment.

---

## 🛑 PHASE 1: What to do on your CURRENT Computer

Before you leave your current computer, you need to make sure everything is backed up and saved.

### 1. Save your Code to GitHub
You need to make sure the latest changes (including `requirements.txt` and `docker-compose.yml`) are pushed to GitHub.
Open a terminal in your project folder and run:
```bash
git add .
git commit -m "Added requirements and docker-compose for migration"
git push origin main
```

### 2. Backup your Heavy/Ignored Files to a USB Drive
Because GitHub ignores large files, you must manually copy these to a USB Flash Drive or Google Drive:
- Copy the entire `models/` folder (where your DeepFace/ArcFace weights are stored).
- Copy any `*.pt`, `*.pth`, `*.weights`, or `*.onnx` files in your main folder.
- Copy your `data/` or `lfw_data/` folders if you want to keep your datasets.

---

## 💻 PHASE 2: Setting up the NEW Computer

Now, turn on your new computer and prepare the environment.

### 1. Install Required Software
You need to download and install three core pieces of software:
- **Git:** Download from `git-scm.com`
- **Anaconda (or Miniconda):** Download from `anaconda.com`
- **Docker Desktop:** Download from `docker.com` (Ensure it is running and you see the whale icon in your taskbar).

### 2. Bring your Code Over
Open a terminal/command prompt and clone your project:
```bash
git clone <your-github-repo-url>
cd Face_Detection_Project
```

### 3. Restore your Heavy Files
Plug in your USB drive and **paste the `models/` folder** and your datasets back into the `Face_Detection_Project` folder exactly where they were on your old computer.

---

## 🐘 PHASE 3: Starting the Database (The Easy Way)

Thanks to Docker, you don't need to install PostgreSQL or the `pgvector` extension.

1. Open a terminal inside the `Face_Detection_Project` folder.
2. Run this exact command:
   ```bash
   docker-compose up -d
   ```
3. *Wait a few seconds.* Docker will automatically download PostgreSQL, install `pgvector`, and set your username to `postgres` and password to `todeiei7101` as configured in your `database.py`.

---

## 🐍 PHASE 4: Setting up Python & Conda

Now we need to get Python ready so your webcam and GPU work perfectly.

1. Open the **Anaconda Prompt** (search for it in your Windows Start Menu).
2. Navigate to your project folder:
   ```bash
   cd path\to\Face_Detection_Project
   ```
3. Create a fresh Conda environment (replace `3.10` with your preferred Python version if needed):
   ```bash
   conda create -n face_detect python=3.10
   ```
4. Activate the environment:
   ```bash
   conda activate face_detect
   ```
5. Install all your required libraries using the file we generated earlier:
   ```bash
   pip install -r requirements.txt
   ```
*(Note: If the install fails on specific packages like `tf_keras`, you might need to install them manually via `pip install tf_keras tensorflow torch torchvision`).*

---

## 🌐 PHASE 5: Running the Web App

Everything is set up! Time to start the application.

1. Ensure your Conda environment is activated (`conda activate face_detect`).
2. Make sure your database tables are created. If your script handles this automatically, just run your standard launch command:
   ```bash
   python src/main.py
   ```
   *If you use uvicorn to start your web app directly, run:*
   ```bash
   uvicorn src.web_app:app --reload
   ```
3. Open your web browser and go to your application address (usually `http://localhost:8000` or `http://127.0.0.1:8000`).

🎉 **Congratulations! Your system is now running on the new computer!**
