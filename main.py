import pygame
import sys
import os
import random
import asyncio
import json   



pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 960, 960

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Ratticus Strikes Again - TERRA Game")

SIZES = [48, 60, 80, 96, 120]
POINTS = [1, 2, 3, 4, 5]
MAX_BANANAS = 20
BASE_MOVE_INTERVAL = 200
BOOST_MOVE_INTERVAL = 100
BOOST_DURATION = 5000

TRAIN_CELLS = 5
TRAIN_SPEED = 900
SLIDE_MS = 1000
WARN_MS = 1500
TRAIN_WAIT = (6000, 12000)
FIRST_TRAIN_WAIT = (5000, 9000)

BG_DARK = (25, 20, 20)
BG_LIGHT = (35, 28, 28)
RAT_GRAY = (120, 120, 120)
PINK = (255, 182, 193)
WHITE = (255, 255, 255)
CHEESE_YELLOW = (255, 255, 102)
BANANA_YELLOW = (255, 220, 0)
CHILLI_RED = (255, 50, 50)

# Arrow keys + WASD (QWERTY) + ZQSD (AZERTY)
KEYS_UP = (pygame.K_UP, pygame.K_w, pygame.K_z)
KEYS_DOWN = (pygame.K_DOWN, pygame.K_s)
KEYS_LEFT = (pygame.K_LEFT, pygame.K_a, pygame.K_q)
KEYS_RIGHT = (pygame.K_RIGHT, pygame.K_d)

clock = pygame.time.Clock()
font = pygame.font.SysFont("monospace", 28, bold=True)
small_font = pygame.font.SysFont("monospace", 22, bold=True)
big_font = pygame.font.SysFont("monospace", 48, bold=True)

def load_high_score():
    if os.path.exists("highscore.json"):
        try:
            with open ("highscore.json", "r") as f :
                return json.load(f).get("highscore", 0)
        except Exception:
            return 0
    return 0
def save_highscore(new_score):
    if new_score > load_high_score():
        with open ("highscore.json", "w") as f :
            json.dump({"highscore": new_score}, f)


def load_raw(filename):
    if os.path.exists(filename):
        try:
            return pygame.image.load(filename).convert()
        except pygame.error:
            return None
    return None


def scaled(raw, w, h):
    if raw is None:
        return None
    img = pygame.transform.scale(raw, (w, h))
    img.set_colorkey((255, 255, 255))
    return img


def load_sound(filename):
    if os.path.exists(filename):
        try:
            return pygame.mixer.Sound(filename)
        except pygame.error:
            return None
    return None


SOUNDS = {
    "eating": load_sound("eating.ogg"),
    "dead": load_sound("dead.ogg"),
    "wrong": load_sound("wrong.ogg")
}

RAW = {name: load_raw(name + ".png")
       for name in ("cheese", "mouse", "body", "tail", "banana", "dead", "train", "track", "shield", "chilli", "crumb")}

raw_bg = load_raw("background.png")
BG_IMG = pygame.transform.scale(raw_bg, (WIDTH, HEIGHT)) if raw_bg else None

GRID_SIZE = 80
IMG = {}


def apply_size(size):
    global GRID_SIZE, IMG
    GRID_SIZE = size
    IMG = {n: scaled(RAW[n], size, size)
           for n in ("cheese", "mouse", "body", "tail", "banana", "dead", "track", "shield", "chilli")}
    IMG["train"] = scaled(RAW["train"], TRAIN_CELLS * size, size)


apply_size(GRID_SIZE)

rat = []
rat_dir = next_dir = (GRID_SIZE, 0)
cheese_pos = [0, 0]
bananas = []
particles = []
chilli_pos = None
chilli_timer = 0
shield_pos = None
has_shield = False
highscore = load_high_score()
score = 0
game_over = False
is_paused = False
size_idx = 2
points_per_food = POINTS[size_idx]
train = None
next_train_in = 0


