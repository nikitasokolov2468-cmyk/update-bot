# 🚀 Update Conference Bot

Telegram-бот для автоматизации регистрации участников и обработки оргвзносов на IT-конференцию **Update**. 

Бот собирает анкетные данные участников, запрашивает чек об оплате, заносит данные в Google Таблицу и отправляет заявку на верификацию администратору с возможностью подтверждения в один клик.

---

## 🛠 Технологический стек

* **Language:** Python 3.10+
* **Framework:** `aiogram 3.x` (Asyncio, FSM, Inline Keyboards)
* **Database / Storage:** Google Sheets API (`gspread`, `google-auth`)
* **Environment Management:** `python-dotenv`
* **Deployment:** Docker, Render / VPS

---

## ⚙️ Основной функционал

* 📝 **Пошаговая регистрация (FSM):** сбор ФИО, города и настроя («вайба») участника.
* 💳 **Прием оплаты:** отправка реквизитов и проверка отправки скриншота чека.
* 📊 **Интеграция с Google Таблицами:** автоматическая запись новых заявок и динамическое обновление статуса оплаты.
* 👨‍💼 **Панель администратора:** инлайн-уведомления с фото чека и кнопками «Подтвердить» / «Отклонить» прямо в Telegram.
* ☁️ **Cloud-Native Auth:** поддержка двухрежимной авторизации в Google API (через `credentials.json` локально или переменную окружения `GOOGLE_CREDENTIALS_JSON` в облаке).

---

## 🚀 Локальный запуск

### 1. Клонирование репозитория
```bash
git clone [https://github.com/nikitasokolov2468-cmyk/update-bot.git](https://github.com/nikitasokolov2468-cmyk/update-bot.git)
cd update-bot