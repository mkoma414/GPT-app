import os
import json
import requests
import logging
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

# 初期設定
bot_token = os.environ["SLACK_BOT_TOKEN"]
slack_signing_secret = os.environ["SLACK_SIGNING_SECRET"]
openai_api_key = os.environ["OPENAI_API_KEY"]

logging.basicConfig(level=logging.INFO)

API_ENDPOINT = 'https://api.openai.com/v1/chat/completions'

# Flaskアプリケーションの設定
app = Flask(__name__)
slack_app = App(token=bot_token, signing_secret=slack_signing_secret)
handler = SlackRequestHandler(slack_app)


# 辞書の検索用関数
def dict_search(d,key):
  if not d or not key:
      return None
  elif isinstance(d, dict):
      if key in d:
          return d.get(key)
      else:
          l = [dict_search(d.get(dkey),key) for dkey in d if isinstance(d.get(dkey),dict) or isinstance(d.get(dkey),list)]
          return [lv for lv in l if not lv is None].pop(0) if any(l) else None
  elif isinstance(d,list):
      li = [dict_search(e,key) for e in d if isinstance(e,dict) or isinstance(e,list)]
      return [liv for liv in li if not liv is None].pop(0) if any(li) else None
  else:
      return None

# Slackで通常メッセージが入力された場合の挙動
def normal_message_to_ChatGPT(body, say):
  text = body["event"]["text"]
  thread_ts = body["event"]["ts"]

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

  # Slackに返答を送信
  reply = response["choices"][0]["message"]["content"].strip()
  say(reply, thread_ts=thread_ts)


# Slackのスレッド内にメッセージが入力された場合の挙動
def thread_message_to_ChatGPT(body, say):
  text = body["event"]["text"]
  channel_id = body["event"]["channel"]
  thread_ts = body["event"]["thread_ts"]

  # スレッド内の全テキストを取得
  result = slack_app.client.conversations_replies(
    channel=channel_id,
    ts=thread_ts
  )

  thread_messages = result["messages"]

  messages_text = ""
  for message in thread_messages:
    print(f"message:{message}")

    if "bot_id" in message:
      text = message["text"]
      messages_text += f"Assistant: {text}\n"
    elif "user" in message:
      user = message["user"]
      text = message["text"]
      messages_text += f"User {user}: {text}\n"

  # ChatGPTによる応答の生成
  headers = {
      "Content-Type": "application/json",
      "Authorization": f"Bearer {openai_api_key}"
  }
  data = {
      "model": "gpt-3.5-turbo",
      "messages": [{"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": f"{messages_text}"}],
      "max_tokens": 2048,
      "n": 1,
      "stop": None,
      "temperature": 0.5,
  }

  response = requests.post(API_ENDPOINT, headers=headers, data=json.dumps(data))
  response = response.json()

  # Slackに返答を送信
  reply = response["choices"][0]["message"]["content"].strip()
  say(reply, thread_ts=thread_ts)


# 通常メッセージに対応するイベント 
@slack_app.message() 
def command_handler(body, say):
  # 通常メッセージかスレッド内メッセージかで処理を分岐
  if "thread_ts" in body["event"]:
    thread_message_to_ChatGPT(body, say)
  else:
    normal_message_to_ChatGPT(body, say)


# スラッシュコマンドmenusが入力された時の処理
@slack_app.command("/menus")
def repeat_text(ack, respond, command):
  ack()

  blocks = [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*使用するプロンプトを選択してください*"
      },
      "accessory": {
        "type": "radio_buttons",
        "options": [
          {
            "text": {
              "type": "plain_text",
              "text": "思考の壁打ち"
            },
            "value": "option1"
          },
          {
            "text": {
              "type": "plain_text",
              "text": "Midjourney用のプロンプト作成"
            },
            "value": "option2"
          },
          {
            "text": {
              "type": "plain_text",
              "text": "Twitter投稿文の作成"
            },
            "value": "option3"
          }
        ],
        "action_id": "radio_buttons_action"
      }
    },
    {
      "type": "actions",
      "elements": [
        {
          "type": "button",
          "text": {
            "type": "plain_text",
            "text": "Click me!"
          },
          "action_id": "button_click",
          "value": "button_value"
        }
      ]
    }
  ]

  respond(blocks=blocks)


# Slackが行うバリデーション用
@app.route('/', methods=['POST'])
def url_validation():
  test_message = request.json

  if ('challenge' in test_message):
    return {
      "statusCode": 200,
      "body": json.dumps({'challenge': test_message['challenge']})
    }

  return handler.handle(request)


# Slackでボタンがクリックされた時の処理
@slack_app.action("button_click")
def action_button_click(body, ack, say):
  ack()

  selection = dict_search(body, "value")
  print(selection)
  say(selection)


# Slackイベントのエンドポイント
@app.route('/slack/events', methods=['POST'])
def slack_events():
  return handler.handle(request)

if __name__ == "__main__":
  app.run(port=5001, debug=True)

