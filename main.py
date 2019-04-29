from __future__ import unicode_literals
from flask import Blueprint, request
import json
import logging
import requests
import random
import sqlite3
import os.path
import uuid
import copy


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "users.db")

sample_item =    {
    "tag": "li",
    "children": [
     ""
    ]
   }

sample_page = [
 {"tag": "aside",
  "children": [
   {"tag": "strong",
    "children": [
     "Ингредиенты"
    ]
   }
  ]
 },
 {"tag": "ol",
  "children": []
 },
 {"tag": "aside",
  "children": [
   {
    "tag": "strong",
    "children": [
     "Приготовление"
    ]
   }
  ]
 },
 {"tag": "ol",
  "children": []
 },
 {"tag": "p",
  "children": [
   "\nРецепт создан с помощью навыка для Алисы ",
   {
    "tag": "strong",
    "children": [
     {
      "tag": "em",
      "children": [
       "YaGraph"
      ]
     }
    ]
   }
  ]
 }
]

answers_dictionary = {
    "unknown": ["Я не поняла. Скажите помощь", "Такой команды нет. Скажите помощь", "Ой, команда затерялась. Скажите помощь"],
    "invalid": ["Давайте не будем ругаться, а вы введете валидные данные", "Соблюдайте правила!"],
    "start_reg": ["Итак, поехали! Как вас зовут?", "Ваше имя?"],
    "finish_reg": ["Ура, вы зарегестрировались!", "Регистрация прошла успешно!", "Пять минут, полет нормальный!"],
    "canceled": ["Отменено", "Операция прервана!", "Вы безжалостно убили операцию"],
    "authed_err": ["Вы уже авторизованы", "Второй раз авторизоваться не получится"],
    "reg_later": ["Регистрация потом"], # уже все найс, я не забил
    "finish_auth": ["Ура, вы авторизовались!", "Авторизация прошла успешно!", "Пять минут, полет нормальный!"],
    "auth_first": ["Сначала авторизуйтесь", "Войдите в аккаунт", "Скажите авторизация"]
}

commands_dictionary = {
    "cancel": ["отмена", "хватит", "не надо", "завершить", "назад", "стоп"],
    "register": ["зарегестрироваться", "создать аккаунт", "стать участником", "регистрация"],
    "help": ["помощь", "как", "помоги"],
    "auth": ["авторизация", "войти", "авторизоваться"],
    "create": ["создать страницу", "создать рецепт", "новый рецепт", "добавить рецепт", "давай готовить"]
}

additional_dictionary = {
    "finish_ing": ["все", "конец", "достаточно", "хватит", "это все", "вроде все"],
    "change_ing": ["ой", "ой нет", "изменить", "не так", "поменять"]
}

def validate_pass(req):
    user_id = req['session']['user_id']
    name = sessionStorage[user_id]["process"]["details"]["login"]
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE name = :name AND passphrase = :passphrase", {"name": name, "passphrase": req["request"]["original_utterance"].lower()})
    a = cursor.fetchall()
    conn.close()
    if a:
        return False
    return req["request"]["original_utterance"].lower()

def validate_pass_auth(req):
    user_id = req['session']['user_id']
    name = sessionStorage[user_id]["process"]["details"]["login"]
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE name = :name AND passphrase = :passphrase", {"name": name, "passphrase": req["request"]["original_utterance"].lower()})
    a = cursor.fetchall()
    conn.close()
    if not a:
        return False
    return req["request"]["original_utterance"].lower()

def validate_login(req):
    name = req["request"]["nlu"]["entities"]
    if name and name[0]["type"] == "YANDEX.FIO" and name[0]["value"]["first_name"]:
        name = name[0]["value"]["first_name"].capitalize()
        return name
    return False

def handle_login_auth(name, req, res):
    user_id = req['session']['user_id']
    sessionStorage[user_id]["process"]["details"]["login"] = name
    res['response']['text'] = "Прекрасно, " + name + "! Произнесите кодовую фразу или скажите отмена"
    return res

def handle_login(name, req, res):
    user_id = req['session']['user_id']
    sessionStorage[user_id]["process"]["details"]["login"] = name
    res['response']['text'] = "Прекрасно, " + name + "! Придумайте кодовую фразу. Если ошибка, то попробуйте другую фразу"
    return res

def handle_pass(passphrase, req, res):
    user_id = req['session']['user_id']
    name = sessionStorage[user_id]["process"]["details"]["login"]
    sessionStorage[user_id]["process"]["details"]["authed"] = True
    sessionStorage[user_id]["process"]["details"]["pass"] = passphrase
    res["response"]["text"] = random.choice(answers_dictionary["finish_reg"])
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (id, name, passphrase) VALUES (:id, :name, :passphrase)", {"id" : str(uuid.uuid4())[:8], "name": name, "passphrase": passphrase})
    conn.commit()
    conn.close()
    return res

