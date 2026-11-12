# Распознавание водосчётчиков

Python 3.10+ с pip и venv, CPU. На Debian/Ubuntu при отсутствии venv установите пакет `python3-venv`. При первом запуске нужен интернет для установки зависимостей.

## Запуск одной командой

Из папки проекта:

```sh
python3 start.py
```

Windows: `python start.py`. Скрипт сам создаёт `.venv`, устанавливает единственный `requirements.txt` и запускает сервис. Повторно зависимости устанавливаются только при изменении requirements.

Swagger: http://localhost:8011/docs. Остановка: Ctrl+C.

## HTTPS на стенде

Скопируйте в папку проекта:

- `certs/fullchain.pem` — PEM-сертификат домена с цепочкой;
- `certs/privkey.pem` — соответствующий закрытый ключ без пароля.

После этого та же команда автоматически запускает HTTPS:

```sh
python3 start.py
```

Swagger: `https://ВАШ-ДОМЕН:8011/docs`. Сертификат должен соответствовать домену. Откройте порт 8011 в firewall. Закрытый ключ должен читаться только учётной записью сервиса; сертификаты и ключи исключены из Git.

Другие пути и порт указываются в команде (относительные пути считаются от папки проекта):

```sh
python3 start.py --cert /etc/ssl/water-meter/fullchain.pem --key /etc/ssl/water-meter/privkey.pem --port 8443
```

Альтернатива аргументам: переменные `SSL_CERTFILE` и `SSL_KEYFILE`. После обновления сертификата перезапустите сервис. Если SSL уже завершается на вашем reverse proxy, не копируйте сертификаты в `certs/`, запускайте `python3 start.py --host 127.0.0.1`, направьте proxy на HTTP-порт 8011.

## API

POST `/api/read`, multipart-поле `file`, без дополнительных параметров. Единственный бизнес-эндпойнт; интерфейс — Swagger.

```json
{"serial_number":null,"serial_confidence":0.0,"reading":null,"reading_confidence":0.0}
```

Распознанные значения — строки. Нераспознанное поле — null и confidence 0. Confidence — консервативная оценка поддержки OCR, не калиброванная вероятность. Профили: БЕТАР, НОРМА, ЭКОМЕРА, регистр 5+3 цифры.

Датасетов и весов в Git нет. Стандартные ONNX-модели поставляются пакетом RapidOCR; отдельные обученные веса для этого MVP не требуются.

Тесты после первого запуска: `.venv/bin/python -m pytest test_service.py -q` (Windows: `.venv\Scripts\python.exe -m pytest test_service.py -q`).

Код MVP и упаковка репозитория выполнены Atlas AI agent по поручению владельца.
