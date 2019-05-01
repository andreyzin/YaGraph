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

megaskill = Blueprint('megaskill', __name__)

logging.basicConfig(level=logging.DEBUG)
sessionStorage = {}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "users.db")

@megaskill.route('/megaskill', methods=['POST'])
def main_func():

	response = {
		"version": request.json['version'],
		"session": request.json['session'],
		"response": {
			"end_session": False
		}
	}
	req = request.json
	response = handle(req, response)

	return json.dumps(
		response,
		ensure_ascii=False,
		indent=2
	)

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


class Sequences:

	class Authorize:

		enter_pass = ["Прекрасно, {}! Произнесите кодовую фразу или скажите отмена"]
		invalid_pass = ["Неверная кодовая фраза!"]
		already_authed = ["Вы уже авторизованы", "Второй раз авторизоваться не получится"]
		start_auth = ["Итак, поехали! Как вас зовут?", "Ваше имя?"]
		finish_auth = ["Ура, вы авторизовались!", "Авторизация прошла успешно!", "Пять минут, полет нормальный!"]

		def login_validate(req, res):
			name = req["request"]["nlu"]["entities"]
			if name and name[0]["type"] == "YANDEX.FIO" and name[0]["value"].get("first_name"):
				name = name[0]["value"]["first_name"].capitalize()
				return {"ok": True, "response": name}
			res["response"]["text"] = random.choice(Sequences.Register.invalid_login)
			return {"ok": False, "response": res}

		def pass_validate(req, res):
			user_id = req['session']['user_id']
			name = sessionStorage[user_id]["details"]["login"]
			conn = sqlite3.connect(db_path)
			cursor = conn.cursor()
			cursor.execute("SELECT * FROM users WHERE name = :name AND passphrase = :passphrase", {"name": name, "passphrase": req["request"]["original_utterance"].lower()})
			a = cursor.fetchall()
			conn.close()
			if not a:
				res["response"]["text"] = random.choice(Sequences.Authorize.invalid_pass)
				return {"ok": False, "response": res}
			return {"ok": True, "response": req["request"]["original_utterance"].lower()}

		def login_handle(name, req, res):
			user_id = req['session']['user_id']
			sessionStorage[user_id]["details"]["login"] = name
			res['response']['text'] = random.choice(Sequences.Authorize.enter_pass).format(name)
			return res


		def pass_handle(passphrase, req, res):
			user_id = req['session']['user_id']
			sessionStorage[user_id]["details"]["authed"] = True
			sessionStorage[user_id]["details"]["pass"] = passphrase
			res["response"]["text"] = random.choice(Sequences.Authorize.finish_auth)
			return res

		def start_handle(data, req, res):
			user_id = req["session"]["user_id"]
			if sessionStorage[user_id]["details"].get("authed"):
				Commands.cancel(req, res)
				res["response"]["text"] = random.choice(Sequences.Authorize.already_authed)
				return res
			res["response"]["text"] = random.choice(Sequences.Authorize.start_auth)
			return res

		sequence = [
			{
				"type": "start",
				"handle": start_handle
			},
			{
				"type": "one_time",
				"action_name": "login_input",
				"validate": login_validate,
				"handle": login_handle
			},
			{
				"type": "one_time",
				"action_name": "pass_input",
				"validate": pass_validate,
				"handle": pass_handle
			}
		]

	class Register:
		invalid_login = ["Скажите настоящее имя", "Я не знаю такое имя, скажите настоящее"]
		invalid_pass = ["Попробуйте другую фразу"]
		finish_reg = ["Ура, вы зарегестрировались!", "Регистрация прошла успешно!", "Пять минут, полет нормальный!"]
		start_reg = ["Итак, поехали! Как вас зовут?", "Ваше имя?"]
		enter_pass = ["Прекрасно, {}! Придумайте кодовую фразу. Если ошибка, то попробуйте другую фразу"]
		already_authed = ["Вы уже авторизованы", "Хмм, кто-то пофиксил этот баг"]

		def login_validate(req, res):
			name = req["request"]["nlu"]["entities"]
			if name and name[0]["type"] == "YANDEX.FIO" and name[0]["value"].get("first_name"):
				name = name[0]["value"]["first_name"].capitalize()
				return {"ok": True, "response": name}
			res["response"]["text"] = random.choice(Sequences.Register.invalid_login)
			return {"ok": False, "response": res}

		def pass_validate(req, res):
			user_id = req['session']['user_id']
			name = sessionStorage[user_id]["details"]["login"]
			conn = sqlite3.connect(db_path)
			cursor = conn.cursor()
			cursor.execute("SELECT * FROM users WHERE name = :name AND passphrase = :passphrase", {"name": name, "passphrase": req["request"]["original_utterance"].lower()})
			a = cursor.fetchall()
			conn.close()
			if a:
				res["response"]["text"] = random.choice(Sequences.Register.invalid_pass)
				return {"ok": False, "response": res}
			return {"ok": True, "response": req["request"]["original_utterance"].lower()}

		def login_handle(name, req, res):
			user_id = req['session']['user_id']
			sessionStorage[user_id]["details"]["login"] = name
			res['response']['text'] = random.choice(Sequences.Register.enter_pass).format(name)
			return res

		def pass_handle(passphrase, req, res):
			user_id = req['session']['user_id']
			name = sessionStorage[user_id]["details"]["login"]
			sessionStorage[user_id]["details"]["authed"] = True
			sessionStorage[user_id]["details"]["pass"] = passphrase
			res["response"]["text"] = random.choice(Sequences.Register.finish_reg)
			conn = sqlite3.connect(db_path)
			cursor = conn.cursor()
			cursor.execute("INSERT INTO users (id, name, passphrase) VALUES (:id, :name, :passphrase)", {"id" : str(uuid.uuid4())[:8], "name": name, "passphrase": passphrase})
			conn.commit()
			conn.close()
			return res

		def start_handle(data, req, res):
			user_id = req["session"]["user_id"]
			if sessionStorage[user_id]["details"].get("authed"):
				Commands.cancel(req, res)
				res["response"]["text"] = random.choice(Sequences.Register.already_authed)
				return res
			res["response"]["text"] = random.choice(Sequences.Register.start_reg)
			return res

		sequence = [
			{
				"type": "start",
				"handle": start_handle
			},
			{
				"type": "one_time",
				"action_name": "login_input",
				"validate": login_validate,
				"handle": login_handle
			},
			{
				"type": "one_time",
				"action_name": "pass_input",
				"validate": pass_validate,
				"handle": pass_handle
			}
		]

	class CreatePage:

		sample_item =    {
			"tag": "li",
			"children": [""]
		}

		sample_page = [{
		  "tag": "aside",
		  "children": [{
		    "tag": "strong",
		    "children": ["Ингредиенты"]
		   }]
		 },
		 {"tag": "ol",
		  "children": []
		 },
		 {"tag": "aside",
		  "children": [{
		    "tag": "strong",
		    "children": ["Приготовление"]
		   }]
		 },
		 {"tag": "ol",
		  "children": []
		 },
		 {"tag": "p",
		  "children": ["\nРецепт создан с помощью навыка для Алисы ",
		  {"tag": "strong",
		   "children": [{
		      "tag": "em",
		      "children": ["YaGraph"]
		     }
		    ]
		   }
		  ]
		 }
		]

		start_creating = ["Что готовим?"]
		page_created = ["Страница {} создана. Перечислите ингредиенты, затем скажите хватит"]
		break_words = ["все", "конец", "достаточно", "хватит", "это все", "вроде все"]
		auth_first = ["Сначала авторизуйтесь", "Войдите в аккаунт", "Скажите авторизация"]

		empty_ingredients = ["Все отменено, введите хотя бы один ингредиент"]
		break_ingredients = ["Количество добавленных ингредиентов {}. Перечислите шаги приготовления, затем скажите хватит"]
		ingredient_added = ["Ингредиент {} добавлен. Что еще?"]

		empty_steps = ["Все отменено, введите хотя бы один шаг приготовления"]
		break_steps = ["Ваша страница создана - {}", "Ура! Тут ваш рецепт - {}"]
		step_added = ["Записала. Что дальше?"]

		def start_handle(data, req, res):
			user_id = req["session"]["user_id"]
			if not sessionStorage[user_id]["details"].get("authed"):
				Commands.cancel(req, res)
				res["response"]["text"] = random.choice(Sequences.CreatePage.auth_first)
				return res

			res["response"]["text"] = random.choice(Sequences.CreatePage.start_creating)
			return res

		def title_validate(req, res):
			return {"ok": True, "response": req["request"]["original_utterance"].lower().capitalize()}

		def title_handle(title, req, res):
			user_id = req['session']['user_id']
			name = sessionStorage[user_id]["details"]["login"]
			sessionStorage[user_id]["details"]["ingredients"] = []
			sessionStorage[user_id]["details"]["steps"] = []
			a = Helper.create_page(title, name)
			sessionStorage[user_id]["details"]["page_url"] = a["result"]["url"]
			conn = sqlite3.connect(db_path)
			cursor = conn.cursor()
			cursor.execute("SELECT * FROM users WHERE name = :name AND passphrase = :passphrase", {"name": name, "passphrase": sessionStorage[user_id]["details"]["pass"]})
			owner_id = cursor.fetchall()[0][0]
			cursor.execute("INSERT INTO pages (url, title, owner_id) VALUES (:url, :title, :owner_id)", {"url" : a["result"]["url"], "title": title, "owner_id": owner_id})
			conn.commit()
			conn.close()
			res["response"]["text"] = random.choice(Sequences.CreatePage.page_created).format(title)
			return res

		def ingredient_validate(req, res):
			return {"ok": True, "response": req["request"]["original_utterance"].lower().capitalize()}

		def ingredient_handle(ingredient, req, res):
			user_id = req['session']['user_id']
			sessionStorage[user_id]["details"]["ingredients"].append(ingredient)
			res["response"]["text"] = random.choice(Sequences.CreatePage.ingredient_added).format(ingredient)
			return res

		def ingredient_break(req, res):
			text =  req["request"]["original_utterance"].lower()
			user_id = req["session"]["user_id"]
			break_loop = text in Sequences.CreatePage.break_words
			if break_loop:
				if not sessionStorage[user_id]["details"]["ingredients"]:
					Commands.cancel(req, {"response": {"text": None}})
					res["response"]["text"] = random.choice(Sequences.CreatePage.empty_ingredients)
					return {"ok": True, "response": res}

				res["response"]["text"] = random.choice(Sequences.CreatePage.break_ingredients).format(len(sessionStorage[user_id]["details"]["ingredients"]))
				return {"ok": True, "response": res}

			return {"ok": False, "response": None}

		def step_validate(req, res):
			return {"ok": True, "response": req["request"]["original_utterance"].lower().capitalize()}

		def step_handle(step, req, res):
			user_id = req['session']['user_id']
			sessionStorage[user_id]["details"]["steps"].append(step)
			res["response"]["text"] = random.choice(Sequences.CreatePage.step_added).format(step)
			return res

		def step_break(req, res):
			text =  req["request"]["original_utterance"].lower()
			user_id = req["session"]["user_id"]
			break_loop = text in Sequences.CreatePage.break_words
			if break_loop:
				if not sessionStorage[user_id]["details"]["steps"]:
					Commands.cancel(req, {"response": {"text": None}})
					res["response"]["text"] = random.choice(Sequences.CreatePage.empty_steps)
				else:
					res["response"]["text"] = random.choice(Sequences.CreatePage.break_steps).format(sessionStorage[user_id]["details"]["page_url"])
				Helper.update_page(req)
				return {"ok": True, "response": res}

			return {"ok": False, "response": None}


		sequence = [
			{
				"type": "start",
				"handle": start_handle
			},
			{
				"type": "one_time",
				"action_name": "title_input",
				"validate": title_validate,
				"handle": title_handle
			},
			{
				"type": "loop",
				"action_name": "ingredient_input",
				"validate": ingredient_validate,
				"handle": ingredient_handle,
				"break": ingredient_break
			},
			{
				"type": "loop",
				"action_name": "steps_input",
				"validate": step_validate,
				"handle": step_handle,
				"break": step_break
			}
		]

