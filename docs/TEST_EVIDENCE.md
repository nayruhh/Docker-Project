# Test evidence

Generated on 2026-11-10 12:09 by running the API locally (uvicorn) and sending real HTTP requests.

## 1. API requests (live, against Gemini)

### Valid question (expect 200)

```
$ curl -X POST http://127.0.0.1:8001/ask -H 'Content-Type: application/json' -d '{"question":"What is the capital of France?"}'
{"answer":"The capital of France is **Paris**."}
HTTP 200
```

### Surrounding spaces are trimmed (expect 200)

```
$ curl -X POST http://127.0.0.1:8001/ask -H 'Content-Type: application/json' -d '{"question":"  What is 2+2?  "}'
{"answer":"2 + 2 = 4"}
HTTP 200
```

### Empty question (expect 422)

```
$ curl -X POST http://127.0.0.1:8001/ask -H 'Content-Type: application/json' -d '{"question":""}'
{"detail":[{"type":"string_too_short","loc":["body","question"],"msg":"String should have at least 1 character","input":"","ctx":{"min_length":1}}]}
HTTP 422
```

### Blank question (expect 422)

```
$ curl -X POST http://127.0.0.1:8001/ask -H 'Content-Type: application/json' -d '{"question":"   "}'
{"detail":[{"type":"string_too_short","loc":["body","question"],"msg":"String should have at least 1 character","input":"   ","ctx":{"min_length":1}}]}
HTTP 422
```

### Missing field (expect 422)

```
$ curl -X POST http://127.0.0.1:8001/ask -H 'Content-Type: application/json' -d '{}'
{"detail":[{"type":"missing","loc":["body","question"],"msg":"Field required","input":{}}]}
HTTP 422
```

### Wrong type (expect 422)

```
$ curl -X POST http://127.0.0.1:8001/ask -H 'Content-Type: application/json' -d '{"question":123}'
{"detail":[{"type":"string_type","loc":["body","question"],"msg":"Input should be a valid string","input":123}]}
HTTP 422
```

### Extra field (expect 422)

```
$ curl -X POST http://127.0.0.1:8001/ask -H 'Content-Type: application/json' -d '{"question":"hi","extra":1}'
{"detail":[{"type":"extra_forbidden","loc":["body","extra"],"msg":"Extra inputs are not permitted","input":1}]}
HTTP 422
```

### Too long, 2001 chars (expect 422)

```
$ curl -X POST http://127.0.0.1:8001/ask -H 'Content-Type: application/json' -d '{"question":"aaaaaaaaaaaaaaaaaaaa...(2001 chars)"}'
{"detail":[{"type":"string_too_long","loc":["body","question"],"msg":"String should have at most 2000 characters","input":"aaaaaaaaaaaaaaaaaaaa...(2001 chars)","ctx":{"max_length":2000}}]}
HTTP 422
```

### Wrong method (expect 405)

```
$ curl http://127.0.0.1:8001/ask
{"detail":"Method Not Allowed"}
HTTP 405
```

## 2. Generated log output (`logs/app.log`, written by the run above)

```
2026-11-10 12:09:02 | INFO     | main:16 | Application started
2026-11-10 12:09:04 | INFO     | routes:16 | POST /ask received
2026-11-10 12:09:04 | INFO     | llm:26 | Asking model gemini-3.5-flash (question length=30)
2026-11-10 12:09:14 | INFO     | llm:49 | Model answered (answer length=35)
2026-11-10 12:09:14 | INFO     | routes:16 | POST /ask received
2026-11-10 12:09:14 | INFO     | llm:26 | Asking model gemini-3.5-flash (question length=12)
2026-11-10 12:09:18 | INFO     | llm:49 | Model answered (answer length=9)
```

## 3. Automated tests (`uv run pytest -v`)

```
============================= test session starts =============================
platform win32 -- Python 3.13.7, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\naira\Desktop\Summit\Llm\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\naira\Desktop\Summit\Llm
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.16.0
collecting ... collected 20 items
tests/test_api.py::test_valid_question_returns_answer PASSED             [  5%]
tests/test_api.py::test_question_is_trimmed PASSED                       [ 10%]
tests/test_api.py::test_question_at_max_length_is_accepted PASSED        [ 15%]
tests/test_api.py::test_invalid_request_returns_422[empty] PASSED        [ 20%]
tests/test_api.py::test_invalid_request_returns_422[blank] PASSED        [ 25%]
tests/test_api.py::test_invalid_request_returns_422[too-long] PASSED     [ 30%]
tests/test_api.py::test_invalid_request_returns_422[missing] PASSED      [ 35%]
tests/test_api.py::test_invalid_request_returns_422[wrong-type] PASSED   [ 40%]
tests/test_api.py::test_invalid_request_returns_422[null] PASSED         [ 45%]
tests/test_api.py::test_invalid_request_returns_422[extra-field] PASSED  [ 50%]
tests/test_api.py::test_invalid_json_returns_422 PASSED                  [ 55%]
tests/test_api.py::test_wrong_method_returns_405 PASSED                  [ 60%]
tests/test_api.py::test_model_errors_are_passed_through[429] PASSED      [ 65%]
tests/test_api.py::test_model_errors_are_passed_through[502] PASSED      [ 70%]
tests/test_api.py::test_model_errors_are_passed_through[504] PASSED      [ 75%]
tests/test_logging_config.py::test_creates_console_and_file_handlers PASSED [ 80%]
tests/test_logging_config.py::test_log_line_is_written_to_file_with_format PASSED [ 85%]
tests/test_logging_config.py::test_console_respects_log_level_but_file_keeps_debug PASSED [ 90%]
tests/test_logging_config.py::test_invalid_log_level_falls_back_to_info PASSED [ 95%]
tests/test_logging_config.py::test_calling_setup_twice_does_not_duplicate_handlers PASSED [100%]
============================= 20 passed in 2.26s ==============================
```