def handle_pass_auth(passphrase, req, res):
    user_id = req['session']['user_id']
    sessionStorage[user_id]["process"]["details"]["authed"] = True
    sessionStorage[user_id]["process"]["details"]["pass"] = passphrase
    res["response"]["text"] = random.choice(answers_dictionary["finish_auth"])
    return res

def validate_true(req):
    return req["request"]["original_utterance"].lower().capitalize()

def create_page_handler(title, req, res):
    user_id = req['session']['user_id']
    name = sessionStorage[user_id]["process"]["details"]["login"]
    sessionStorage[user_id]["process"]["details"]["ingredients"] = []
    a = create_page(title, name)
    sessionStorage[user_id]["process"]["details"]["page_url"] = a["result"]["url"]
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE name = :name AND passphrase = :passphrase", {"name": name, "passphrase": sessionStorage[user_id]["process"]["details"]["pass"]})
    owner_id = cursor.fetchall()[0][0]
    cursor.execute("INSERT INTO pages (url, title, owner_id) VALUES (:url, :title, :owner_id)", {"url" : a["result"]["url"], "title": title, "owner_id": owner_id})
    conn.commit()
    conn.close()
    res["response"]["text"] = f"Страница {title} создана. Сколько ингредиентов?"
    return res

def validate_indredient(req):
    user_id = req['session']['user_id']
    ingredient = req["request"]["original_utterance"].lower().capitalize()
    if len(sessionStorage[user_id]["process"]["details"]["ingredients"]) == sessionStorage[user_id]["process"]["details"]["amount_ing"] - 1:
        if not sessionStorage[user_id]["process"]["details"]["ingredients"]:
            return False
        sessionStorage[user_id]["process"]["details"]["ingredients"].append(ingredient)
        data = sessionStorage[user_id]["process"]["details"]["ingredients"]
        sessionStorage[user_id]["process"]["details"]["ingredients"] = []
        return data

    if ingredient in additional_dictionary["change_ing"]:
        return False

    return ingredient

def finish_ing(ingredients, req, res):
    user_id = req['session']['user_id']
    page = sample_page
    for i in ingredients:
        item = copy.deepcopy(sample_item)
        item["children"][0] = i
        page[1]["children"].append(item)
    res["response"]["text"] = f'Готово! - {sessionStorage[user_id]["process"]["details"]["page_url"]}'
    edit_page(sessionStorage[user_id]["process"]["details"]["page_url"].split("/")[-1], content = page)
    return res

def handle_indredient_loop(ingredient, req, res):
    if "list" in str(type(ingredient)):
        res = finish_ing(ingredient, req, res)
        return res
    user_id = req['session']['user_id']
    sessionStorage[user_id]["process"]["details"]["ingredients"].append(ingredient)
    res["response"]["text"] = f"Ингредиент {ingredient} добавлен. Что еще?"
    return res

def validate_indredient_amount(req):
    amount = req["request"]["nlu"]["entities"]
    if amount and amount[0]["type"] == "YANDEX.NUMBER" and amount[0]["value"]:
        amount = amount[0]["value"]
        if 0 < amount < 20:
            return amount
    return False

def handle_indredient_amount(amount, req, res):
    user_id = req['session']['user_id']
    sessionStorage[user_id]["process"]["details"]["amount_ing"] = amount
    a = ingredients_sequence
    for i in range(amount - 1):
        a.append(ingredients_sequence[-1])
    sessionStorage[user_id]["process"]["sequence"] = a
    res["response"]["text"] = f"По очереди говорите ингредиенты"
    return res

register_sequence = [
    {
        "action": "login_input",
        "validate": validate_login,
        "handle": handle_login
    },
    {
        "action": "pass_input",
        "validate": validate_pass,
        "handle": handle_pass
    }
]

auth_sequence = [
    {
        "action": "login_input",
        "validate": validate_login,
        "handle": handle_login_auth
    },
    {
        "action": "pass_input",
        "validate": validate_pass_auth,
        "handle": handle_pass_auth
    }
]

ingredients_sequence = [
    {
        "action": "title_input",
        "validate": validate_true,
        "handle": create_page_handler
    },
    {
        "action": "ingredient_amount_input",
        "validate": validate_indredient_amount,
        "handle": handle_indredient_amount
    },
    {
        "action": "ingredient_input_loop",
        "validate": validate_indredient,
        "handle": handle_indredient_loop
    }
]


class TeleAPI(object):

	main_page = "https://telegra.ph/Glavnaya-stranica-navyka-YaGraph-04-28"
	user = {'short_name': 'YaGraph', 'author_name': 'Yandex Alice Skill(YaGraph)', 'author_url': '', 'access_token': '972ba3f5a9423243f5a90511de51e35814f5f9562096fd90422798481a46', 'auth_url': 'https://edit.telegra.ph/auth/tBqYFYTyDtBXWi0LkyWNZFx5ktum1mVtVlrBii7TLG'}
	def __init__(self, method=None):
		self._method = method
		self.resp = None

	def __getattr__(self, method):
		return TeleAPI((self._method + "." if self._method else '') + method)

	def __call__(self, **kwargs):
		self.resp = requests.get(f"https://api.telegra.ph/{self._method}", params = kwargs)
		return self.resp.json()

