import tkinter as tk

WIDTH, HEIGHT = 600, 500
PADDLE_W, PADDLE_H = 90, 12
BALL_R = 8
ROWS, COLS = 6, 10
BRICK_W = WIDTH // COLS
BRICK_H = 22
COLORS = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#3498db", "#9b59b6"]
FPS_MS = 16


class Breakout:
    def __init__(self, root):
        self.root = root
        root.title("블럭깨기")
        root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="#111")
        self.canvas.pack()
        self.left = self.right = False
        root.bind("<KeyPress-Left>", lambda e: setattr(self, "left", True))
        root.bind("<KeyRelease-Left>", lambda e: setattr(self, "left", False))
        root.bind("<KeyPress-Right>", lambda e: setattr(self, "right", True))
        root.bind("<KeyRelease-Right>", lambda e: setattr(self, "right", False))
        root.bind("<Motion>", self.on_mouse)
        root.bind("<space>", self.on_space)
        root.bind("r", lambda e: self.reset())
        self.reset()
        self.loop()

    def reset(self):
        self.canvas.delete("all")
        self.score = 0
        self.lives = 3
        self.state = "ready"  # ready, playing, over, win
        self.bricks = {}
        for r in range(ROWS):
            for c in range(COLS):
                x1, y1 = c * BRICK_W, 50 + r * BRICK_H
                item = self.canvas.create_rectangle(
                    x1 + 1, y1 + 1, x1 + BRICK_W - 1, y1 + BRICK_H - 1,
                    fill=COLORS[r % len(COLORS)], outline="")
                self.bricks[item] = (x1, y1, x1 + BRICK_W, y1 + BRICK_H)
        self.paddle_x = WIDTH / 2
        self.paddle = self.canvas.create_rectangle(0, 0, 0, 0, fill="#ecf0f1", outline="")
        self.ball = self.canvas.create_oval(0, 0, 0, 0, fill="#fff", outline="")
        self.hud = self.canvas.create_text(10, 10, anchor="nw", fill="#fff",
                                           font=("Arial", 12))
        self.msg = self.canvas.create_text(WIDTH / 2, HEIGHT / 2, fill="#fff",
                                           font=("Arial", 18, "bold"), justify="center")
        self.place_ball()
        self.update_visuals()

    def place_ball(self):
        self.bx = self.paddle_x
        self.by = HEIGHT - 40 - BALL_R
        self.vx, self.vy = 4, -5
        self.state = "ready" if self.state not in ("over", "win") else self.state

    def on_mouse(self, e):
        self.paddle_x = min(max(e.x, PADDLE_W / 2), WIDTH - PADDLE_W / 2)

    def on_space(self, e):
        if self.state == "ready":
            self.state = "playing"
        elif self.state in ("over", "win"):
            self.reset()

    def loop(self):
        self.step()
        self.update_visuals()
        self.root.after(FPS_MS, self.loop)

    def step(self):
        if self.left:
            self.paddle_x -= 8
        if self.right:
            self.paddle_x += 8
        self.paddle_x = min(max(self.paddle_x, PADDLE_W / 2), WIDTH - PADDLE_W / 2)

        if self.state == "ready":
            self.bx = self.paddle_x
            return
        if self.state != "playing":
            return

        self.bx += self.vx
        self.by += self.vy

        # walls
        if self.bx < BALL_R:
            self.bx, self.vx = BALL_R, abs(self.vx)
        elif self.bx > WIDTH - BALL_R:
            self.bx, self.vx = WIDTH - BALL_R, -abs(self.vx)
        if self.by < BALL_R:
            self.by, self.vy = BALL_R, abs(self.vy)

        # paddle
        py = HEIGHT - 40
        if (self.vy > 0 and py <= self.by + BALL_R <= py + PADDLE_H + 6
                and abs(self.bx - self.paddle_x) <= PADDLE_W / 2 + BALL_R):
            offset = (self.bx - self.paddle_x) / (PADDLE_W / 2)
            speed = min((self.vx ** 2 + self.vy ** 2) ** 0.5 * 1.02, 10)
            self.vx = offset * speed * 0.8
            self.vy = -(max(speed ** 2 - self.vx ** 2, 4)) ** 0.5
            self.by = py - BALL_R

        # bricks
        for item, (x1, y1, x2, y2) in list(self.bricks.items()):
            if (x1 - BALL_R < self.bx < x2 + BALL_R
                    and y1 - BALL_R < self.by < y2 + BALL_R):
                overlap_x = min(self.bx + BALL_R - x1, x2 - (self.bx - BALL_R))
                overlap_y = min(self.by + BALL_R - y1, y2 - (self.by - BALL_R))
                if overlap_x < overlap_y:
                    self.vx = -self.vx
                else:
                    self.vy = -self.vy
                self.canvas.delete(item)
                del self.bricks[item]
                self.score += 10
                break

        if not self.bricks:
            self.state = "win"
        elif self.by > HEIGHT + BALL_R:
            self.lives -= 1
            if self.lives <= 0:
                self.state = "over"
            else:
                self.state = "ready"
                self.place_ball()

    def update_visuals(self):
        py = HEIGHT - 40
        self.canvas.coords(self.paddle, self.paddle_x - PADDLE_W / 2, py,
                           self.paddle_x + PADDLE_W / 2, py + PADDLE_H)
        self.canvas.coords(self.ball, self.bx - BALL_R, self.by - BALL_R,
                           self.bx + BALL_R, self.by + BALL_R)
        self.canvas.itemconfig(self.hud, text=f"점수: {self.score}    목숨: {self.lives}")
        texts = {
            "ready": "스페이스바로 시작\n← → 또는 마우스로 이동",
            "over": f"게임 오버! 점수: {self.score}\n스페이스바: 다시 시작",
            "win": f"클리어! 점수: {self.score}\n스페이스바: 다시 시작",
        }
        self.canvas.itemconfig(self.msg, text=texts.get(self.state, ""))
        self.canvas.tag_raise(self.msg)


if __name__ == "__main__":
    root = tk.Tk()
    Breakout(root)
    root.mainloop()
