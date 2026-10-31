"""Headless smoke tests for local data and gameplay progression."""
import json
import os
import sqlite3
import sys
import tempfile
import types
from pathlib import Path

# game.py can be imported without opening a display by providing only the Rect API
# used for module-level UI constants. Runtime rendering still requires pygame-ce.
class FakeRect:
    def __init__(self, *args):
        self.args = args

sys.modules['pygame'] = types.SimpleNamespace(Rect=FakeRect)
tmp_root = tempfile.mkdtemp(prefix='cheonsang-rpg-test-')
os.environ['XDG_DATA_HOME'] = tmp_root
sys.path.insert(0, str(Path(__file__).resolve().parent))
import game

# Make an old-style SQLite DB first; Database must upgrade it without losing records.
old_dir = Path(tmp_root) / 'CheonsangRPG'
old_dir.mkdir(parents=True, exist_ok=True)
old_db_path = old_dir / 'game.db'
conn = sqlite3.connect(old_db_path)
conn.execute("""CREATE TABLE users (
    username TEXT PRIMARY KEY, salt BLOB NOT NULL, password_hash BLOB NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0, banned INTEGER NOT NULL DEFAULT 0,
    score INTEGER NOT NULL DEFAULT 0, gold INTEGER NOT NULL DEFAULT 120,
    level INTEGER NOT NULL DEFAULT 1, exp INTEGER NOT NULL DEFAULT 0,
    hp INTEGER NOT NULL DEFAULT 100, max_hp INTEGER NOT NULL DEFAULT 100,
    mp INTEGER NOT NULL DEFAULT 50, max_mp INTEGER NOT NULL DEFAULT 50,
    state TEXT NOT NULL DEFAULT '{}', created_at TEXT DEFAULT CURRENT_TIMESTAMP
)""")
salt = b'0123456789abcdef'
conn.execute("INSERT INTO users(username,salt,password_hash,state) VALUES(?,?,?,?)",
             ('old_user', salt, game.Database.hash_password('test1234', salt), '{}'))
conn.commit()
conn.close()

db = game.Database()
assert db.refresh_user('old_user')['nickname'] == 'old_user'

# Legacy saves that used to store skill names in "special" now migrate them to
# books, not directly to learned skills. Quest items are preserved.
legacy_state = {
    'special': ['수상한 종이', '이상한 스킬', '마나 감지'],
    'learned_skills': [],
    'equipped_skills': {'E': '이상한 스킬', 'T': '마나 감지'},
}
conn = sqlite3.connect(old_db_path)
conn.execute('UPDATE users SET state=? WHERE username=?', (json.dumps(legacy_state, ensure_ascii=False), 'old_user'))
conn.commit()
conn.close()
legacy_player = game.Player(db.refresh_user('old_user'))
assert legacy_player.state['learned_skills'] == []
assert '이상한 스킬 스킬북' in legacy_player.state['skill_books']
assert '마나 감지 스킬북' in legacy_player.state['skill_books']
assert '수상한 종이' in legacy_player.state['special']
assert legacy_player.state['equipped_skills'] == {}

# New accounts receive a separate nickname and start without any learned skills.
ok, msg = db.register('tester01', 'test1234', '별빛여행자')
assert ok, msg
row = db.refresh_user('tester01')
assert row['nickname'] == '별빛여행자'
p = game.Player(row)
assert p.nickname == '별빛여행자'
assert p.state['learned_skills'] == []
assert p.state['skill_books'] == []

# Admin account search by nickname works in local test mode too.
assert any(u['username'] == 'tester01' for u in db.list_users('별빛여행자'))

# Stats and mana core progression.
base_attack = p.attack
p.state['stats']['strength'] = 2
assert p.attack > base_attack
p.state['mana_core_level'] = 2
assert p.attack > base_attack * 2
p.add_exp(100)
assert p.level == 2 and p.state['stat_points'] >= 8

for field, value, expected in [('level', 15, 15), ('score', 9876, 9876), ('gold', 12345, 12345), ('exp', 77, 77)]:
    assert db.admin_set_value('tester01', field, value)
    assert db.refresh_user('tester01')[field] == expected
