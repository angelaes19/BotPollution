# 🌫️ Bot Pollution

An interactive AI chatbot that reveals the digital carbon footprint of your conversations. Each message calculates estimated CO₂ emissions and visualizes them in equivalent smoked cigarettes.

Developed by **Carla Olivares Navarro** & **Angela Escudero Sanchez**, with collaboration from **Eric García Castro** (Programming) and **Marc Ortiz** (Industrial Engineering).

---

## 🚀 Features

- **Mistral AI Integration**: Powered by Mistral AI models (`mistral-large-latest` with fallback to `mistral-medium`).
- **Real-time Carbon Footprint**: Calculates grams of CO₂ and cigarette puffs per message.
- **Dynamic Interface**: Darkens progressively as accumulated CO₂ increases, with a daily usage limit modal.
- **Ready for Vercel**: Configured for deployment on Vercel as a Python Serverless Function.

---

## 🛠️ Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/angelaes19/BotPollution.git
   cd BotPollution
   ```

2. **Create and activate a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Create a `.env` file in the root directory:
   ```env
   MISTRAL_API_KEY=your_mistral_api_key_here
   ```

5. **Run the application:**
   ```bash
   python app.py
   ```
   Open your browser at `http://localhost:5000`.

---

## 🌐 Deploy to Vercel

1. Import this repository in [Vercel](https://vercel.com/angelaes19s-projects).
2. In **Environment Variables**, add:
   - `MISTRAL_API_KEY`: your Mistral AI API key.
3. Click **Deploy**.