## 4. PostgreSQL storage (`feat-postgres-storage`)

Verified against a real PostgreSQL 17 container, locally and via `docker compose`.

```
$ curl -X POST http://localhost:8000/ask -H 'Content-Type: application/json' -d '{"question":"Name one planet."}'
{"answer":"Mars"}
HTTP 200

$ curl http://localhost:8000/history
[{"id":1,"question":"Name one planet.","answer":"Mars","created_at":"2026-11-10T10:37:11.042718Z"}]
HTTP 200

$ curl "http://127.0.0.1:8002/history?limit=0"
{"detail":[{"type":"greater_than_equal","loc":["query","limit"],"msg":"Input should be greater than or equal to 1","input":"0","ctx":{"ge":1}}]}
HTTP 422
```

Row in the database after the local run:

```
 id |            question            |               answer                |          created_at
----+--------------------------------+-------------------------------------+------------------------------
  6 | What is the capital of France? | The capital of France is **Paris**. | 2026-11-10 10:36:09.02574+00
```

Log lines:

```
2026-11-10 10:37:02 | INFO     | db:39 | Database ready
2026-11-10 10:37:11 | INFO     | db:52 | Saved question/answer to database
```

Automated tests: `30 passed` (27 mocked + 3 against a real Postgres via `TEST_DATABASE_URL`).

## 5. Redis flow and duplicate-question strategy

Run against a real PostgreSQL and a real Redis (model stubbed, because it needs an API key):

```
200 MISS What is the capital of France?
200 HIT  what is  the CAPITAL of france?
200 MISS Something else?
model calls: 2          (three submissions, the model ran twice)
```

```
    id    |            question             |      normalized_question       | cache_hit
----------+---------------------------------+--------------------------------+-----------
 054dec1c | What is the capital of France?  | what is the capital of france? | f
 1e896c56 | what is  the CAPITAL of france? | what is the capital of france? | t
 93443380 | Something else?                 | something else?                | f
```

Each submission has its own row (new UUID), the original question is kept as typed, and the
cache hit is marked. The Redis entries had a TTL of 3599 seconds (1 hour).

Automated tests (`tests/test_cache_flow.py`) assert the exact call order:
MISS = `redis_get, generate, save, redis_set`; HIT = `redis_get, save(cache_hit=True)` with no
generation; a failed generation is neither saved nor cached; and the API still answers when
Redis is unreachable.

## 6. Docker Compose stack

```
SERVICE    STATUS                    PORTS
backend    Up 5 seconds (healthy)    0.0.0.0:8000->8000/tcp
postgres   Up 11 seconds (healthy)   5432/tcp
redis      Up 11 seconds (healthy)   6379/tcp
```

Only the backend is published to the host. The backend runs as a non-root user and applies
the migration when it starts:

```
$ docker compose exec backend id
uid=10001(appuser) gid=10001(appuser) groups=10001(appuser)

INFO  [alembic.runtime.migration] Running upgrade  -> 0001, create qa_records
Database ready
```

It connects by service name (`POSTGRES_HOST=postgres`, `REDIS_URL=redis://redis:6379/0`).

### Records survive container removal

```
before: [{"id":"bb66a5e6-8963-40c2-9db8-7f50520014fe","question":"Will I survive a restart?","answer":"Yes, via the postgres_data volume", ...}]

$ docker compose down        # removes all three containers and the network, keeps the volume
Container qademo-backend-1 Removed   Container qademo-redis-1 Removed   Container qademo-postgres-1 Removed

$ docker compose up -d --wait
after:  [{"id":"bb66a5e6-8963-40c2-9db8-7f50520014fe","question":"Will I survive a restart?","answer":"Yes, via the postgres_data volume", ...}]
```

The same record with the same UUID is returned after every container was removed and recreated.
The multi-stage image is about 77 MB, compared with about 336 MB for the earlier single-stage image.
