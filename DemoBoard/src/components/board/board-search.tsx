import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search } from "lucide-react";

export function BoardSearch({ defaultValue }: { defaultValue?: string }) {
  return (
    <form action="/" method="get" className="flex w-full max-w-sm items-center gap-2">
      <Input
        type="search"
        name="q"
        placeholder="제목, 내용, 작성자 검색"
        defaultValue={defaultValue}
        aria-label="게시글 검색"
      />
      <Button type="submit" variant="outline" size="icon" aria-label="검색">
        <Search />
      </Button>
    </form>
  );
}
