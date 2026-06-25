# 2026-05-13 작업 정리

## 📋 오늘의 주요 작업

### 1. GitHub 저장소 연동
- **저장소:** https://github.com/cutysexywoong/First_step.git
- **목표:** 로컬 프로젝트를 GitHub과 연동

**🤔 쉬운 설명:**
- **GitHub = 파일 보관함:** 내 컴퓨터의 파일들을 인터넷에 있는 보관함(GitHub)에 저장하는 것
- **연동 = 연결하기:** 내 컴퓨터와 인터넷 보관함을 연결해서 파일을 주고받을 수 있게 만들기

---

## 🔧 작업 과정

### 1단계: Git 초기화 및 설정

**🤔 쉬운 설명:**
- **Git = 버전 관리 프로그램:** 파일의 변화를 기록하고 관리해주는 도구 (예: 게임 저장 포인트처럼!)
- **초기화 = 준비하기:** 이 폴더에서 Git을 사용하겠다고 선언하는 것

#### Git 설정
```bash
git config --global user.email "cocomoro5861@gmail.com"
git config --global user.name "cutysexywoong"
```

#### 저장소 초기화
```bash
cd c:\FIrst_Woong
git init
git add .
git commit -m "Initial commit: birthday check project"
```

**결과:**
- 7개 파일 추가
- Initial commit 생성 (커밋 해시: `2fa8153`)

**📝 쉬운 설명:**
- **commit = 저장:** 현재 파일들의 상태를 "카메라로 찍듯이" 저장하는 것
- **7개 파일:** birthday_check 프로젝트의 모든 파일들이 저장됨

---

### 2단계: SSH 키 생성

**🤔 쉬운 설명:**
- **SSH 키 = 열쇠:** 내 컴퓨터임을 증명하는 안전한 열쇠 (신분증처럼!)
- **공개 키 = 자물쇠:** GitHub에 올려두는 것
- **비공개 키 = 열쇠:** 내 컴퓨터에만 보관하는 것
- 둘이 짝을 이루어야 안전하게 연결됨

#### SSH 디렉토리 생성
```powershell
New-Item -ItemType Directory -Path $env:USERPROFILE\.ssh -Force
```

#### ED25519 SSH 키 생성
```bash
ssh-keygen -t ed25519 -C cocomoro5861@gmail.com -f $env:USERPROFILE\.ssh\id_ed25519
```

**생성된 키:**
- 공개 키: `id_ed25519.pub`
- 비공개 키: `id_ed25519`
- Key Fingerprint: `SHA256:oQhdJ+mDaVg6EXKlTHmltp8UbA//Q7U4vLcnNSrK63Q`

#### GitHub에 SSH 키 등록
✅ GitHub Settings > Authentication keys에 등록 완료
- 상태: "Added on May 13, 2026"
- 사용 상태: "Never used — Read/write"

**📝 쉬운 설명:**
- **Authentication keys = 인증 열쇠들:** GitHub에서 관리하는 나의 신분증들
- **Read/write = 읽고 쓰기:** 파일을 읽을 수도 있고 저장할 수도 있다는 뜻

---

### 3단계: 원격 저장소 연결 문제 및 해결

**🤔 쉬운 설명:**
- **원격 저장소 = 인터넷 보관함:** GitHub에 있는 나의 파일 보관소
- **로컬 저장소 = 내 컴퓨터:** 내 컴퓨터에 있는 파일들

#### 초기 시도 (실패)
```bash
git remote add origin https://github.com/cutysexywoong/First_step.git
git push -u origin main
```
❌ 오류: Permission denied (HTTPS 인증 문제)

#### 문제 원인 분석
1. **계정 혼용 문제:** 
   - GitHub 로그인 계정: `mrchoi5861-afk`
   - 저장소 소유자: `cutysexywoong`
   - 오류: HTTP 403 (권한 없음)

   **📝 쉬운 설명:** 내가 A라는 이름으로 로그인했는데, B라는 이름의 보관함에 들어가려고 한 것 (당연히 안 됨!)

2. **리모트 설정 혼란:**
   - `origin`: HTTPS (mrchoi5861-afk 계정)
   - `upstream`: SSH (cutysexywoong 계정)

   **📝 쉬운 설명:** 여러 개의 연결이 섞여 있어서 어느 것을 써야 할지 헷갈린 상태

#### 해결 과정

**Step 1: Credential 초기화**
```powershell
git credential reject host=github.com protocol=https
cmdkey /delete:git:https://github.com
```

**Step 2: 리모트 정리**
```bash
git remote remove origin
git remote rename upstream origin
```

**Step 3: 최종 설정 확인**
```bash
git remote -v
```

**결과:**
```
origin  https://github.com/cutysexywoong/First_step.git (fetch)
origin  https://github.com/cutysexywoong/First_step.git (push)
```

---

## ✅ 최종 상태

**🎉 축하합니다!** 모든 설정이 완료되었습니다!

