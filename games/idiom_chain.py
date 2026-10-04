import random

DEFAULT_IDIOMS={
 '画龙点睛':'睛', '水落石出':'出', '出类拔萃':'萃', '春暖花开':'开', '开门见山':'山',
 '山清水秀':'秀', '秀外慧中':'中', '中流砥柱':'柱', '柱石之坚':'坚', '坚不可摧':'摧',
 '摧枯拉朽':'朽', '朽木不可雕':'雕', '雕虫小技':'技', '技高一筹':'筹', '筹谋已定':'定',
 '定国安邦':'邦', '邦家之光':'光', '光明正大':'大', '大公无私':'私', '私心杂念':'念',
}

class IdiomChain:
    name='成语接龙'
    def __init__(self, idioms=None):
        self.pool=set(idioms or DEFAULT_IDIOMS)
        self.used=[]; self.current=None; self.turn='player'; self.over=False; self.winner=None
    def start(self, first=None):
        if first is None:
            # 开局必须选择一个“最后一个字确实还能接下去”的成语，
            # 避免随机抽到“点睛”这类没有后继词的死局。
            starters = [x for x in self.pool if self._next_candidates(x)]
            if not starters:
                return {'ok':False,'reason':'当前词库没有可开始的成语'}
            first = random.choice(starters)
        if first not in self.pool:
            return {'ok':False,'reason':'这个成语不在当前词库'}
        self.used=[first]; self.current=first; self.turn='player'; return {'ok':True,'idiom':first}
    def _next_candidates(self, last):
        char=last[-1]
        return [x for x in self.pool if x not in self.used and x[0]==char]
    def player(self, idiom):
        if self.over: return {'ok':False,'reason':'游戏已经结束'}
        if self.current is None: return {'ok':False,'reason':'请先开始游戏'}
        if idiom in self.used: return {'ok':False,'reason':'这个成语已经说过了'}
        if not idiom or idiom[0]!=self.current[-1]: return {'ok':False,'reason':f'需要用“{self.current[-1]}”开头'}
        if idiom not in self.pool: return {'ok':False,'reason':'这个成语不在词库'}
        self.used.append(idiom); self.current=idiom
        candidates=self._next_candidates(idiom)
        if not candidates: self.over=True; self.winner='player'; return {'ok':True,'result':'player_win','idiom':idiom}
        ai=random.choice(candidates); self.used.append(ai); self.current=ai
        candidates=self._next_candidates(ai)
        if not candidates: self.over=True; self.winner='ai'; return {'ok':True,'result':'ai_win','ai':ai}
        return {'ok':True,'result':'continue','ai':ai,'current':ai}
    def hint(self):
        c=self._next_candidates(self.current or '')
        return random.choice(c) if c else None
