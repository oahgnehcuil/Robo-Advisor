# DAT.co Financial Monitor

A web-based platform for monitoring and visualizing Digital Asset Treasury (DAT) company financial indicators, focusing on MicroStrategy (MSTR) Modified Net Asset Value (MNAV) and premium indicators.

## Features

- **Real-time MNAV Calculation**: Calculates Modified Net Asset Value for MicroStrategy based on Bitcoin holdings
- **Premium/Discount Analysis**: Shows the premium or discount of MSTR stock relative to its MNAV
- **Historical Time-Series Data**: Stores and displays 30 days of historical data
- **Interactive Charts**: Visualizations for premium trends and price comparisons
- **Auto-updates**: Daily automatic data updates via GitHub Actions
- **Manual Updates**: On-demand data refresh capability

## Architecture

### Backend (Flask)
- **app.py**: Main Flask application with API endpoints
- **data_updater.py**: Standalone script for data updates
- **mnav_data.json**: JSON file storing historical data

### Frontend
- **templates/index.html**: Responsive web interface with Chart.js visualizations
- Real-time data fetching from backend APIs
- Interactive charts for premium and price trends

### API Endpoints

- `GET /`: Main dashboard page
- `GET /api/current`: Current MNAV data
- `GET /api/historical`: Historical time-series data
- `GET /api/update`: Manual data update trigger

## Installation & Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**:
   ```bash
   python app.py
   ```

3. **Access the Dashboard**:
   Open http://localhost:5000 in your browser

## Data Sources

- **MicroStrategy (MSTR)**: Stock price and financial data via Yahoo Finance
- **Bitcoin (BTC-USD)**: Bitcoin price via Yahoo Finance
- **Holdings Data**: Based on publicly disclosed Bitcoin holdings (252,220 BTC as of 2026)

## Calculations

### MNAV Formula
```
MNAV = Total Equity + (Bitcoin Holdings × Bitcoin Price)
```

### Premium Formula
```
Premium (%) = ((Market Cap / MNAV) - 1) × 100
```

## Deployment

### GitHub Actions Auto-Update
The system includes automatic daily updates via GitHub Actions:
- **Schedule**: Daily at 00:00 UTC (08:00 Taiwan Time)
- **Manual Trigger**: Available via GitHub Actions dashboard
- **Data Persistence**: Historical data stored in `mnav_data.json`

### Manual Updates
- Use the "手動更新數據" button on the dashboard
- Run `python data_updater.py` directly
- Call `/api/update` endpoint

## File Structure

```
hw2/
├── app.py                 # Main Flask application
├── data_updater.py        # Standalone data update script
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html        # Main dashboard template
├── mnav_data.json        # Historical data storage (auto-generated)
├── update_stats.yml      # GitHub Actions workflow
└── README.md             # This file
```

## Monitoring Indicators

### Primary Indicator: MNAV Premium
- **Purpose**: Measures market sentiment relative to intrinsic value
- **Interpretation**:
  - Positive Premium: Market values MSTR above its Bitcoin holdings
  - Negative Premium (Discount): Market undervalues MSTR relative to Bitcoin

### Relationship with Bitcoin
The MNAV premium indicator reflects:
1. **Market Sentiment**: Investor confidence in MicroStrategy's Bitcoin strategy
2. **Leverage Effect**: How effectively MSTR uses leverage to acquire Bitcoin
3. **Premium Decay**: Changes in premium over time indicate market efficiency

## Technical Notes

- Data updates are limited to once per day to avoid API rate limits
- Historical data is limited to 30 days for performance
- Error handling includes fallback mechanisms for missing financial data
- Charts auto-refresh every 5 minutes when the dashboard is open

## Future Enhancements

- Additional DAT companies (Coinbase, Marathon Digital, etc.)
- AI-powered insights and trend analysis
- Alert system for significant premium changes
- Export functionality for data analysis
