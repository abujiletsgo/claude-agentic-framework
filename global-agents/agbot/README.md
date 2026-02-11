# AGBot Specialized Agents

AGBot-specific agents for Polymarket copy-trading analysis.

## Available Agents

### 1. **trader-data-validator** (Haiku - Fast & Cost-Effective)
- **Purpose**: Validate imported trader data quality
- **Tools**: Read, Grep, Bash
- **Use Cases**:
  - Check schema compliance (35 required columns)
  - Detect missing/null values
  - Flag suspicious patterns and outliers
  - Validate sport tagging quality

### 2. **performance-analyzer** (Sonnet - Balanced)
- **Purpose**: Analyze trader performance metrics
- **Tools**: Read, Bash, Write
- **Use Cases**:
  - Calculate ROI, win rates, Sharpe ratios
  - Sport-specific performance breakdown
  - Market type profitability (MoneyLine/Spread/O-U)
  - Temporal pattern analysis
  - Risk metrics (max drawdown, etc.)

### 3. **market-researcher** (Sonnet - Balanced)
- **Purpose**: Research Polymarket ecosystem and betting dynamics
- **Tools**: WebSearch, WebFetch, Write
- **Use Cases**:
  - Polymarket platform mechanics
  - Liquidity and market efficiency analysis
  - Competitive landscape research
  - API capabilities exploration
  - Sports betting fundamentals

### 4. **strategy-advisor** (Sonnet - Balanced)
- **Purpose**: Generate copy-trading strategy recommendations
- **Tools**: Read, Bash, Write
- **Use Cases**:
  - Trader selection criteria
  - Sport/market filtering rules
  - Bet sizing optimization (Kelly criterion)
  - Risk management parameters
  - Multi-trader portfolio construction

### 5. **risk-assessor** (Sonnet - Balanced)
- **Purpose**: Evaluate trader risk profiles
- **Tools**: Read, Bash, Write
- **Use Cases**:
  - Max drawdown and recovery analysis
  - Volatility metrics (Sharpe ratio, std dev)
  - Value at Risk (VaR) calculations
  - Correlation analysis
  - Minimum capital requirements

### 6. **combo-optimizer** (Sonnet - Balanced)
- **Purpose**: Find optimal trader+sport+market+size combinations
- **Tools**: Read, Bash, Write
- **Use Cases**:
  - Rank all combinations by risk-adjusted returns
  - Statistical significance filtering (min 20 trades)
  - Consistency testing across time periods
  - Diversified portfolio construction
  - Backtest validation

### 7. **data-ingestion-helper** (Haiku - Fast & Cost-Effective)
- **Purpose**: Assist with importing trader data
- **Tools**: Read, Bash, Write, Edit
- **Use Cases**:
  - File format detection and validation
  - Schema mapping and transformation
  - Sport normalization and market classification
  - Database insertion guidance
  - Error handling and troubleshooting

## Usage Examples

```bash
# Validate trader data
"Use trader-data-validator to check drpufferfish data quality"

# Analyze performance
"Launch performance-analyzer for drpufferfish across all sports"

# Research markets
"Use market-researcher to explain how Polymarket spread markets work"

# Get strategy recommendations
"Use strategy-advisor to build a copy-trading plan for NHL and NBA"

# Assess risk
"Launch risk-assessor to evaluate drpufferfish risk profile"

# Optimize combinations
"Use combo-optimizer to find top 20 combos by Sharpe ratio"

# Import new data
"Use data-ingestion-helper to import newtrader_raw.xlsx"
```

## Agent Selection Guide

| Task Type | Recommended Agent | Model | Speed | Cost |
|-----------|------------------|-------|-------|------|
| Data validation | trader-data-validator | Haiku | Fast | $ |
| Performance analysis | performance-analyzer | Sonnet | Medium | $$ |
| Market research | market-researcher | Sonnet | Medium | $$ |
| Strategy creation | strategy-advisor | Sonnet | Medium | $$ |
| Risk assessment | risk-assessor | Sonnet | Medium | $$ |
| Combo optimization | combo-optimizer | Sonnet | Medium | $$ |
| Data import help | data-ingestion-helper | Haiku | Fast | $ |

## Integration with AGBot CLI

These agents complement AGBot's CLI commands:
- `agbot import` → data-ingestion-helper validates
- `agbot stats` → performance-analyzer interprets
- `agbot rank` → combo-optimizer expands on

## Commands Available

Use these slash commands to invoke agents quickly:
- `/validate-trader` → trader-data-validator
- `/analyze-performance` → performance-analyzer
- `/research-markets` → market-researcher
- `/suggest-strategy` → strategy-advisor
- `/assess-risk` → risk-assessor
- `/optimize-combos` → combo-optimizer
- `/import-trader` → data-ingestion-helper
