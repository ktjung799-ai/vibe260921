import random
import tkinter as tk

CELL = 20
COLS, ROWS = 30, 20
WIDTH, HEIGHT = COLS * CELL, ROWS * CELL
DELAY = 100  # ms per move

BG = "#141414"
GRID = "#1e1e1e"
HEAD = "#50dc64"
BODY = "#32aa46"
FOOD = "#e63c3c"
TEXT = "#f0f0f0"

KEYS = {
    "Up": (0, -1), "Down": (0, 1), "Left": (-1, 0), "Right": (1, 0),
    "w": (0, -1), "s": (0, 1), "a": (-1, 0), "d": (1, 0),
}


class Snake:
    def __init__(self, root):
        self.root = root
        root.title("Snake")
        root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg=BG, highlightthickness=0)
        self.canvas.pack()
        root.bind("<Key>", self.on_key)
        self.best = 0
        self.reset()
        self.tick()

    def reset(self):
        cx, cy = COLS // 2, ROWS // 2
        self.snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.direction = (1, 0)
        self.pending = self.direction
        self.score = 0
        self.game_over = False
        self.food = self.spawn_food()

    def spawn_food(self):
        free = [(x, y) for x in range(COLS) for y in range(ROWS) if (x, y) not in self.snake]
        return random.choice(free) if free else None

    def on_key(self, event):
        if event.keysym in ("Escape",):
            self.root.destroy()
            return
        if self.game_over:
            if event.keysym in ("Return", "space") or event.char.lower() == "r":
                self.reset()
            return
        d = KEYS.get(event.keysym) or KEYS.get(event.char.lower())
        if d and (d[0] + self.direction[0], d[1] + self.direction[1]) != (0, 0):
            self.pending = d

    def tick(self):
        if not self.game_over:
            self.step()
        self.draw()
        self.root.after(DELAY, self.tick)

    def step(self):
        self.direction = self.pending
        head = (self.snake[0][0] + self.direction[0], self.snake[0][1] + self.direction[1])
        grow = head == self.food
        body = self.snake if grow else self.snake[:-1]
        if not (0 <= head[0] < COLS and 0 <= head[1] < ROWS) or head in body:
            self.end()
            return
        self.snake.insert(0, head)
        if grow:
            self.score += 1
            self.food = self.spawn_food()
            if self.food is None:  # 판을 가득 채우면 승리
                self.end()
        else:
            self.snake.pop()

    def end(self):
        self.game_over = True
        self.best = max(self.best, self.score)

    def cell(self, pos, color):
        x, y = pos
        self.canvas.create_rectangle(
            x * CELL + 1, y * CELL + 1, (x + 1) * CELL - 1, (y + 1) * CELL - 1,
            fill=color, outline="")

    def draw(self):
        c = self.canvas
        c.delete("all")
        for x in range(COLS):
            for y in range(ROWS):
                if (x + y) % 2 == 0:
                    c.create_rectangle(x * CELL, y * CELL, (x + 1) * CELL, (y + 1) * CELL,
                                       fill=GRID, outline="")
        if self.food:
            self.cell(self.food, FOOD)
        for i, seg in enumerate(self.snake):
            self.cell(seg, HEAD if i == 0 else BODY)
        c.create_text(8, 8, anchor="nw", fill=TEXT, font=("Arial", 13),
                      text=f"Score: {self.score}  Best: {self.best}")
        if self.game_over:
            c.create_text(WIDTH // 2, HEIGHT // 2 - 20, fill=TEXT,
                          font=("Arial", 32, "bold"), text="GAME OVER")
            c.create_text(WIDTH // 2, HEIGHT // 2 + 25, fill=TEXT, font=("Arial", 13),
                          text="Enter / R: restart   Esc: quit")


if __name__ == "__main__":
    root = tk.Tk()
    Snake(root)
    root.mainloop()
