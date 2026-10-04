import random

class Gomoku:
    name = '五子棋'
    def __init__(self, size=15):
        self.size = size
        self.board = [[' ']*size for _ in range(size)]
        self.over = False
        self.winner = None

    def legal(self): return [(r,c) for r in range(self.size) for c in range(self.size) if self.board[r][c]==' ']

    def _five(self, r, c, p):
        for dr,dc in ((1,0),(0,1),(1,1),(1,-1)):
            n=1
            for s in (1,-1):
                rr,cc=r+dr*s,c+dc*s
                while 0<=rr<self.size and 0<=cc<self.size and self.board[rr][cc]==p:
                    n+=1; rr+=dr*s; cc+=dc*s
            if n>=5: return True
        return False

    def _best_ai(self):
        legal=self.legal()
        center=self.size//2
        def score(p):
            r,c=p; s=0
            s -= abs(r-center)+abs(c-center)
            for dr in (-1,0,1):
                for dc in (-1,0,1):
                    rr,cc=r+dr,c+dc
                    if 0<=rr<self.size and 0<=cc<self.size and self.board[rr][cc]=='X': s+=5
                    if 0<=rr<self.size and 0<=cc<self.size and self.board[rr][cc]=='O': s+=3
            return s
        # Win/block first.
        for p in legal:
            r,c=p; self.board[r][c]='O'
            if self._five(r,c,'O'): self.board[r][c]=' '; return p
            self.board[r][c]=' '
        for p in legal:
            r,c=p; self.board[r][c]='X'
            if self._five(r,c,'X'): self.board[r][c]=' '; return p
            self.board[r][c]=' '
        return max(legal, key=score)

    def move(self, row, col):
        if self.over: return {'ok':False,'reason':'游戏已经结束'}
        try: r,c=int(row)-1,int(col)-1
        except: return {'ok':False,'reason':'请输入行和列'}
        if not (0<=r<self.size and 0<=c<self.size) or self.board[r][c]!=' ': return {'ok':False,'reason':'这个位置不能下'}
        self.board[r][c]='X'
        if self._five(r,c,'X'):
            self.over=True; self.winner='player'; return {'ok':True,'result':'player_win','ai_move':None}
        if not self.legal(): self.over=True; return {'ok':True,'result':'draw','ai_move':None}
        ar,ac=self._best_ai(); self.board[ar][ac]='O'
        if self._five(ar,ac,'O'): self.over=True; self.winner='ai'; result='ai_win'
        elif not self.legal(): self.over=True; result='draw'
        else: result='continue'
        return {'ok':True,'result':result,'ai_move':(ar+1,ac+1)}

    def render(self):
        out=['   '+' '.join(f'{i+1:2}' for i in range(self.size))]
        for i,row in enumerate(self.board,1): out.append(f'{i:2} '+' '.join(v if v!=' ' else '·' for v in row))
        return '\n'.join(out)
