-- DemoBoard schema
-- Run this once in your Supabase project's SQL Editor
-- (Dashboard -> SQL Editor -> New query -> paste -> Run).

create table if not exists posts (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  author text not null,
  content text not null,
  views integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists comments (
  id uuid primary key default gen_random_uuid(),
  post_id uuid not null references posts (id) on delete cascade,
  author text not null,
  content text not null,
  created_at timestamptz not null default now()
);

create index if not exists comments_post_id_idx on comments (post_id);

-- Atomic view counter, so concurrent viewers don't race a read-modify-write
-- from the app.
create or replace function increment_post_views(post_id uuid)
returns void
language sql
as $$
  update posts set views = views + 1 where id = post_id;
$$;

-- Row Level Security. DemoBoard has no auth (anyone can write, matching the
-- original JSON-file version), so these policies simply allow the public
-- (anon) role to do everything. Tighten this if you add real users/auth.
alter table posts enable row level security;
alter table comments enable row level security;

drop policy if exists "Public read posts" on posts;
create policy "Public read posts" on posts for select using (true);
drop policy if exists "Public insert posts" on posts;
create policy "Public insert posts" on posts for insert with check (true);
drop policy if exists "Public update posts" on posts;
create policy "Public update posts" on posts for update using (true) with check (true);
drop policy if exists "Public delete posts" on posts;
create policy "Public delete posts" on posts for delete using (true);

drop policy if exists "Public read comments" on comments;
create policy "Public read comments" on comments for select using (true);
drop policy if exists "Public insert comments" on comments;
create policy "Public insert comments" on comments for insert with check (true);
drop policy if exists "Public delete comments" on comments;
create policy "Public delete comments" on comments for delete using (true);

-- Seed data (safe to re-run: only inserts when the table is empty).
insert into posts (title, author, content, views)
select * from (
  values
    (
      'DemoBoard에 오신 것을 환영합니다',
      '관리자',
      'Next.js, TypeScript, shadcn/ui로 만든 데모 게시판입니다.' || chr(10) || chr(10) ||
      '왼쪽 위 ''글쓰기'' 버튼으로 새 글을 작성해 보세요.',
      12
    ),
    (
      '게시판 사용법 안내',
      '관리자',
      '- 목록에서 제목을 클릭하면 상세 글을 볼 수 있어요.' || chr(10) ||
      '- 글 상세에서 수정/삭제가 가능합니다.' || chr(10) ||
      '- 댓글도 남길 수 있어요.',
      5
    )
) as seed (title, author, content, views)
where not exists (select 1 from posts);
