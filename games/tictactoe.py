import random

class TicTacToe:
    name = '井字棋'
    def __init__(self, ai_level='normal'):
        self.board = [' '] * 9
        self.player = 'X'
        self.ai = 'O'
        self.ai_level = ai_level
        self.over = False
        self.winner = None

    def render(self):
        b = self.board
        return '\n'.join(' | '.join(b[i:i+3][j] or '·' for j in range(3)) for i in range(0, 9, 3))

    def legal(self): return [i for i, v in enumerate(self.board) if v == ' ']

    def _win(self, p):
        return any(all(self.board[i] == p for i in line) for line in ((0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)))

    def move(self, pos):
        if self.over: return {'ok': False, 'reason': '游戏已经结束'}
        try: pos = int(pos) - 1
        except: return {'ok': False, 'reason': '位置必须是 1-9'}
        if pos not in self.legal(): return {'ok': False, 'reason': '这个位置不能下'}
        self.board[pos] = self.player
        if self._win(self.player):
            self.over, self.winner = True, 'player'
            return {'ok': True, 'result': 'player_win', 'board': self.render()}
        if not self.legal():
            self.over = True
            return {'ok': True, 'result': 'draw', 'board': self.render()}
        ai_pos = self.ai_move()
        if self._win(self.ai):
            self.over, self.winner = True, 'ai'
            result = 'ai_win'
        elif not self.legal():
            self.over, result = True, 'draw'
        else:
            result = 'continue'
        return {'ok': True, 'result': result, 'ai_move': ai_pos + 1, 'board': self.render()}

    def ai_move(self):
        legal = self.legal()
        if self.ai_level == 'easy':
            p = random.choice(legal)
            self.board[p] = self.ai
            return p
        # Win, block, center, corner, random.
        for p in legal:
            self.board[p] = self.ai
            if self._win(self.ai): return p
            self.board[p] = ' '
        for p in legal:
            self.board[p] = self.player
            if self._win(self.player):
                self.board[p] = self.ai
                return p
            self.board[p] = ' '
        if 4 in legal: self.board[4] = self.ai; return 4
        corners = [p for p in (0,2,6,8) if p in legal]
        if corners:
            p = random.choice(corners); self.board[p] = self.ai; return p
        p = random.choice(legal); self.board[p] = self.ai; return p
