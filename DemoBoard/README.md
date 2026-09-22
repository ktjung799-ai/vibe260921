# DemoBoard

Next.js (App Router) · TypeScript · shadcn/ui · Supabase로 만든 데모 게시판 사이트입니다.

## 기능

- 게시글 목록 (검색, 페이지네이션)
- 글쓰기 / 상세보기 / 수정 / 삭제
- 댓글 작성 / 삭제
- 조회수 카운트
- 작업 결과 토스트 알림 (등록/수정/삭제)

## 시작하기

### 1. Supabase 프로젝트 준비

1. [supabase.com](https://supabase.com) 에서 프로젝트를 만듭니다 (이미 있다면 생략).
2. 프로젝트의 **SQL Editor**에서 [`supabase/schema.sql`](./supabase/schema.sql) 내용을 그대로 실행합니다.
   `posts`, `comments` 테이블과 조회수 증가용 함수, RLS 정책, 샘플 글 2개가 생성됩니다.
3. **Project Settings → API**에서 `Project URL`과 `Publishable key`(`sb_publishable_...`)를 복사합니다.

### 2. 환경 변수 설정

```bash
cp .env.local.example .env.local
```

`.env.local`을 열어 위에서 복사한 값을 채워 넣습니다.

```
NEXT_PUBLIC_SUPABASE_URL=https://xxxxxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
```

### 3. 앱 실행

```bash
npm install
npm run dev
```

브라우저에서 [http://localhost:3000](http://localhost:3000) 을 엽니다.

## 데이터 저장

Supabase(Postgres)에 `posts`, `comments` 두 테이블로 저장됩니다. 이 앱은 별도 로그인 기능이 없는 데모이므로, RLS 정책이 익명(anon) 사용자에게 읽기/쓰기를 모두 허용하도록 되어 있습니다. 실제 서비스에 사용하려면 인증을 추가하고 정책을 좁혀야 합니다.

## 주요 구조

- `supabase/schema.sql` — 테이블/함수/RLS 정책/샘플 데이터 SQL
- `src/lib/supabase.ts` — Supabase 클라이언트
- `src/lib/posts.ts` — 게시글/댓글 데이터 접근 계층 (Supabase 쿼리)
- `src/app/posts/actions.ts` — 글/댓글 생성·수정·삭제 Server Actions
- `src/app/page.tsx` — 게시글 목록
- `src/app/posts/new`, `src/app/posts/[id]`, `src/app/posts/[id]/edit` — 글쓰기/상세/수정 페이지
- `src/components/board/*` — 게시판 전용 UI 컴포넌트
- `src/components/ui/*` — shadcn/ui 컴포넌트
