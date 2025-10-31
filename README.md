# ♻️ EcoSort - AI-Powered Waste Classification

EcoSort is an intelligent web application that uses Google's Gemini AI to classify waste items into categories (biodegradable/non-biodegradable and wet/dry) and provides appropriate disposal advice.

## 🌟 Features

- **AI-Powered Classification**: Uses Google's Gemini AI for accurate waste classification
- **Dual Classification**: Categorizes waste by both biodegradability and moisture content
- **Responsive Design**: Works on desktop and mobile devices
- **Privacy-Focused**: No data is stored; all processing happens locally
- **Educational**: Provides disposal advice and environmental tips

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Google Gemini API key (get one from [Google AI Studio](https://aistudio.google.com/app/apikey))

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ecosort.git
   cd ecosort
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root and add your Google Gemini API key:
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```

## 🖥️ Running the Application

1. Start the Streamlit app:
   ```bash
   streamlit run app.py
   ```

2. Open your browser and navigate to the URL shown in the terminal (usually `http://localhost:8501`)

3. Upload an image of a waste item and click "Classify Waste"

## 🏗️ Project Structure

```
waste-segregation-app/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── .env.example          # Example environment variables
├── .gitignore            # Git ignore file
└── src/
    ├── model.py          # Handles Gemini API integration
    └── prediction.py     # Formats classification and disposal logic
```

## 🔒 Security

- API keys are stored in `.env` (not committed to version control)
- Images are processed locally and not stored
- No personal data is collected
- Rate limiting is recommended for production use

## 🌍 Environmental Impact

By helping users properly segregate waste, EcoSort aims to:
- Reduce contamination in recycling streams
- Increase composting of organic waste
- Educate users about proper waste disposal
- Contribute to a cleaner, more sustainable planet

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Made with ♻️ for a cleaner planet
</p>