assert db.admin_set_value('tester01', 'stat_points', 44)
assert json.loads(db.refresh_user('tester01')['state'])['stat_points'] == 44
assert db.admin_set_value('tester01', 'core', 3)
assert json.loads(db.refresh_user('tester01')['state'])['mana_core_level'] == 3
assert db.admin_set_value('tester01', 'vitality', 5)
assert json.loads(db.refresh_user('tester01')['state'])['stats']['vitality'] == 5
assert db.admin_set_value('tester01', 'mana', 4)
assert json.loads(db.refresh_user('tester01')['state'])['stats']['mana'] == 4
assert db.admin_grant_skills('tester01')
admin_granted_state = json.loads(db.refresh_user('tester01')['state'])
assert admin_granted_state['learned_skills'] == []
assert '이상한 스킬 스킬북' in admin_granted_state['skill_books']
assert '마나 감지 스킬북' in admin_granted_state['skill_books']
assert '마나 순환 스킬북' not in admin_granted_state['skill_books']
assert db.admin_heal('tester01')

# Fake game instance for pure gameplay methods.
class FakeGame:
    def __init__(self, player):
        self.player = player
        self.db = db
        self.enemies = []
        self.messages = []
        self.add_skill_book = lambda skill: game.Game.add_skill_book(self, skill)
    def toast_msg(self, *args, **kwargs):
        pass

p = game.Player(db.refresh_user('tester01'))
p.state['learned_skills'] = []
p.state['special'] = []
p.state['skill_books'] = []
p.state['mana_detection'] = 0
fake = FakeGame(p)

game.Game.add_skill_book(fake, '마나 감지')
assert '마나 감지 스킬북' in p.state['skill_books']
assert '마나 감지' not in p.state['learned_skills']
game.Game.learn_skill_book(fake, '마나 감지 스킬북')
assert '마나 감지' in p.state['learned_skills']
assert p.state['equipped_skills']['T'] == '마나 감지'
p.mp = 50
game.Game.use_mana_skill(fake)
assert p.mp == 0 and p.state['mana_detection'] == 5000
p.mp = 50
p.mana_skill_cd = 0
game.Game.use_mana_skill(fake)
assert '마나 감지' not in p.state['learned_skills']
assert '마나 순환' in p.state['learned_skills']
assert p.state['equipped_skills']['T'] == '마나 순환'

# Pyramid guardian yields a paper and an unusual skill book; the book must be learned
# before the pyramid path becomes available (the skill isn't pre-granted).
p.zone = '샌드 사막'
p.state['special'] = []
p.state['learned_skills'] = []
guardian = game.Enemy('피라미드 수호자', 200, 200)
game.Game.add_loot(fake, guardian)
assert '수상한 종이' in p.state['special']
assert '이상한 스킬 스킬북' in p.state['skill_books']
assert '이상한 스킬' not in p.state['learned_skills']
game.Game.learn_skill_book(fake, '이상한 스킬 스킬북')
assert '이상한 스킬' in p.state['learned_skills']

# In the second world, monsters drop books; Ancient Guardian's invisibility detection
# remains a book until the player chooses to learn it.
p.zone = '2세계 · 별빛 황야'
p.state['learned_skills'] = []
p.state['skill_books'] = []
p.state['final_boss_defeated'] = False
mob = game.Enemy('성운 슬라임', 200, 200)
game.Game.add_loot(fake, mob)
assert '마나 감지 스킬북' in p.state['skill_books']
ancient = game.Enemy('고대 수호자', 220, 220)
game.Game.add_loot(fake, ancient)
assert '투명 감지 스킬북' in p.state['skill_books']
assert not any(e.is_boss for e in fake.enemies)
game.Game.learn_skill_book(fake, '투명 감지 스킬북')
assert '투명 감지' in p.state['learned_skills']
assert any(e.is_boss and e.name == game.FINAL_BOSS for e in fake.enemies)

# Final boss completion reward.
boss = next(e for e in fake.enemies if e.is_boss)
game.Game.add_loot(fake, boss)
assert p.state['final_boss_defeated'] is True
assert '파멸의 용핵' in p.state['special']

# Town return is unconditional from any map/zone.
class TravelStub:
    modal = 'map'
    player = p
    def enter_zone(self, zone):
        self.player.zone = zone
travel = TravelStub()
game.Game.travel_to_town(travel)
assert travel.modal == '' and p.zone == '천상 마을'

db.conn.close()
print('PASS: legacy skill-to-book migration, online-ready account fields, nickname search, clean skillbook start, admin book grants, stats/core, skill learning/hotkey mapping, mana evolution, pyramid quest, hidden boss, final clear')
