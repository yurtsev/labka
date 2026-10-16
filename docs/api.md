# API

REST API backend на `/api` и WebSocket на `/api/ws`. Здесь — общие правила и карта эндпоинтов;
схемы запросов и ответов — в Swagger (http://localhost:8000/docs) и в `/openapi.json`.

## Общие правила

**Аутентификация.** `POST /api/auth/login` ставит две httpOnly-cookie: access-токен (JWT,
15 минут) и refresh-токен (30 дней, отправляется только на `/api/auth`). Когда access-токен истёк,
API отвечает 401, клиент вызывает `POST /api/auth/refresh` и повторяет запрос. Refresh-токен
одноразовый: при обновлении выдаётся новая пара, а повторное использование старого отзывает сессию.

**Доступ.** Преподаватель работает только со своими курсами, студент — только с курсами своей
группы. Чужой курс — 403, несуществующий — 404, изменение архивного курса — 409.

**Ошибки** приходят в одном формате:

```json
{
  "error": {
    "code": "courses.not_found",
    "message": "Курс не найден",
    "details": null,
    "request_id": "0199f0c2-…"
  }
}
```

`code` — стабильный машинный код (`<домен>.<ошибка>`), `message` — текст для пользователя по-русски.
Ошибки валидации — 422 с кодом `request.invalid` и списком полей в `details.fields`. Тот же
`request_id` приходит в заголовке `X-Request-Id` и есть в логах.

**Списки** постраничные: параметры `page` (с 1) и `per_page` (по умолчанию 20, максимум 100), ответ —
`{"items", "page", "per_page", "total", "pages"}`.

**Файлы** через backend не проходят. Загрузка в три шага:

1. `POST …/uploads` с `content_type` и `file_size` — backend проверяет размер и выдаёт
   presigned-форму S3;
2. браузер отправляет файл прямо в S3 по этой форме;
3. ключ файла передаётся в запрос, который создаёт объект (материал, задание, попытку, аватарку).

Скачивание — по presigned-ссылкам из ответов API, ссылки живут 15 минут.

## Эндпоинты

### Вход и профиль

| Метод | Путь | Что делает |
|---|---|---|
| POST | `/api/auth/register` | регистрация студента по коду группы |
| POST | `/api/auth/login` | вход |
| POST | `/api/auth/refresh` | обновить токены |
| POST | `/api/auth/logout` | выход |
| POST | `/api/auth/password` | сменить пароль |
| GET | `/api/auth/me` | текущий пользователь |
| GET | `/api/profile` | профиль: ФИО, почта, группа или кафедра |
| POST / PUT / DELETE | `/api/profile/avatar/uploads`, `/api/profile/avatar` | загрузить, поставить, убрать аватарку |
| GET | `/api/home` | данные главной (у студента и преподавателя свои) |

### Курсы

| Метод | Путь | Что делает |
|---|---|---|
| GET / POST | `/api/courses` | список курсов (с фильтром архива), создать курс |
| GET | `/api/courses/available-groups` | группы, которые преподаватель может добавить |
| GET / PUT | `/api/courses/{course_id}` | курс, изменить курс |
| POST / DELETE | `/api/courses/{course_id}/groups[/{group_id}]` | добавить или убрать группу |
| POST | `/api/courses/{course_id}/archive`, `…/unarchive` | в архив и обратно |
| GET | `/api/courses/{course_id}/feed` | лента: задания и объявления |
| POST / PUT / DELETE | `/api/courses/{course_id}/announcements[/{id}]` | объявления |
| GET / POST / PUT / DELETE | `/api/courses/{course_id}/materials[/{id}]` | материалы |
| POST / DELETE | `…/materials/uploads`, `…/materials/{id}/files[/{file_id}]` | файлы материалов |

### Задания, попытки, проверка

| Метод | Путь | Что делает |
|---|---|---|
| POST | `/api/courses/{course_id}/assignments` | создать задание |
| GET / PUT / DELETE | `/api/courses/{course_id}/assignments/{assignment_id}` | задание |
| POST / DELETE | `…/assignments/uploads`, `…/assignments/{id}/files[/{file_id}]` | файлы задания |
| GET | `…/assignments/{id}/students` | таблица студентов со статусами (преподаватель) |
| GET / POST | `…/assignments/{id}/submissions` | свои попытки, отправить попытку (студент) |
| POST | `…/assignments/{id}/submissions/uploads` | загрузка файла попытки |
| GET | `…/assignments/{id}/students/{student_id}/submissions` | попытки студента для проверки |
| POST / PUT | `…/submissions/{submission_id}/review` | проверить, исправить оценку |
| GET | `/api/reviews/queue` | очередь на проверку |

### Расписание и календарь

| Метод | Путь | Что делает |
|---|---|---|
| GET | `/api/schedule/slots` | окна пар |
| GET | `/api/courses/{course_id}/schedule` | правила и разовые занятия курса |
| POST / PUT / DELETE | `/api/courses/{course_id}/schedule/rules[/{id}]` | правила расписания |
| POST / PUT / DELETE | `/api/courses/{course_id}/schedule/extras[/{id}]` | разовые занятия |
| GET / POST / PUT / DELETE | `/api/courses/{course_id}/exams[/{id}]` | зачёты и экзамены |
| GET | `/api/calendar` | календарь за день, неделю или месяц |
| GET / POST / PUT / DELETE | `/api/personal-tasks[/{id}]` | личные задачи студента |
| PATCH | `/api/personal-tasks/{id}/done` | отметить «сделано» |

### Уведомления

| Метод | Путь | Что делает |
|---|---|---|
| GET | `/api/notifications` | список, фильтр непрочитанных |
| GET | `/api/notifications/unread-count` | счётчик непрочитанных |
| POST | `/api/notifications/{id}/read`, `/api/notifications/read-all` | отметить прочитанными |
| WS | `/api/ws` | поток уведомлений |

## WebSocket `/api/ws`

Подключение аутентифицируется той же cookie, что и REST. Сообщения сервера:

| `type` | Когда |
|---|---|
| `ready` | сразу после подключения, с `unread_count` |
| `notification` | новое или обновлённое уведомление, с `notification` и `unread_count` |
| `resync` | события могли потеряться — клиенту нужно перечитать список |
| `ping` | раз в 30 секунд |

Коды закрытия: `4401` — нет входа или сессия отозвана (клиент обновляет токен и переподключается),
`4403` — запрос с чужого сайта (Origin не из `cors.origins`).