class Commands:
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

	def cancel(req, res):
		canceled = ["Отменено", "Операция прервана!", "Вы безжалостно убили операцию"]
		cancel_error = ["Все отменено и так", "Текущих операций нет"]
		user_id = req['session']['user_id']
		if not sessionStorage[user_id]["process"]["sequence"]:
			res["response"]["text"] = random.choice(cancel_error)
			return res

		sessionStorage[user_id]["process"] = {
			"sequence": None,
			"iteration": 0,
			"loop_iteration": 0,
			"next": None
		}
		res['response']['text'] = random.choice(canceled)
		return res

	def unknown(req, res):
		unknown = ["Я не поняла. Скажите помощь", "Такой команды нет. Скажите помощь", "Ой, команда затерялась. Скажите помощь"]
		res['response']['text'] = random.choice(unknown)
		return res

	def help(req, res):
		res["response"]["text"] = "Доступны такие команды: " + ", ".join([random.choice(command["variants"]).capitalize() for command in commands if command["show"]])
		return res

commands = [
	{
		"name": "cancel",
		"variants": ["отмена", "хватит", "не надо", "завершить", "назад", "стоп"],
		"function": Commands.cancel,
		"show": True
	},
	{
		"name": "register",
		"variants": ["зарегестрироваться", "создать аккаунт", "стать участником", "регистрация"],
		"sequence": Sequences.Register.sequence,
		"show": True
	},
	{
		"name": "auth",
		"variants": ["авторизация", "войти", "авторизоваться"],
		"sequence": Sequences.Authorize.sequence,
		"show": True
	},
	{
		"name": "help",
		"variants": ["помощь", "как", "помоги", "а как"],
		"function": Commands.help,
		"show": False
	},
	{
		"name": "create_page",
		"variants": ["создать страницу", "создать рецепт", "новый рецепт", "добавить рецепт", "давай готовить"],
		"sequence": Sequences.CreatePage.sequence,
		"show": True
	}
]