def draw_text(text, fnt, y, color=WHITE):
    surf = fnt.render(text, True, color)
    screen.blit(surf, surf.get_rect(center=(WIDTH // 2, y)))


def draw_background():
    if BG_IMG:
        screen.blit(BG_IMG, (0, 0))
    else:
        for row in range(HEIGHT // GRID_SIZE):
            for col in range(WIDTH // GRID_SIZE):
                color = BG_DARK if (row + col) % 2 == 0 else BG_LIGHT
                pygame.draw.rect(screen, color, (col * GRID_SIZE, row * GRID_SIZE, GRID_SIZE, GRID_SIZE))


def draw_cheese(pos):
    if IMG["cheese"]:
        screen.blit(IMG["cheese"], (pos[0], pos[1]))
    else:
        pygame.draw.rect(screen, CHEESE_YELLOW, (pos[0], pos[1], GRID_SIZE, GRID_SIZE))


def draw_banana(pos):
    if IMG["banana"]:
        screen.blit(IMG["banana"], (pos[0], pos[1]))
    else:
        pygame.draw.rect(screen, BANANA_YELLOW, (pos[0], pos[1], GRID_SIZE, GRID_SIZE))


def draw_shield(pos):
    if pos and IMG["shield"]:
        screen.blit(IMG["shield"], (pos[0], pos[1]))
    elif pos:
        pygame.draw.circle(screen, (0, 200, 255), (pos[0] + GRID_SIZE // 2, pos[1] + GRID_SIZE // 2), GRID_SIZE // 3)


def draw_chilli(pos):
    if pos and IMG["chilli"]:
        screen.blit(IMG["chilli"], (pos[0], pos[1]))
    elif pos:
        pygame.draw.circle(screen, CHILLI_RED, (pos[0] + GRID_SIZE // 2, pos[1] + GRID_SIZE // 2), GRID_SIZE // 3)


def draw_rat(rat, direction):
    if chilli_timer > 0:
        hx, hy = rat[0][0] + GRID_SIZE // 2, rat[0][1] + GRID_SIZE // 2
        pygame.draw.circle(screen, CHILLI_RED, (hx, hy), GRID_SIZE // 2 + 6, 4)

    if len(rat) > 1:
        tail_pos = rat[-1]
        second_last = rat[-2]
        dx = tail_pos[0] - second_last[0]
        dy = tail_pos[1] - second_last[1]

        if IMG["tail"]:
            if dx > 0:
                rot_tail = IMG["tail"]
            elif dx < 0:
                rot_tail = pygame.transform.rotate(IMG["tail"], 180)
            elif dy < 0:
                rot_tail = pygame.transform.rotate(IMG["tail"], 90)
            else:
                rot_tail = pygame.transform.rotate(IMG["tail"], 270)
            screen.blit(rot_tail, (tail_pos[0], tail_pos[1]))
        else:
            tx, ty = tail_pos[0] + GRID_SIZE // 2, tail_pos[1] + GRID_SIZE // 2
            pygame.draw.line(screen, PINK, (tx, ty), (tx + dx // 2, ty + dy // 2), 5)

    for i in range(1, len(rat) - 1):
        segment = rat[i]
        prev_segment = rat[i - 1]

        if IMG["body"]:
            seg_dx = prev_segment[0] - segment[0]
            seg_dy = prev_segment[1] - segment[1]
            if seg_dx < 0:
                rot_body = IMG["body"]
            elif seg_dx > 0:
                rot_body = pygame.transform.flip(IMG["body"], True, False)
            elif seg_dy > 0:
                rot_body = pygame.transform.rotate(IMG["body"], 90)
            else:
                rot_body = pygame.transform.rotate(IMG["body"], 270)
            screen.blit(rot_body, (segment[0], segment[1]))
        else:
            cx, cy = segment[0] + GRID_SIZE // 2, segment[1] + GRID_SIZE // 2
            pygame.draw.circle(screen, RAT_GRAY, (cx, cy), GRID_SIZE // 2 - 2)

    hx, hy = rat[0][0], rat[0][1]
    head_img = IMG["dead"] if (game_over and IMG["dead"]) else IMG["mouse"]
    if head_img is not None:
        rot_head = head_img
        if direction == (GRID_SIZE, 0):
            rot_head = pygame.transform.flip(head_img, True, False)
        elif direction == (0, -GRID_SIZE):
            rot_head = pygame.transform.rotate(head_img, 270)
        elif direction == (0, GRID_SIZE):
            rot_head = pygame.transform.rotate(head_img, 90)
        screen.blit(rot_head, (hx, hy))
    else:
        pygame.draw.circle(screen, RAT_GRAY, (hx + GRID_SIZE // 2, hy + GRID_SIZE // 2), GRID_SIZE // 2)

    if has_shield:
        hx, hy = rat[0][0] + GRID_SIZE // 2, rat[0][1] + GRID_SIZE // 2
        pygame.draw.circle(screen, (0, 200, 255), (hx, hy), GRID_SIZE // 2 + 4, 3)


def new_train():
    horizontal = random.choice([True, False])
    count = (HEIGHT if horizontal else WIDTH) // GRID_SIZE
    return {
        "horizontal": horizontal,
        "index": random.randrange(count),
        "forward": random.choice([True, False]),
        "phase": "slide_in",
        "t": 0,
        "pos": 0.0,
    }


def update_train(dt):
    global train, next_train_in
    if train is None:
        next_train_in -= dt
        if next_train_in <= 0:
            train = new_train()
        return

    train["t"] += dt
    phase = train["phase"]
    length = TRAIN_CELLS * GRID_SIZE
    span = WIDTH if train["horizontal"] else HEIGHT

    if phase == "slide_in" and train["t"] >= SLIDE_MS:
        train["phase"], train["t"] = "warning", 0
    elif phase == "warning" and train["t"] >= WARN_MS:
        train["phase"], train["t"] = "train", 0
        train["pos"] = -length if train["forward"] else span
    elif phase == "train":
        move = TRAIN_SPEED * dt / 1000
        train["pos"] += move if train["forward"] else -move
        if (train["forward"] and train["pos"] > span) or (not train["forward"] and train["pos"] < -length):
            train["phase"], train["t"] = "slide_out", 0
    elif phase == "slide_out" and train["t"] >= SLIDE_MS:
        train = None
        next_train_in = random.randint(*TRAIN_WAIT)


def train_rect():
    length = TRAIN_CELLS * GRID_SIZE
    if train["horizontal"]:
        return pygame.Rect(int(train["pos"]), train["index"] * GRID_SIZE, length, GRID_SIZE)
    return pygame.Rect(train["index"] * GRID_SIZE, int(train["pos"]), GRID_SIZE, length)


def train_hits_rat():
    tr = train_rect()
    for seg in rat:
        cell = pygame.Rect(seg[0], seg[1], GRID_SIZE, GRID_SIZE).inflate(-GRID_SIZE // 5, -GRID_SIZE // 5)
        if tr.colliderect(cell):
            return True
    return False


def draw_track_tile(x, y, horizontal):
    G = GRID_SIZE
    img = IMG["track"]
    if img is not None:
        if not horizontal:
            img = pygame.transform.rotate(img, 90)
        screen.blit(img, (x, y))
        return
    rail = max(3, G // 16)
    pygame.draw.rect(screen, (70, 55, 40), (x, y, G, G))
    tie = (101, 67, 33)
    steel = (170, 170, 170)
    if horizontal:
        pygame.draw.rect(screen, tie, (x + int(G * 0.35), y + 3, int(G * 0.3), G - 6))
        pygame.draw.rect(screen, steel, (x, y + int(G * 0.2), G, rail))
        pygame.draw.rect(screen, steel, (x, y + int(G * 0.8) - rail, G, rail))
    else:
        pygame.draw.rect(screen, tie, (x + 3, y + int(G * 0.35), G - 6, int(G * 0.3)))
        pygame.draw.rect(screen, steel, (x + int(G * 0.2), y, rail, G))
        pygame.draw.rect(screen, steel, (x + int(G * 0.8) - rail, y, rail, G))


def draw_track():
    G = GRID_SIZE
    phase = train["phase"]
    if phase == "slide_in":
        p = min(train["t"] / SLIDE_MS, 1)
    elif phase == "slide_out":
        p = 1 - min(train["t"] / SLIDE_MS, 1)
    else:
        p = 1

    blink = phase == "warning" and (train["t"] // 250) % 2 == 0

    if train["horizontal"]:
        ox = int((p - 1) * WIDTH)
        y = train["index"] * G
        for col in range(WIDTH // G):
            draw_track_tile(col * G + ox, y, True)
        if blink:
            overlay = pygame.Surface((WIDTH, G), pygame.SRCALPHA)
            overlay.fill((255, 0, 0, 90))
            screen.blit(overlay, (0, y))
    else:
        oy = int((p - 1) * HEIGHT)
        x = train["index"] * G
        for row in range(HEIGHT // G):
            draw_track_tile(x, row * G + oy, False)
        if blink:
            overlay = pygame.Surface((G, HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 0, 0, 90))
            screen.blit(overlay, (x, 0))


def draw_train():
    tr = train_rect()
    img = IMG["train"]
    if img is not None:
        if train["horizontal"]:
            if not train["forward"]:
                img = pygame.transform.flip(img, True, False)
        else:
            img = pygame.transform.rotate(img, 270 if train["forward"] else 90)
        screen.blit(img, tr.topleft)
        return

    front = TRAIN_CELLS - 1 if train["forward"] else 0
    for i in range(TRAIN_CELLS):
        if train["horizontal"]:
            cell = pygame.Rect(tr.x + i * GRID_SIZE, tr.y, GRID_SIZE, GRID_SIZE)
        else:
            cell = pygame.Rect(tr.x, tr.y + i * GRID_SIZE, GRID_SIZE, GRID_SIZE)
        color = (200, 60, 60) if i == front else (150, 30, 30)
        pygame.draw.rect(screen, color, cell.inflate(-4, -4), border_radius=6)
        pygame.draw.circle(screen, (255, 230, 120), cell.center, max(4, GRID_SIZE // 10))


def spawn_cheese():
    while True:
        pos = [random.randint(0, WIDTH // GRID_SIZE - 1) * GRID_SIZE,
               random.randint(0, HEIGHT // GRID_SIZE - 1) * GRID_SIZE]
        if pos not in rat and pos not in bananas and pos != shield_pos and pos != chilli_pos:
            return pos

def spawn_particles(pos,img_key, count = 8):
    if not RAW.get(img_key):
        return
    for _ in range(count):
        particles.append({
            "x":pos[0] + GRID_SIZE // 2,
            "y":pos[1] + GRID_SIZE // 2,
            "dx": random.uniform(-3.5, 3.5),
            "dy": random.uniform(-3.5, 3.5),
            "img": scaled(RAW[img_key], GRID_SIZE // 3, GRID_SIZE // 3),
            "life":18,
            "max_life": 18
        })
def update_and_draw_particles():
    for p in particles[:]:
        p["x"] += p["dx"]
        p["y"] += p["dy"]
        p["life"] -= 1

        if p["life"] <= 0:
            particles.remove(p)
        else:
            alpha = int(255 * (p["life"] / p["max_life"]))
            img = p["img"].copy()
            img.set_alpha(alpha)
            rect = img.get_rect(center= (int(p["x"]), int(p["y"])))
            screen.blit(img, rect)



def spawn_banana():
    while True:
        pos = [random.randint(0, WIDTH // GRID_SIZE - 1) * GRID_SIZE,
               random.randint(0, HEIGHT // GRID_SIZE - 1) * GRID_SIZE]
        if pos not in rat and pos != cheese_pos and pos not in bananas and pos != shield_pos and pos != chilli_pos:
            return pos


def spawn_shield():
    while True:
        pos = [random.randint(0, WIDTH // GRID_SIZE - 1) * GRID_SIZE,
               random.randint(0, HEIGHT // GRID_SIZE - 1) * GRID_SIZE]
        if pos not in rat and pos != cheese_pos and pos not in bananas and pos != chilli_pos:
            return pos


def spawn_chilli():
    while True:
        pos = [random.randint(0, WIDTH // GRID_SIZE - 1) * GRID_SIZE,
               random.randint(0, HEIGHT // GRID_SIZE - 1) * GRID_SIZE]
        if pos not in rat and pos != cheese_pos and pos not in bananas and pos != shield_pos:
            return pos


def reset():
    global rat, rat_dir, next_dir, score, cheese_pos, game_over, bananas
    global is_paused, train, next_train_in, has_shield, shield_pos, chilli_pos, chilli_timer
    G = GRID_SIZE
    rat = [[3 * G, 3 * G], [2 * G, 3 * G], [1 * G, 3 * G]]
    rat_dir = next_dir = (G, 0)
    score = 0
    game_over = False
    has_shield = False
    shield_pos = None
    chilli_pos = None
    chilli_timer = 0
    is_paused = False
    bananas = []
    train = None
    next_train_in = random.randint(*FIRST_TRAIN_WAIT)
    cheese_pos = spawn_cheese()


async def start_screen(idx):
    slider = pygame.Rect(200, 640, 560, 10)
    start_btn = pygame.Rect(WIDTH // 2 - 130, 780, 260, 70)
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 150))
    dragging = False
    last = len(SIZES) - 1

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif ev.type == pygame.KEYDOWN:
                if ev.key in KEYS_LEFT:
                    idx = max(0, idx - 1)
                elif ev.key in KEYS_RIGHT:
                    idx = min(last, idx + 1)
                elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return idx
                elif ev.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if start_btn.collidepoint(ev.pos):
                    return idx
                if slider.inflate(40, 60).collidepoint(ev.pos):
                    dragging = True
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                dragging = False

        if dragging:
            frac = (pygame.mouse.get_pos()[0] - slider.left) / slider.width
            idx = max(0, min(last, round(frac * last)))

        if BG_IMG:
            screen.blit(BG_IMG, (0, 0))
        else:
            screen.fill(BG_DARK)
        screen.blit(dim, (0, 0))

        draw_text("RATTICUS STRIKES AGAIN", big_font, 120)
        draw_text("Eat the cheese. Avoid bananas. Watch the tracks!", small_font, 180)

        size = SIZES[idx]
        preview = scaled(RAW["mouse"], size, size)
        if preview:
            screen.blit(preview, preview.get_rect(center=(WIDTH // 2, 340)))
        else:
            pygame.draw.circle(screen, RAT_GRAY, (WIDTH // 2, 340), size // 2)

        draw_text(f"Rat size: {size}px   Grid: {WIDTH // size} x {HEIGHT // size}", font, 520)
        draw_text(f"Points per cheese: {POINTS[idx]}", font, 570, CHEESE_YELLOW)

        pygame.draw.rect(screen, (90, 90, 90), slider, border_radius=5)
        for i in range(len(SIZES)):
            nx = slider.left + int(i * slider.width / last)
            pygame.draw.line(screen, WHITE, (nx, slider.top - 10), (nx, slider.bottom + 10), 2)
        hx = slider.left + int(idx * slider.width / last)
        pygame.draw.circle(screen, CHEESE_YELLOW, (hx, slider.centery), 18)
        pygame.draw.circle(screen, (60, 60, 60), (hx, slider.centery), 18, 3)
        screen.blit(small_font.render("small", True, WHITE), (slider.left - 20, slider.bottom + 30))
        big_label = small_font.render("big", True, WHITE)
        screen.blit(big_label, (slider.right - big_label.get_width() + 20, slider.bottom + 30))

        pygame.draw.rect(screen, (60, 140, 60), start_btn, border_radius=12)
        pygame.draw.rect(screen, WHITE, start_btn, 3, border_radius=12)
        draw_text("START", font, start_btn.centery)

        draw_text("Drag the slider or use LEFT / RIGHT (A/D/Q), then ENTER", small_font, 900)

        pygame.display.flip()
        clock.tick(30)
        await asyncio.sleep(0)


async def win_screen():
    if os.path.exists("win.ogg"):
        pygame.mixer.music.load("win.ogg")
        pygame.mixer.music.play(-1)

    monologue = [
        "SQUEAK! 100 POINTS?!",
        "Ratticus reigns supreme...",
        "I AM THE CHEESE KING!",
        "Press ENTER to return to Menu"
    ]

    angle = 0
    bounce = 0
    bounce_dir = 1

    while True:
        clock.tick(30)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_m):
                pygame.mixer.music.stop()
                return

        angle = (angle + 4) % 360
        bounce += bounce_dir * 1.5
        if abs(bounce) > 20:
            bounce_dir *= -1

        draw_background()

        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        screen.blit(dim, (0, 0))

        draw_text("VICTORY!", big_font, 120, CHEESE_YELLOW)

        rat_img = RAW["mouse"] if RAW["mouse"] else None
        if rat_img:
            dance_size = 180
            scaled_rat = pygame.transform.scale(rat_img, (dance_size, dance_size))
            rot_rat = pygame.transform.rotate(scaled_rat, (angle % 30) - 15)
            rect = rot_rat.get_rect(center=(WIDTH // 2, 340 + int(bounce)))
            screen.blit(rot_rat, rect)

        y_start = 520
        for i, line in enumerate(monologue):
            color = CHEESE_YELLOW if i == 2 else WHITE
            fnt = font if i < 3 else small_font
            draw_text(line, fnt, y_start + (i * 60), color)

        pygame.display.flip()
        await asyncio.sleep(0)


async def play():
    global is_paused, game_over, rat_dir, next_dir, score, cheese_pos
    global has_shield, shield_pos, chilli_pos, chilli_timer

    reset()
    move_timer = 0

    while True:
        dt = clock.tick(30)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_p and not game_over:
                    is_paused = not is_paused

                if game_over and ev.key == pygame.K_r:
                    reset()
                    move_timer = 0

                if ev.key == pygame.K_m and (game_over or is_paused):
                    return

                if not is_paused and not game_over:
                    if ev.key in KEYS_UP and rat_dir != (0, GRID_SIZE):
                        next_dir = (0, -GRID_SIZE)
                    elif ev.key in KEYS_DOWN and rat_dir != (0, -GRID_SIZE):
                        next_dir = (0, GRID_SIZE)
                    elif ev.key in KEYS_LEFT and rat_dir != (GRID_SIZE, 0):
                        next_dir = (-GRID_SIZE, 0)
                    elif ev.key in KEYS_RIGHT and rat_dir != (-GRID_SIZE, 0):
                        next_dir = (GRID_SIZE, 0)

        if not is_paused and not game_over:
            update_train(dt)

            if chilli_timer > 0:
                chilli_timer -= dt

            current_interval = BOOST_MOVE_INTERVAL if chilli_timer > 0 else BASE_MOVE_INTERVAL

            move_timer += dt
            if move_timer >= current_interval:
                move_timer -= current_interval
                rat_dir = next_dir
                new_head = [rat[0][0] + rat_dir[0], rat[0][1] + rat_dir[1]]

                hit_wall = not (0 <= new_head[0] < WIDTH and 0 <= new_head[1] < HEIGHT)
                hit_self = new_head in rat[:-1]

                if hit_wall or hit_self:
                    if chilli_timer > 0:
                        pass
                    elif has_shield:
                        has_shield = False
                    else:
                        game_over = True
                        if SOUNDS["dead"]:
                            SOUNDS["dead"].play()
                else:
                    rat.insert(0, new_head)
                    rat.pop()

                    if shield_pos and new_head == shield_pos:
                        has_shield = True
                        shield_pos = None

                    if chilli_pos and new_head == chilli_pos:
                        chilli_timer = BOOST_DURATION
                        chilli_pos = None

                    if new_head in bananas:
                        if chilli_timer > 0:
                            bananas.remove(new_head)
                        elif has_shield:
                            has_shield = False
                            bananas.remove(new_head)
                        else:
                            game_over = True
                            if SOUNDS["wrong"]:
                                SOUNDS["wrong"].play()

                    elif new_head == cheese_pos:
                        spawn_particles(cheese_pos, "crumb", count = 10)
                        score += points_per_food
                        if SOUNDS["eating"]:
                            SOUNDS["eating"].play()
                        if score > load_high_score():
                            highscore = score
                            save_highscore(highscore)

                        if score >= 100:
                            await win_screen()
                            return

                        cheese_pos = spawn_cheese()

                        rand_val = random.random()
                        if not has_shield and shield_pos is None and rand_val < 0.15:
                            shield_pos = spawn_shield()
                        elif chilli_pos is None and chilli_timer <= 0 and rand_val < 0.30:
                            chilli_pos = spawn_chilli()
                        elif len(bananas) < MAX_BANANAS and rand_val < 0.70:
                            bananas.append(spawn_banana())

            if train is not None and train["phase"] == "train" and train_hits_rat():
                if not game_over:
                    if chilli_timer > 0:
                        pass
                    elif has_shield:
                        has_shield = False
                    else:
                        game_over = True
                        if SOUNDS["dead"]:
                            SOUNDS["dead"].play()

        draw_background()
        if train is not None:
            draw_track()
        draw_cheese(cheese_pos)
        if shield_pos:
            draw_shield(shield_pos)
        if chilli_pos:
            draw_chilli(chilli_pos)
        for b in bananas:
            draw_banana(b)
        draw_rat(rat, rat_dir)
        update_and_draw_particles()
        if train is not None and train["phase"] == "train":
            draw_train()

        screen.blit(font.render(f"Score: {score}    highscore:{load_high_score()}", True, WHITE), (15, 15))
        screen.blit(small_font.render(f"+{points_per_food} per cheese", True, CHEESE_YELLOW), (15, 52))

        if chilli_timer > 0:
            boost_secs = max(0, int(chilli_timer // 1000) + 1)
            screen.blit(small_font.render(f"BOOST & INVINCIBLE: {boost_secs}s", True, CHILLI_RED), (15, 85))

        if is_paused:
            draw_text("PAUSED", big_font, HEIGHT // 2)
            draw_text("P = resume   M = menu", font, HEIGHT // 2 + 60)
        if game_over:
            draw_text("GAME OVER", big_font, HEIGHT // 2 - 30)
            draw_text("R = restart   M = menu", font, HEIGHT // 2 + 30)

        pygame.display.flip()
        await asyncio.sleep(0)


async def main():
    global size_idx, points_per_food
    while True:
        size_idx = await start_screen(size_idx)
        apply_size(SIZES[size_idx])
        points_per_food = POINTS[size_idx]
        await play()

if __name__ == "__main__":
    asyncio.run(main())
#py -3.12 -m pygbag .
