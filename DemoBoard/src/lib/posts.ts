import { supabase } from "@/lib/supabase";
import type { Comment, Post, PostSummary } from "@/lib/types";

// --- Row shapes coming back from Supabase (snake_case, per Postgres/PostgREST
// convention) mapped to the camelCase app-facing types in src/lib/types.ts. ---

type CommentRow = {
  id: string;
  author: string;
  content: string;
  created_at: string;
};

type PostRow = {
  id: string;
  title: string;
  author: string;
  content: string;
  views: number;
  created_at: string;
  updated_at: string;
};

function mapComment(row: CommentRow): Comment {
  return {
    id: row.id,
    author: row.author,
    content: row.content,
    createdAt: row.created_at,
  };
}

function mapPost(row: PostRow & { comments?: CommentRow[] }): Post {
  return {
    id: row.id,
    title: row.title,
    author: row.author,
    content: row.content,
    views: row.views,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    comments: (row.comments ?? []).map(mapComment),
  };
}

// PostgREST's `or()` filter uses comma to separate conditions and `%`/`_` as
// ILIKE wildcards, so a raw search string needs those characters escaped/
// stripped to stay a well-formed filter.
function toSearchPattern(query: string): string {
  const escaped = query.replace(/[%_]/g, (m) => `\\${m}`).replace(/[,()]/g, " ");
  return `%${escaped}%`;
}

export const PAGE_SIZE = 10;

export async function listPosts(options: { query?: string; page?: number } = {}): Promise<{
  posts: PostSummary[];
  total: number;
  page: number;
  pageCount: number;
}> {
  const query = options.query?.trim();

  let countQuery = supabase.from("posts").select("id", { count: "exact", head: true });
  if (query) {
    const pattern = toSearchPattern(query);
    countQuery = countQuery.or(
      `title.ilike.${pattern},content.ilike.${pattern},author.ilike.${pattern}`
    );
  }
  const { count, error: countError } = await countQuery;
  if (countError) throw countError;

  const total = count ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const page = Math.min(Math.max(1, options.page ?? 1), pageCount);
  const start = (page - 1) * PAGE_SIZE;

  let dataQuery = supabase
    .from("posts")
    .select("id, title, author, views, created_at, updated_at, comments(count)")
    .order("created_at", { ascending: false })
    .range(start, start + PAGE_SIZE - 1);
  if (query) {
    const pattern = toSearchPattern(query);
    dataQuery = dataQuery.or(
      `title.ilike.${pattern},content.ilike.${pattern},author.ilike.${pattern}`
    );
  }
  const { data, error } = await dataQuery;
  if (error) throw error;

  const posts: PostSummary[] = (data ?? []).map((row) => {
    const commentCount = Array.isArray(row.comments)
      ? ((row.comments[0] as { count?: number } | undefined)?.count ?? 0)
      : 0;
    return {
      id: row.id,
      title: row.title,
      author: row.author,
      views: row.views,
      createdAt: row.created_at,
      updatedAt: row.updated_at,
      commentCount,
    };
  });

  return { posts, total, page, pageCount };
}

export async function getPost(id: string): Promise<Post | undefined> {
  const { data, error } = await supabase
    .from("posts")
    .select("*, comments(*)")
    .eq("id", id)
    .order("created_at", { foreignTable: "comments", ascending: true })
    .maybeSingle();
  if (error) throw error;
  if (!data) return undefined;
  return mapPost(data);
}

export async function incrementViews(id: string): Promise<void> {
  const { error } = await supabase.rpc("increment_post_views", { post_id: id });
  if (error) throw error;
}

export async function createPost(input: {
  title: string;
  author: string;
  content: string;
}): Promise<Post> {
  const { data, error } = await supabase
    .from("posts")
    .insert({ title: input.title, author: input.author, content: input.content })
    .select()
    .single();
  if (error) throw error;
  return mapPost({ ...data, comments: [] });
}

export async function updatePost(
  id: string,
  input: { title: string; author: string; content: string }
): Promise<Post | undefined> {
  const { data, error } = await supabase
    .from("posts")
    .update({
      title: input.title,
      author: input.author,
      content: input.content,
      updated_at: new Date().toISOString(),
    })
    .eq("id", id)
    .select("*, comments(*)")
    .maybeSingle();
  if (error) throw error;
  if (!data) return undefined;
  return mapPost(data);
}

export async function deletePost(id: string): Promise<boolean> {
  const { data, error } = await supabase.from("posts").delete().eq("id", id).select("id");
  if (error) throw error;
  return (data?.length ?? 0) > 0;
}

export async function addComment(
  postId: string,
  input: { author: string; content: string }
): Promise<Comment | undefined> {
  const { data, error } = await supabase
    .from("comments")
    .insert({ post_id: postId, author: input.author, content: input.content })
    .select()
    .single();
  if (error) {
    // Postgres foreign-key violation: the post doesn't exist (or was just deleted).
    if (error.code === "23503") return undefined;
    throw error;
  }
  return mapComment(data);
}

export async function deleteComment(postId: string, commentId: string): Promise<boolean> {
  const { data, error } = await supabase
    .from("comments")
    .delete()
    .eq("id", commentId)
    .eq("post_id", postId)
    .select("id");
  if (error) throw error;
  return (data?.length ?? 0) > 0;
}