class Helper:

	def update_page(req):
		user_id = req['session']['user_id']
		page = Sequences.CreatePage.sample_page
		ingredients = sessionStorage[user_id]["details"]["ingredients"]
		steps = sessionStorage[user_id]["details"]["steps"]
		sessionStorage[user_id]["details"]["ingredients"] = []
		sessionStorage[user_id]["details"]["steps"] = []
		for i in ingredients:
			item = copy.deepcopy(Sequences.CreatePage.sample_item)
			item["children"][0] = i
			page[1]["children"].append(item)
		for i in steps:
			item = copy.deepcopy(Sequences.CreatePage.sample_item)
			item["children"][0] = i
			page[3]["children"].append(item)
		Helper.edit_page(sessionStorage[user_id]["details"]["page_url"].split("/")[-1], content = page)

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

	def append_iteration(req):
		user_id = req['session']['user_id']
		iteration = sessionStorage[user_id]["process"]["iteration"]
		# if sequence is finished, clearing session process
		if iteration + 1 >= len(sessionStorage[user_id]["process"]["sequence"]):
			sessionStorage[user_id]["process"] = {
				"sequence": None,
				"iteration": 0,
				"loop_iteration": 0,
				"next": None
			}
		else:
			# else just adding 1 to iteration
			sessionStorage[user_id]["process"]["iteration"] = iteration + 1

	def append_loop_iteration(req):
		user_id = req['session']['user_id']
		loop_iteration = sessionStorage[user_id]["process"]["loop_iteration"]
		sessionStorage[user_id]["process"]["loop_iteration"] = loop_iteration + 1

