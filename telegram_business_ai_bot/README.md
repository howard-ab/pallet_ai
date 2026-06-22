# Telegram Business AI Bot

A demo MVP Telegram bot for a small business that sells dried fruits, apricots, nuts, raisins, dates, and gift boxes.

The bot helps customers browse a product catalog, ask product questions, and receive short AI-powered answers through the Hugging Face Inference API. The AI model is hosted externally and does not run locally.

## Folder structure

```text
telegram_business_ai_bot/
    bot/
        __init__.py
        main.py
        config.py
        keyboards.py
        catalog.py
        ai_service.py
        handlers.py
    .env.example
    requirements.txt
    README.md
```

## Requirements

- Python 3.10+
- Telegram bot token from BotFather
- Hugging Face API token

## Install dependencies

```bash
cd telegram_business_ai_bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configure environment variables

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Then fill in real values:

```env
TELEGRAM_BOT_TOKEN=your_real_telegram_bot_token
HUGGINGFACE_API_TOKEN=your_real_huggingface_api_token
HUGGINGFACE_MODEL=Qwen/Qwen2.5-Coder-3B-Instruct
SHOP_WEBAPP_URL=https://howard-ab.github.io/pallet_ai/webapp/
SHOP_CHANNEL_URL=https://t.me/your_channel
```

`HUGGINGFACE_MODEL` is configurable. By default, the project uses a small Qwen instruct model that is available through Hugging Face Inference Providers:

```text
Qwen/Qwen2.5-Coder-3B-Instruct
```

## Run the bot

```bash
cd telegram_business_ai_bot
source .venv/bin/activate
python -m bot.main
```

Open your Telegram bot and send `/start`.

## Telegram Mini App

The project already contains a ready-to-deploy Telegram Mini App in `webapp/`.

GitHub Pages deployment is configured in:

```text
.github/workflows/deploy-telegram-webapp.yml
```

How to publish it:

1. Push the repository to GitHub.
2. Open GitHub -> Settings -> Pages.
3. In `Build and deployment`, choose `GitHub Actions`.
4. Push to `main` or `feature_bot`, or run the workflow manually in `Actions`.
5. After deployment, the Mini App will be available at:

```text
https://howard-ab.github.io/pallet_ai/webapp/
```

Then set the same URL in `.env`:

```env
SHOP_WEBAPP_URL=https://howard-ab.github.io/pallet_ai/webapp/
```

If you want to disable Mini App opening in the bot, leave:

```env
SHOP_WEBAPP_URL=
```

## Features

- Main menu with Catalog, Ask AI, About business, and Contact manager.
- Product catalog grouped by categories:
  - Dried fruits
  - Apricots
  - Nuts
  - Raisins
  - Dates
  - Gift boxes
- Category navigation with a Back to menu button.
- AI question mode using Hugging Face Inference API.
- Friendly fallback message when the external AI API is unavailable.
- Local JSONL session history in `sessions/` and technical logs in `logs/`.
- No database required for the MVP.

## Example use cases for small and medium businesses

- Answer common product questions automatically.
- Recommend dried fruits, nuts, and gift boxes for different customer needs.
- Explain differences between products, origins, weights, and prices.
- Reduce manager workload before order confirmation.
- Demo how AI can support customer communication in Telegram.

## Future improvements

- CRM integration
- Order tracking
- Payments
- Analytics dashboard
- Multilingual support
- Product recommendations based on customer behavior
