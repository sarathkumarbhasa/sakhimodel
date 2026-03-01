#!/usr/bin/env python3
"""
Webhook setup script.
Run once after deployment to register your Render URL with Telegram.

Usage:
    python scripts/setup_webhook.py \
        --token YOUR_BOT_TOKEN \
        --url https://your-app.onrender.com \
        --action set
"""

import argparse
import asyncio
import sys

import httpx


async def set_webhook(token: str, app_url: str) -> None:
    webhook_url = f"{app_url}/webhook/telegram"
    api_url = f"https://api.telegram.org/bot{token}/setWebhook"

    payload = {
        "url": webhook_url,
        "allowed_updates": ["message"],
        "drop_pending_updates": True,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(api_url, json=payload)

    data = response.json()
    if data.get("ok"):
        print(f"✅ Webhook set successfully!")
        print(f"   URL: {webhook_url}")
    else:
        print(f"❌ Failed to set webhook: {data}")
        sys.exit(1)


async def get_webhook_info(token: str) -> None:
    api_url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(api_url)
    print("Webhook info:", response.json())


async def delete_webhook(token: str) -> None:
    api_url = f"https://api.telegram.org/bot{token}/deleteWebhook"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(api_url, json={"drop_pending_updates": True})
    print("Delete result:", response.json())


def main():
    parser = argparse.ArgumentParser(description="Manage Sakhi Telegram webhook")
    parser.add_argument("--token", required=True, help="Telegram bot token")
    parser.add_argument("--url", help="Render app base URL (e.g. https://sakhi.onrender.com)")
    parser.add_argument("--action", choices=["set", "info", "delete"], default="set")

    args = parser.parse_args()

    if args.action == "set":
        if not args.url:
            print("--url is required for 'set' action")
            sys.exit(1)
        asyncio.run(set_webhook(args.token, args.url))
    elif args.action == "info":
        asyncio.run(get_webhook_info(args.token))
    elif args.action == "delete":
        asyncio.run(delete_webhook(args.token))


if __name__ == "__main__":
    main()