def handle(req, res):
	user_id = req['session']['user_id']
	text = req["request"]["original_utterance"].lower()
	# default command is 'unknown'
	current_command = {
		"name": "unknown",
		"variants": [""],
		"function": Commands.unknown
	}
	# Finding matches in commands
	for command in commands:
		if text in command["variants"]:
			current_command = command

	# If user session is new or the session isnt started, initializing new empty session and sending help
	if req['session']['new'] or user_id not in sessionStorage:
		sessionStorage[user_id] = {
			"process": {
				"sequence": None,
				"iteration": 0,
				"loop_iteration": 0
			},
			"details": {}
		}
		return Commands.help(req, res)

	# if command is cancel canceling all operations
	if current_command["name"] == "cancel":
		return Commands.cancel(req, res)

	# if there is no running sequences
	if not sessionStorage[user_id]["process"]["sequence"]:
		# if command causes function, run function and return its answer
		if "function" in current_command:
			return current_command["function"](req, res)

		#  if command causes sequence
		sessionStorage[user_id]["process"] = {
			"sequence": current_command["sequence"],
			"iteration": 0,
			"loop_iteration": 0
		}
	# if user has sequences to run
	if sessionStorage[user_id]["process"]["sequence"]:
		iteration = sessionStorage[user_id]["process"]["iteration"]
		action = sessionStorage[user_id]["process"]["sequence"][iteration]

		# if action type is start, just calling handler
		if action["type"] == "start":
			Helper.append_iteration(req)
			return action["handle"](text, req, res)

		# if action type is one_time, then validating data and sending response generated by handler
		if action["type"] == "one_time":
			validated = action["validate"](req, res)
			if validated["ok"]:
				Helper.append_iteration(req)
				return action["handle"](validated["response"], req, res)

			# if data is invalid, sending validation function response
			return validated["response"]

		# so the harder one)))
		# if action type is loop, then checking condition to break the loop
		if action["type"] == "loop":
			break_loop = action["break"](req, res)
			if break_loop["ok"]:

				# if the loop was broken, then sending onLoopFinish response and appending iteration
				Helper.append_iteration(req)
				return break_loop["response"]

			# if the loop is continueing, then validating data, sending response and adding 1 to loop_iteration
			validated = action["validate"](req, res)
			Helper.append_loop_iteration(req)
			if validated["ok"]:
				return action["handle"](validated["response"], req, res)

			# if data is invalid, sending validation function response
			return validated["response"]
