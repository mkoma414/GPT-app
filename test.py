import os
import json
import requests
import logging
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

# 環境変数の読み込み
bot_token = os.environ["SLACK_BOT_TOKEN"]
slack_signing_secret = os.environ["SLACK_SIGNING_SECRET"]
openai_api_key = os.environ["OPENAI_API_KEY"]

logging.warning(slack_signing_secret)

API_ENDPOINT = 'https://api.openai.com/v1/chat/completions'

# Flaskアプリケーションの設定
app = Flask(__name__)
slack_app = App(token=bot_token, signing_secret=slack_signing_secret)
handler = SlackRequestHandler(slack_app)

# メッセージイベントのリスナーを設定 
@slack_app.message("hello") 
def command_handler(body, say):
    text = body["event"]["text"]

    # ChatGPTによる応答の生成
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}"
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "system", "content": "You are a helpful assistant."},
                     {"role": "user", "content": f"{text}"}],
        "max_tokens": 2048,
        "n": 1,
        "stop": None,
        "temperature": 0.5,
    }

    response = requests.post(API_ENDPOINT, headers=headers, data=json.dumps(data))
    response = response.json()

    logging.warning(response)


    # Slackに返答を送信
    reply = response["choices"][0]["message"]["content"].strip()
    say(reply)

# Slackイベントのエンドポイント
@app.route("/slack/events", methods=["POST"])
def slack_events():
  test_message = request.json

  if ('challenge' in test_message):
    return {
      "statusCode": 200,
      "body": json.dumps({'challenge': test_message['challenge']})
    }

  return handler.handle(request)

if __name__ == "__main__":
    app.run(debug=True)