### Git 설정
| 항목 | 값 |
|------|-----|
| **로컬 사용자** | cutysexywoong (cocomoro5861@gmail.com) |
| **원격 저장소** | https://github.com/cutysexywoong/First_step.git |
| **Branch** | main |
| **현재 커밋** | 2fa8153 - Initial commit |

**📝 쉬운 설명:**
- **Branch = 가지:** 여러 개의 작업을 동시에 하고 싶을 때 나누는 갈래 (나무 가지처럼!)
- **현재 커밋 = 현재 저장 상태:** 지금 저장되어 있는 파일들의 상태

### 추적된 파일 (총 7개)
```
✅ .vscode/settings.json
✅ .vscode/woong_exercise
✅ birthday_check/.gitignore
✅ birthday_check/README.md
✅ birthday_check/birthday_check_v1.py
✅ birthday_check/birthday_check_v2.py
✅ birthday_check/birthday_check_v3.py
```

### .gitignore 규칙
```
# Python bytecode
__pycache__/
*.py[cod]

# IDE settings
.vscode/
```

**📝 쉬운 설명:**
- **.gitignore = 무시할 파일 목록:** "이 파일들은 GitHub에 올리지 마!"라고 하는 것
- **__pycache__ = 임시 파일:** Python이 자동으로 만드는 캐시 (게임의 임시 저장 같은 거!)
- **.pyc, .pyo, .pyd = 컴파일된 파일:** 실행하기 쉽도록 변환된 파일 (중요하지 않으니 올리지 않음)

---

## 🚀 이후 작업 방법

**🤔 쉬운 설명:** 내 컴퓨터의 파일을 수정하고 GitHub에 업로드하는 과정

### 새 파일 추가 후 푸시
```bash
cd c:\FIrst_Woong
git add .              # 📝 수정한 모든 파일을 준비 (무대 리허설처럼!)
git commit -m "메시지"  # 💾 준비된 파일들을 저장 (게임 저장하기처럼!)
git push               # 🚀 GitHub에 업로드 (보관함에 넣기!)
```

**단계별 설명:**
1. **git add .** = "이 파일들을 올릴 준비를 해"
2. **git commit -m "메시지"** = "준비한 파일들을 저장해. 그리고 이 메시지를 기록해"
3. **git push** = "저장한 파일들을 GitHub에 업로드해"

### 일반적인 Git 명령어
```bash
# 상태 확인
git status              # ❓ "지금 뭐가 바뀌었어?" (현재 상태 보기)

# 최근 커밋 확인
git log --oneline -5    # 📋 "지금까지 뭘 저장했어?" (최근 5개 저장 보기)

# 변경사항 보기
git diff                # 🔍 "이전과 뭐가 달라졌어?" (변경 사항 비교)

# 원격 저장소에서 당겨오기
git pull origin main    # ⬇️ "GitHub에서 최신 파일을 받아와" (인터넷 보관함에서 받기)

# 특정 파일 추적 취소
git rm --cached 파일명  # 🚫 "이 파일은 더 이상 관리하지 마"
```

---

## 💡 추가 정보

### SSH 키 사용 설정
현재 HTTPS를 사용 중이지만, SSH 사용 시 설정:
```bash
git remote set-url origin git@github.com:cutysexywoong/First_step.git
```

**📝 쉬운 설명:**
- **HTTPS = 비밀번호 입력 방식:** 매번 로그인할 때 비밀번호를 입력하는 것
- **SSH = 열쇠 방식:** 미리 만든 열쇠(SSH 키)를 사용해서 자동으로 인증되는 것 (더 안전함!)

### VS Code 한글화 (참고)
- **Korean Language Pack** 확장팩 설치로 한글화 가능
- Microsoft 공식 확장팩: `MS-CEINTL.vscode-language-pack-ko`

**📝 쉬운 설명:**
- **확장팩 = 추가 기능:** VS Code에 기능을 더해주는 플러그인 (게임 모드처럼!)
- **Language Pack = 언어 팩:** 프로그램을 다른 언어로 바꿔주는 것

---

## 📅 날짜
**작업 완료일:** 2026-05-13 (May 13, 2026)

**작업 시간:** 오후 9시~10시경

**최종 상태:** ✅ GitHub 연동 완료

---

## 🎓 배운 것들 정리

| 용어 | 쉬운 설명 |
|------|---------|
| **Git** | 파일의 변화를 기록하는 도구 (게임 저장 포인트처럼!) |
| **GitHub** | 인터넷에 있는 파일 보관함 (클라우드!) |
| **Commit** | 파일들의 현재 상태를 사진처럼 찍어서 저장하는 것 |
| **Push** | 내 컴퓨터의 파일을 GitHub에 업로드하기 |
| **Pull** | GitHub에서 최신 파일을 내 컴퓨터로 받기 |
| **SSH 키** | 내 컴퓨터임을 증명하는 안전한 열쇠 |
| **Branch** | 여러 작업을 동시에 하기 위해 나누는 갈래 |
| **.gitignore** | "이 파일들은 GitHub에 올리지 마!"라고 하는 목록 |
