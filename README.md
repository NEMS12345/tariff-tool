# Tariff Tool

A Streamlit application for analyzing and comparing energy tariffs.

## Setup

1. Clone the repository:
   ```
   git clone https://github.com/your-username/tariff-tool.git
   cd tariff-tool
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Update `.env` with your Supabase credentials

4. Run the application:
   ```
   python -m streamlit run tariff_tool_v3.py
   ```

## Environment Variables and Secrets

This application uses environment variables and Streamlit secrets to store sensitive information like API credentials.

### Local Development

For local development, you can use a `.env` file:
1. Copy `.env.example` to `.env`
2. Replace the placeholder values with your actual Supabase credentials

### Cloud Deployment

For Streamlit Cloud deployment, you need to set up secrets in the Streamlit Cloud dashboard:

1. Go to your app dashboard on Streamlit Cloud
2. Navigate to the "Settings" tab
3. Under "Secrets", add the following configuration:

```toml
[supabase]
url = "your_supabase_url_here"
key = "your_supabase_key_here"
```

4. Replace the placeholder values with your actual Supabase credentials
5. Save the changes and redeploy your app

## Features

- Energy tariff analysis and comparison
- Visualization of energy pricing data
- Competitor price comparison
- OPEX budget analysis
