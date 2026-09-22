import Link from "next/link";
import { Eye, MessageCircle } from "lucide-react";
import { listPosts } from "@/lib/posts";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { BoardSearch } from "@/components/board/board-search";
import { BoardPagination } from "@/components/board/board-pagination";
import { ToastOnParam } from "@/components/board/toast-on-param";

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

export default async function HomePage(props: PageProps<"/">) {
  const searchParams = await props.searchParams;
  const q = typeof searchParams.q === "string" ? searchParams.q : undefined;
  const pageParam = typeof searchParams.page === "string" ? Number(searchParams.page) : 1;

  const { posts, total, page, pageCount } = await listPosts({
    query: q,
    page: Number.isFinite(pageParam) ? pageParam : 1,
  });

  return (
    <div className="flex flex-col gap-6">
      <ToastOnParam param="deleted" message="글이 삭제되었습니다." />

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-semibold">게시판</h1>
          <p className="text-sm text-muted-foreground">
            총 {total}개의 글{q ? ` · "${q}" 검색 결과` : ""}
          </p>
        </div>
        <BoardSearch defaultValue={q} />
      </div>

      <div className="overflow-hidden rounded-xl border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-14 text-center">번호</TableHead>
              <TableHead>제목</TableHead>
              <TableHead className="w-28">작성자</TableHead>
              <TableHead className="w-24">작성일</TableHead>
              <TableHead className="w-16 text-center">조회</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {posts.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="h-32 text-center text-muted-foreground">
                  {q ? "검색 결과가 없습니다." : "등록된 글이 없습니다."}
                </TableCell>
              </TableRow>
            ) : (
              posts.map((post, idx) => (
                <TableRow key={post.id}>
                  <TableCell className="text-center text-muted-foreground">
                    {total - ((page - 1) * 10 + idx)}
                  </TableCell>
                  <TableCell>
                    <Link
                      href={`/posts/${post.id}`}
                      className="font-medium hover:underline underline-offset-4"
                    >
                      {post.title}
                    </Link>
                    {post.commentCount > 0 && (
                      <Badge variant="secondary" className="ml-2 align-middle">
                        <MessageCircle data-icon="inline-start" />
                        {post.commentCount}
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{post.author}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDate(post.createdAt)}
                  </TableCell>
                  <TableCell className="text-center text-muted-foreground">
                    <span className="inline-flex items-center gap-1">
                      <Eye className="size-3.5" />
                      {post.views}
                    </span>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <BoardPagination page={page} pageCount={pageCount} query={q} />
    </div>
  );
}