API = TeleAPI()
def create_page(title, author):
	a = API.createPage(access_token = TeleAPI.user["access_token"], title = title, content = '[{"tag":"p","children":["Hello, world!"]}]', author_name = author + "(YaGraph)", author_url = TeleAPI.main_page)
	return a

def edit_page(page_path, content = None, title = None, author_name = None):
	page = API.getPage(path = page_path, return_content = "true")
	if not content:
		content = page["result"]["content"]
		print(content)
	if not title:
		title = page["result"]["title"]
	if not author_name:
		author_name = page["result"]["author_name"]

	a = API.editPage(access_token = TeleAPI.user["access_token"], author_url = TeleAPI.main_page, path = page_path, author_name = author_name, title = title, content = json.dumps(content))
	return a["ok"]


elephant = Blueprint('elephant', __name__)

logging.basicConfig(level=logging.DEBUG)
sessionStorage = {}

@elephant.route('/elephant', methods=['POST'])
def main_func():

    response = {
        "version": request.json['version'],
        "session": request.json['session'],
        "response": {
            "end_session": False
        }
    }
    req = request.json
    response = new_handle(req, response)

    return json.dumps(
        response,
        ensure_ascii=False,
        indent=2
    )


def new_handle(req, res):
    user_id = req['session']['user_id']
    text = req["request"]["original_utterance"].lower()
    command = ""

    for i in commands_dictionary:
        if text in commands_dictionary[i]:
            command = i

    if req['session']['new']:
        sessionStorage[user_id] = {
            "process":{
                "working": False,
                "sequence": None,
                "action": None,
                "details": {}
            }
        }
        command = "help"

    if command == "cancel":
        sessionStorage[user_id] = {
        "process":{
            "working": False,
            "sequence": None,
            "action": None,
            "details": sessionStorage[user_id]["process"]["details"]
            }
        }
        res['response']['text'] = random.choice(answers_dictionary["canceled"])
        return res

    if sessionStorage[user_id]["process"]["working"]:
        action = sessionStorage[user_id]["process"]["action"]
        action_dict = sessionStorage[user_id]["process"]["sequence"][action]
        valid = action_dict["validate"](req)
        if valid:
            sessionStorage[user_id]["process"]["details"][action_dict["action"]] = valid
            res = action_dict["handle"](valid, req, res)
            if action + 1 >= len(sessionStorage[user_id]["process"]["sequence"]):
                sessionStorage[user_id] = {
                    "process":{
                        "working": False,
                        "sequence": None,
                        "action": None,
                        "details": sessionStorage[user_id]["process"]["details"]
                        }
                    }
            else:
                sessionStorage[user_id]["process"]["action"] = action + 1
        else:
            res['response']['text'] = random.choice(answers_dictionary["invalid"])
        return res

    else:
        if not command:
            res['response']['text'] = random.choice(answers_dictionary["unknown"])
            return res

        if command == "register":
            # res["response"]["text"] = random.choice(answers_dictionary["reg_later"])
            # return res
            if sessionStorage[user_id]["process"]["details"].get("authed"):
                res["response"]["text"] = random.choice(answers_dictionary["authed_err"])
                return res
            sessionStorage[user_id] = {
            "process":{
                "working": True,
                "sequence": register_sequence,
                "action": 0,
                "details": sessionStorage[user_id]["process"]["details"]
                }
            }
            res["response"]["text"] = random.choice(answers_dictionary["start_reg"])
            return res

        if command == "auth":
            if sessionStorage[user_id]["process"]["details"].get("authed"):
                res["response"]["text"] = random.choice(answers_dictionary["authed_err"])
                return res
            sessionStorage[user_id] = {
            "process":{
                "working": True,
                "sequence": auth_sequence,
                "action": 0,
                "details": sessionStorage[user_id]["process"]["details"]
                }
            }
            res["response"]["text"] = random.choice(answers_dictionary["start_reg"])
            return res

        if command == "create":
            if not sessionStorage[user_id]["process"]["details"].get("authed"):
                res["response"]["text"] = random.choice(answers_dictionary["auth_first"])
                return res

            sessionStorage[user_id] = {
            "process":{
                "working": True,
                "sequence": ingredients_sequence,
                "action": 0,
                "details": sessionStorage[user_id]["process"]["details"]
                }
            }
            res["response"]["text"] = "Что готовим?"
            return res

        if command == "help":
            res["response"]["text"] = "Доступны такие команды: " + ", ".join([random.choice(commands_dictionary[i]).capitalize() for i in commands_dictionary])
            return res
