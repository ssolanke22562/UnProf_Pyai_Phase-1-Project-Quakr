# Guide: Deploying Quakr to Render (24/7 Free Hosting)

This guide shows you how to host the **Quakr** dashboard permanently on the cloud (for free) so it remains accessible anytime without running local tunnels.

---

## 🚀 Deployment Steps (Render)

Render is a modern cloud hosting platform with a free tier that is perfect for Python/FastAPI web services.

### 1. Create a Render Account
1. Go to [Render](https://render.com) and click **Sign Up**.
2. Sign in using your **GitHub** account (this makes connecting your repository very easy).

### 2. Create a New Web Service
1. Click the **New +** button in the top right of the Render Dashboard.
2. Select **Web Service**.
3. Choose **Build and deploy from a Git repository**.

### 3. Connect your Repository
1. You will see a list of your GitHub repositories. Find and click **Connect** next to `UnProf_Pyai_Phase-1-Project-Quakr`.

### 4. Configure Web Service Settings
Fill in the configuration fields with the following values:

| Field | Value |
| :--- | :--- |
| **Name** | `quakr-seismic-dashboard` *(or any unique name you like)* |
| **Region** | Choose the one closest to you (e.g., `Singapore` or `Oregon`) |
| **Branch** | `main` |
| **Language** | `Python` (it should detect this automatically) |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app:app --host 0.0.0.0 --port $PORT` |

### 5. Select the Free Instance Type
- Scroll down to the Instance Types and select the **Free** tier.
- Click **Deploy Web Service** at the bottom of the page.

---

## ⚡ What Happens Next?
1. Render will fetch the code from your GitHub repository, install the dependencies, and start the FastAPI server.
2. Once the build is complete (usually takes 2-3 minutes), Render will provide a public URL like:
   `https://quakr-seismic-dashboard.onrender.com`
3. This URL is **permanent** and will open successfully for anyone.

> [!NOTE]
> **Free Tier Cold Starts:** Free instances on Render spin down (go to sleep) if they don't receive traffic for 15 minutes. When someone visits the URL after a spin-down, it will take 30–50 seconds for the server to wake up and load the page. Once awake, it will be instant.

## 🔄 Automatic Redeployment
Every time you push a new commit to your GitHub repository (`git push`), Render will automatically detect the change, rebuild your application, and update the live website!
