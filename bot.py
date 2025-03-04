import telebot
import requests
import random
import sqlite3
from telebot import types

# Токен бота
TOKEN = ""
# Токен для API Кинопоиска
KP_TOKEN = ""

# Инициализация бота
bot = telebot.TeleBot(TOKEN)

# Подключение к базе данных SQLite
conn = sqlite3.connect('movies.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблицы для хранения предпочтений пользователей
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INTEGER,
    movie_id INTEGER,
    liked INTEGER,
    PRIMARY KEY (user_id, movie_id)
    )
''')
conn.commit()

# Список жанров
genres = [
    "комедия",
    "драма",
    "боевик",
    "фантастика",
    "ужасы",
    "триллер",
    "мелодрама",
    "детектив",
    "мультфильм",
    "аниме",
]

# Словарь для перевода типа картины на русский
type_translation = {
    "movie": "фильм",
    "tv-series": "сериал",
    "cartoon": "мультфильм",
    "anime": "аниме",
    "animated-series": "анимационный сериал",
    "tv-show": "телешоу",
}

# Словарь для хранения состояний пользователей (например, ожидание ввода актера, рейтинга и т.д.)
USER_STATES = {}

# Функция для создания клавиатуры с кнопкой "Назад"
def create_back_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    back_button = types.KeyboardButton("⬅️ Назад")
    markup.add(back_button)
    return markup

# Функция для отображения главного меню
def show_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    button_genre = types.KeyboardButton("🎭 Жанр")
    button_actor = types.KeyboardButton("🎬 Актер")
    button_rating = types.KeyboardButton("⭐️ Рейтинг")  
    button_country = types.KeyboardButton("🌍 Страна")  
    button_year = types.KeyboardButton("📅 Год")
    button_favorites = types.KeyboardButton("❤️ Понравившиеся")
    markup.add(button_genre, button_actor, button_rating, button_country, button_year, button_favorites)
    bot.send_message(chat_id, "Выбери критерий поиска фильма:", reply_markup=markup)

# Обработчик команды /start
@bot.message_handler(commands=["start"])
def send_welcome(message):
    show_main_menu(message.chat.id)

# Обработчик кнопки "Назад"
@bot.message_handler(func=lambda message: message.text == "⬅️ Назад")
def handle_back(message):
    show_main_menu(message.chat.id)

# Обработчик кнопки "🎭 Жанр"
@bot.message_handler(func=lambda message: message.text == "🎭 Жанр")
def choose_genre(message):
    # Создаем клавиатуру с кнопками жанров и кнопкой "Назад"
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [types.KeyboardButton(genre.capitalize()) for genre in genres]
    markup.add(*buttons)
    markup.add(types.KeyboardButton("⬅️ Назад"))
    bot.send_message(message.chat.id, "Выбери жанр:", reply_markup=markup)

# Обработчик выбора жанра
@bot.message_handler(func=lambda message: message.text.lower() in genres)
def handle_genre(message):
    chat_id = message.chat.id
    genre = message.text.lower()
    # Формируем URL для запроса к API Кинопоиска по выбранному жанру
    url = f"https://api.kinopoisk.dev/v1.3/movie?field=genres.name&search={genre}&limit=50&token={KP_TOKEN}"
    response = requests.get(url)
    data = response.json()

    if data.get("docs"):
        # Если фильмы найдены, вызываем функцию рекомендации
        recommend_movie(chat_id, data)
    else:
        # Если фильмы не найдены, сообщаем об этом пользователю
        bot.send_message(chat_id, f"К сожалению, по жанру '{genre}' ничего не найдено.", reply_markup=create_back_keyboard())

# Обработчик кнопки "🎬 Актер"
@bot.message_handler(func=lambda message: message.text == "🎬 Актер")
def ask_actor(message):
    bot.send_message(message.chat.id, "Введите имя и фамилию актера:", reply_markup=create_back_keyboard())
    # Устанавливаем состояние ожидания ввода актера
    USER_STATES[message.chat.id] = "waiting_actor"

# Обработчик ввода актера
@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == "waiting_actor")
def handle_actor(message):
    chat_id = message.chat.id
    actor = message.text
    # Формируем URL для запроса к API Кинопоиска по актеру
    url = f"https://api.kinopoisk.dev/v1.3/movie?field=persons.name&search={actor}&limit=50&token={KP_TOKEN}"
    response = requests.get(url)
    data = response.json()

    if data.get("docs"):
        # Если фильмы найдены, вызываем функцию рекомендации
        recommend_movie(chat_id, data)
    else:
        # Если фильмы не найдены, сообщаем об этом пользователю
        bot.send_message(chat_id, f"К сожалению, фильмы с актером '{actor}' не найдены.", reply_markup=create_back_keyboard())
    # Убираем состояние ожидания ввода актера
    USER_STATES.pop(chat_id, None)

# Обработчик кнопки "⭐️ Рейтинг"
@bot.message_handler(func=lambda message: message.text == "⭐️ Рейтинг")  
def ask_rating(message):
    bot.send_message(message.chat.id, "Введите минимальный рейтинг (например, 7.5):", reply_markup=create_back_keyboard())
    # Устанавливаем состояние ожидания ввода рейтинга
    USER_STATES[message.chat.id] = "waiting_rating"

# Обработчик ввода рейтинга
@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == "waiting_rating")
def handle_rating(message):
    chat_id = message.chat.id
    try:
        # Преобразуем введенный текст в число
        min_rating = float(message.text)
    except ValueError:
        # Если введено не число, сообщаем об ошибке
        bot.send_message(chat_id, "Пожалуйста, введите число (например, 7.5).", reply_markup=create_back_keyboard())
        return

    # Формируем URL для запроса к API Кинопоиска по рейтингу
    url = f"https://api.kinopoisk.dev/v1.3/movie?field=rating.kp&search={min_rating}&limit=50&token={KP_TOKEN}"
    response = requests.get(url)
    data = response.json()

    if data.get("docs"):
        # Если фильмы найдены, вызываем функцию рекомендации
        recommend_movie(chat_id, data)
    else:
        # Если фильмы не найдены, сообщаем об этом пользователю
        bot.send_message(chat_id, f"К сожалению, фильмы с рейтингом выше {min_rating} не найдены.", reply_markup=create_back_keyboard())
    # Убираем состояние ожидания ввода рейтинга
    USER_STATES.pop(chat_id, None)

# Обработчик кнопки "🌍 Страна"
@bot.message_handler(func=lambda message: message.text == "🌍 Страна")  
def ask_country(message):
    bot.send_message(message.chat.id, "Введите страну производства (например, США):", reply_markup=create_back_keyboard())
    # Устанавливаем состояние ожидания ввода страны
    USER_STATES[message.chat.id] = "waiting_country"

# Обработчик ввода страны
@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == "waiting_country")
def handle_country(message):
    chat_id = message.chat.id
    country = message.text.strip()
    # Формируем URL для запроса к API Кинопоиска по стране
    url = f"https://api.kinopoisk.dev/v1.3/movie?field=countries.name&search={country}&limit=50&token={KP_TOKEN}"
    response = requests.get(url)
    data = response.json()

    if data.get("docs"):
        # Если фильмы найдены, вызываем функцию рекомендации
        recommend_movie(chat_id, data)
    else:
        # Если фильмы не найдены, сообщаем об этом пользователю
        bot.send_message(chat_id, f"К сожалению, фильмы из страны '{country}' не найдены.", reply_markup=create_back_keyboard())
    # Убираем состояние ожидания ввода страны
    USER_STATES.pop(chat_id, None)

# Обработчик кнопки "📅 Год"
@bot.message_handler(func=lambda message: message.text == "📅 Год")
def ask_year(message):
    bot.send_message(message.chat.id, "Введите год выпуска фильма:", reply_markup=create_back_keyboard())
    # Устанавливаем состояние ожидания ввода года
    USER_STATES[message.chat.id] = "waiting_year"

# Обработчик ввода года
@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == "waiting_year")
def handle_year(message):
    chat_id = message.chat.id
    year = message.text
    # Формируем URL для запроса к API Кинопоиска по году
    url = f"https://api.kinopoisk.dev/v1.3/movie?field=year&search={year}&limit=50&token={KP_TOKEN}"
    response = requests.get(url)
    data = response.json()

    if data.get("docs"):
        # Если фильмы найдены, вызываем функцию рекомендации
        recommend_movie(chat_id, data)
    else:
        # Если фильмы не найдены, сообщаем об этом пользователю
        bot.send_message(chat_id, f"К сожалению, фильмы {year} года не найдены.", reply_markup=create_back_keyboard())
    # Убираем состояние ожидания ввода года
    USER_STATES.pop(chat_id, None)

# Обработчик кнопки "❤️ Понравившиеся"
@bot.message_handler(func=lambda message: message.text == "❤️ Понравившиеся")
def show_favorites(message):
    user_id = message.from_user.id
    # Получаем список понравившихся фильмов пользователя из базы данных
    cursor.execute("SELECT movie_id FROM user_preferences WHERE user_id = ? AND liked = 1", (user_id,))
    favorite_movies = cursor.fetchall()

    if favorite_movies:
        response_text = "Ваши понравившиеся фильмы:\n\n"
        for movie in favorite_movies:
            movie_id = movie[0]
            # Получаем информацию о фильме по его ID
            url = f"https://api.kinopoisk.dev/v1.3/movie/{movie_id}?token={KP_TOKEN}"
            response = requests.get(url)
            movie_data = response.json()

            if movie_data:
                name = movie_data.get("name", "Название неизвестно")
                year = movie_data.get("year", "Год неизвестен")
                response_text += f"{name} ({year})\n"
            else:
                response_text += f"Фильм с ID {movie_id} не найден.\n"
        bot.send_message(message.chat.id, response_text, reply_markup=create_back_keyboard())
    else:
        bot.send_message(message.chat.id, "У вас пока нет понравившихся фильмов.", reply_markup=create_back_keyboard())

# Функция для рекомендации фильма
def recommend_movie(chat_id, data):
    user_id = chat_id
    # Получаем список непонравившихся фильмов пользователя
    cursor.execute("SELECT movie_id FROM user_preferences WHERE user_id = ? AND liked = 0", (user_id,))
    disliked_movies = [row[0] for row in cursor.fetchall()]

    # Фильтруем фильмы, исключая те, которые пользователь уже отметил как непонравившиеся
    filtered_movies = [movie for movie in data["docs"] if movie.get("id") not in disliked_movies]

    if not filtered_movies:
        bot.send_message(chat_id, "К сожалению, подходящих фильмов не найдено.", reply_markup=create_back_keyboard())
        return

    # Выбираем случайный фильм из отфильтрованного списка
    random_movie = random.choice(filtered_movies)
    movie_id = random_movie.get("id")
    name = random_movie.get("name", "Название неизвестно")
    year = random_movie.get("year", "Год неизвестен")
    description = random_movie.get("description", "Описание отсутствует")
    rating = random_movie.get("rating", {}).get("kp", "Рейтинг отсутствует")
    type_ = random_movie.get("type", "Тип неизвестен")
    poster_url = random_movie.get("poster", {}).get("url")

    # Переводим тип фильма на русский язык
    type_in_russian = type_translation.get(type_, type_)
    response_text = f"Рекомендую посмотреть: {name} ({year})\nТип: {type_in_russian}\nОписание: {description}\nРейтинг: {rating}"

    # Создаем клавиатуру с кнопками "Понравилось" и "Не понравилось"
    markup = types.InlineKeyboardMarkup()
    like_button = types.InlineKeyboardButton("👍 Понравилось", callback_data=f"like_{movie_id}")
    dislike_button = types.InlineKeyboardButton("👎 Не понравилось", callback_data=f"dislike_{movie_id}")
    markup.add(like_button, dislike_button)

    # Отправляем сообщение с рекомендацией и клавиатурой
    if poster_url:
        bot.send_photo(chat_id, poster_url, caption=response_text, reply_markup=markup)
    else:
        bot.send_message(chat_id, response_text, reply_markup=markup)

# Обработчик кнопок "Понравилось" и "Не понравилось"
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    movie_id = int(call.data.split('_')[1])
    action = call.data.split('_')[0]

    if action == "like":
        # Добавляем фильм в понравившиеся
        cursor.execute("REPLACE INTO user_preferences (user_id, movie_id, liked) VALUES (?, ?, ?)", (user_id, movie_id, 1))
        bot.answer_callback_query(call.id, "Фильм добавлен в понравившиеся!")
    elif action == "dislike":
        # Добавляем фильм в непонравившиеся
        cursor.execute("REPLACE INTO user_preferences (user_id, movie_id, liked) VALUES (?, ?, ?)", (user_id, movie_id, 0))
        bot.answer_callback_query(call.id, "Фильм добавлен в непонравившиеся.")
    conn.commit()

# Запуск бота
bot.polling(none_stop=True)