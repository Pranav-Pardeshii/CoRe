# API Contracts

All endpoints match the contracts consumed by the Streamlit frontend (`frontend/api_client.py`).

## Health & Root

- `GET /` -> `200 OK`: `{"message": "MHT-CET College Predictor"}`
- `GET | HEAD /ping` -> `200 OK`: `{"status": "ok"}` (executes `SELECT 1`, public rate-limited)
- `GET /health/live` -> `200 OK`: `{"status": "alive"}` (process liveness, no DB call)
- `GET /health/ready` -> `200 OK`: `{"status": "ready"}` or `503 Service Unavailable`: `{"status": "unavailable"}` (verifies MySQL via `SELECT 1`)

## Authentication (`/auth`)

- `POST /auth/register`
  - Body (JSON): `{"username": str, "password": str}` (`username`: 3–50 chars matching `^[A-Za-z0-9_.-]{3,50}$`; `password`: 8–128 chars)
  - `200 OK`: `{"message": "User registered successfully."}`
  - `409 Conflict`: `{"detail": "Username already exists."}`
- `POST /auth/login`
  - Body (form-encoded `OAuth2PasswordRequestForm`): `username`, `password`
  - `200 OK`: `{"access_token": str, "token_type": "bearer"}`
  - `401 Unauthorized`: `{"detail": "Invalid username or password."}` (uniform for unknown user and wrong password, timing-equalized with dummy Argon2id check)
  - `429 Too Many Requests`: IP or per-username failed-login threshold exceeded

## Catalog (`/catalog`)

- `GET /catalog/filters` (`Cache-Control: public, max-age=3600`)
  - `200 OK`: `{"categories": [str], "branches": [str], "divisions": [str], "years": [int], "levels": [str]}`

## Recommendations (`/recommender`)

- `GET /recommender/` (`Cache-Control: public, max-age=3600`)
  - Query params: `percentile` (`0 <= x <= 100`), `category`, `branch`, `division`, `page` (`>= 1`, default `1`), `page_size` (`5 <= x <= 30`, default `10`)
  - `200 OK`: `{"eligible_colleges": [{"college": str, "branch": str, "branch_code": str, "min_cutoff": float, "max_cutoff": float}], "count": int}`

## Trends (`/trends`)

- `GET /trends/` (`Cache-Control: public, max-age=3600`)
  - Query params: `branch_code`, `category` (`"All"` defaults to `"GOPENS"`), `level` (optional `str`)
  - `200 OK`: `{"branch_code": str, "count": int, "trends": [{"year": int, "round": int, "level": str, "percentile": float}]}`

## Saved Lists (`/saved-lists`)

All endpoints require `Authorization: Bearer <token>`. User identity is derived from the signed JWT `sub` claim.

- `GET /saved-lists/` -> `200 OK`: `{"saved_list": [{"id": int, "college_name": str, "branch_name": str}]}`
- `POST /saved-lists/` -> Body `{"branch_code": str}` -> `200 OK`: `{"message": "Item saved successfully."}` (`409` on duplicate item, `400` on invalid branch or 100-item limit)
- `PUT /saved-lists/` -> Body `{"ordered_list": [int, ...]}` -> `200 OK`: `{"message": "Bingo! list reordered successfully!"}` (`422` on duplicate IDs in payload, `400` on mismatched/non-owned IDs)
- `DELETE /saved-lists/{id}` -> `200 OK`: `{"message": "Item deleted successfully!"}` (`404` if not found or not owned)
