import random

COLORS = ["红", "黄", "绿", "蓝"]


class Uno:
    name = "UNO"

    def __init__(self):
        self.deck = []
        self.discard = []
        self.hands = [[], []]
        self.turn = 0
        self.over = False
        self.winner = None
        self.pending_draw = 0
        self.current_color = None
        self._deal()

    def _newdeck(self):
        d = []
        for c in COLORS:
            d += [(c, str(n)) for n in range(10)]
            d += [(c, str(n)) for n in range(1, 10)]
            d += [(c, "跳过"), (c, "反转"), (c, "+2")] * 2
        d += [("万能", "变色")] * 4
        d += [("万能", "+4")] * 4
        random.shuffle(d)
        return d

    def _deal(self):
        self.deck = self._newdeck()
        self.discard = []
        self.hands = [[], []]
        self.turn = 0
        self.over = False
        self.winner = None
        self.pending_draw = 0
        self.current_color = None

        for _ in range(7):
            self.hands[0].append(self.deck.pop())
            self.hands[1].append(self.deck.pop())

        while True:
            c = self.deck.pop()
            if c[1] not in ("+4", "变色"):
                self.discard = [c]
                self.current_color = c[0]
                break
            self.deck.insert(0, c)
            random.shuffle(self.deck)

    def top(self):
        return self.discard[-1]

    def can_play(self, card):
        if self.over:
            return False
        color, value = card
        top_color, top_value = self.top()
        return (
            color == "万能"
            or color == self.current_color
            or value == top_value
        )

    def _choose_wild_color(self, who):
        colors = [c[0] for c in self.hands[who] if c[0] in COLORS]
        if colors:
            return max(COLORS, key=lambda c: colors.count(c))
        return random.choice(COLORS)

    def draw(self, who=0):
        if not (0 <= who < len(self.hands)):
            raise ValueError("玩家编号无效")
        if not self.deck:
            if len(self.discard) <= 1:
                return None
            top = self.discard[-1]
            self.deck = self.discard[:-1]
            self.discard = [top]
            random.shuffle(self.deck)
        if not self.deck:
            return None
        card = self.deck.pop()
        self.hands[who].append(card)
        return card

    def _effect(self, card, who):
        value = card[1]
        if value == "+2":
            self.pending_draw = 2
        elif value == "+4":
            self.pending_draw = 4
        elif value in ("跳过", "反转"):
            # 只有两名玩家时，跳过/反转都等价于当前玩家继续。
            self.turn = who
            return
        if card[0] == "万能":
            self.current_color = self._choose_wild_color(who)
        else:
            self.current_color = card[0]

    def player_play(self, index):
        if self.over or self.turn != 0:
            return {"ok": False, "reason": "现在不是你的回合"}
        try:
            i = int(index) - 1
        except Exception:
            return {"ok": False, "reason": "请输入手牌编号"}
        if not (0 <= i < len(self.hands[0])):
            return {"ok": False, "reason": "手牌编号无效"}

        card = self.hands[0][i]
        if not self.can_play(card):
            return {"ok": False, "reason": "这张牌不能出"}

        self.hands[0].pop(i)
        self.discard.append(card)
        self._effect(card, 0)

        if not self.hands[0]:
            self.over = True
            self.winner = "player"
            return {"ok": True, "result": "player_win", "card": card}

        # 跳过/反转：玩家继续；其它牌：轮到桌宠。
        if card[1] in ("跳过", "反转"):
            self.turn = 0
            return {"ok": True, "result": "continue", "card": card, "skip": True}

        self.turn = 1
        return {"ok": True, "card": card, "hand": self.hands[0]}

    def ai_turn(self):
        if self.over or self.turn != 1:
            return {"action": "none", "reason": "现在不是桌宠回合"}

        if self.pending_draw:
            count = self.pending_draw
            drawn = 0
            for _ in range(count):
                if self.draw(1) is None:
                    break
                drawn += 1
            self.pending_draw = 0
            self.turn = 0
            return {"action": "draw", "count": drawn}

        playable = [(i, c) for i, c in enumerate(self.hands[1]) if self.can_play(c)]
        if not playable:
            card = self.draw(1)
            self.turn = 0
            return {"action": "draw", "card": card}

        i, card = random.choice(playable)
        self.hands[1].pop(i)
        self.discard.append(card)
        self._effect(card, 1)

        if not self.hands[1]:
            self.over = True
            self.winner = "ai"
            return {"action": "play", "card": card, "result": "ai_win"}

        if card[1] in ("跳过", "反转"):
            self.turn = 1
            return {"action": "play", "card": card, "skip": True}

        self.turn = 0
        return {"action": "play", "card": card}

    def hand_text(self):
        return [f"{i + 1}. {c[0]} {c[1]}" for i, c in enumerate(self.hands[0])]
