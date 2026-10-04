import random

class RussianRoulette:
    name='俄罗斯轮盘'
    def __init__(self, chambers=6):
        self.chambers=max(2,int(chambers)); self.position=random.randrange(self.chambers); self.bullet=random.randrange(self.chambers); self.turn=0; self.over=False; self.winner=None
    def player_pull(self):
        if self.over or self.turn!=0: return {'ok':False,'reason':'当前不是你的回合'}
        fired=self.position==self.bullet; self.position=(self.position+1)%self.chambers
        if fired: self.over=True; self.winner='ai'
        else: self.turn=1
        r={'ok':True,'fired':fired,'result':'lose' if fired else 'continue'}
        return r
    def ai_pull(self):
        if self.over: return {'result':self.winner}
        fired=self.position==self.bullet; self.position=(self.position+1)%self.chambers
        if fired: self.over=True; self.winner='player'
        else: self.turn=0
        return {'fired':fired,'result':'win' if fired else 'continue'}
