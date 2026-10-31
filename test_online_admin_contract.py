"""Static contract checks for the shared online-account admin API."""
from pathlib import Path

root = Path(__file__).resolve().parent
game = (root / "game.py").read_text(encoding="utf-8")
server = (root / "server" / "app.py").read_text(encoding="utf-8")
config = (root / "server_config.json").read_text(encoding="utf-8")

# The desktop client calls the protected server-wide account search route.
assert '"/api/admin/users?q="' in game
route = server.split('@APP.get("/api/admin/users")', 1)[1].split('@APP.get("/api/admin/users/<username>")', 1)[0]
assert "@require_admin" in route
assert "nickname ILIKE" in route and "username ILIKE" in route
assert '"total": len(users)' in route
assert "LIMIT" not in route.upper(), "The admin search must not silently hide accounts beyond a fixed cap."

# Admin mutations are server-authenticated and operate on the shared users table.
for path in ("/update", "/ban", "/skills", "/heal"):
    assert path in server
assert "@require_admin" in server
assert 'os.environ.get("DATABASE_URL"' in server
assert 'os.environ.get("ADMIN_PASSWORD"' in server

# A released game build uses the same API URL file next to the executable.
assert '"api_url": ""' in config
assert '"api_url"' in game
print("PASS: online admin is server-authenticated and searches all PostgreSQL users by username/nickname")
