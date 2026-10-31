# 천상 RPG 온라인 서버 설정 (기존 talking-on-db 재사용)

이 구성은 Render에 천상 RPG API 웹 서비스만 만들고, 이미 있는 Render PostgreSQL `talking-on-db`를 재사용합니다. 새 PostgreSQL 인스턴스를 만들지 않습니다.

## 데이터 분리와 안전
- 천상 RPG는 기존 데이터베이스 안에 `cheonsang_rpg` 전용 PostgreSQL 스키마를 만들고, 모든 테이블 조회/저장을 그 스키마에서만 수행합니다.
- 기존 프로젝트가 사용하는 `public` 스키마의 테이블은 생성·수정·삭제하지 않습니다.
- 기존 데이터베이스 자체를 삭제하거나 초기화하지 마세요.
- 기존 DB 사용자에게 스키마 생성 권한이 있어야 첫 실행이 성공합니다. Render에서 DB를 만든 기본 소유자 계정의 내부 연결 URL을 사용하세요.

## 1. GitHub
프로젝트 저장소 최상위에 `render.yaml`, `game.py`, `server/`가 있어야 합니다. `venv`, `.venv`, `build`, `dist`, `__pycache__`는 업로드하지 않아도 됩니다. 비밀번호나 연결 문자열을 소스 코드에 넣지 마세요.

## 2. Render Blueprint
1. Blueprint 이름은 현재 저장소의 Blueprint를 사용합니다.
2. Branch는 `main`, Blueprint Path는 `render.yaml`입니다.
3. 이 Blueprint는 `cheonsang-rpg-api` 웹 서비스만 생성합니다. 데이터베이스 리소스는 정의하지 않으므로 새 DB를 만들지 않습니다.
4. API 서비스 리전은 기존 DB와 같은 `Ohio`로 설정되어 있습니다.
5. 기존 Blueprint가 이미 만들어져 있는 경우 `sync: false` 변수 입력창이 다시 표시되지 않을 수 있습니다. 그런 경우 웹 서비스가 만들어진 뒤 서비스의 Environment 탭에서 아래 변수를 직접 추가하세요.

## 3. 기존 PostgreSQL 연결 (중요)
1. Render Dashboard에서 기존 `talking-on-db` 데이터베이스를 엽니다.
2. `Connect` 탭을 선택합니다.
3. `Internal Database URL`을 복사합니다. API 서비스도 Ohio 리전에 있으므로 내부 URL을 사용합니다.
4. Render의 `cheonsang-rpg-api` 웹 서비스 → `Environment` → `Add Environment Variable`에서:
   - Key: `DATABASE_URL`
   - Value: 방금 복사한 Internal Database URL
5. 같은 Environment 화면에 아래 값도 있는지 확인합니다.
   - `ADMIN_USERNAME` = `최연욱`
   - `ADMIN_PASSWORD` = 관리자가 직접 정한 8글자 이상의 비밀번호
6. Save and deploy를 누릅니다.

**DATABASE_URL은 비밀 정보입니다.** GitHub 파일, 게임 ZIP, 스크린샷, 채팅에 붙여 넣지 마세요. Render의 Environment 화면에만 입력하세요.

## 4. 배포 확인
배포가 끝나면 서비스 주소의 `/health`를 열어 다음과 비슷한 JSON을 확인합니다.

```json
{"ok":true,"service":"Cheonsang RPG API"}
```

그 후 서비스 주소를 게임 프로젝트의 `server_config.json`에 입력합니다. 주소 끝에 `/health` 또는 `/api`를 붙이지 않습니다.

```json
{
  "api_url": "https://실제-cheonsang-rpg-api-주소.onrender.com"
}
```

EXE를 다시 빌드한 뒤 모든 플레이어에게 같은 API 주소가 설정된 게임을 배포해야 계정이 공유됩니다.

## 5. 기존 로컬 계정 가져오기
온라인 API에 관리자 로그인이 가능한 것을 먼저 확인한 다음 게임이 꺼진 상태에서 `IMPORT_LOCAL_ACCOUNTS.bat`을 실행합니다. 이 도구는 비밀번호 원문 대신 기존 PBKDF2 salt/hash와 저장 데이터를 전송합니다. 이미 존재하는 아이디는 덮어쓰지 않고 건너뜁니다.

## 온라인 관리자 기능
- 닉네임 또는 아이디로 서버 전체 계정 검색
- 밴/언밴, 점수/레벨/골드/경험치 수정
- 스탯 포인트, 마나 코어, 힘/체력/마나/민첩 수정
- 스킬북 지급, HP/MP 회복
- 수정된 계정의 기존 세션을 종료해 오래된 게임 화면이 수정값을 덮어쓰지 않도록 처리

## 운영 주의
현재 재사용하는 `talking-on-db`는 Render Free PostgreSQL이며, 대시보드상 만료 예정일은 **2026-11-11**입니다. 이 날짜 전에 장기 보존이 가능한 DB 플랜 또는 별도 영구 DB로 이전해야 합니다. 기존 데이터베이스를 재사용한다고 해서 무료 DB 만료일이 연장되는 것은 아닙니다.

무료 웹 서비스는 유휴 상태에서 잠들 수 있어 첫 접속이 느릴 수 있습니다. 이 구성은 계정/캐릭터 데이터 공유용 API이며, 실시간 필드 멀티플레이 서버는 아닙니다.
