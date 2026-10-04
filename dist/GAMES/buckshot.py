import random

class Buckshot:
    name='Buckshot Roulette'
    def __init__(self, hp=3, shells=6):
        self.hp=[hp,hp]; self.max_hp=hp; self.shells=[]; self.turn=0; self.over=False; self.winner=None
        self.shell_count = max(2, int(shells))
        self._reload()
    def _reload(self):
        live=max(1,min(self.shell_count-1, self.shell_count//2))
        self.shells=[True]*live+[False]*(self.shell_count-live)
        random.shuffle(self.shells)

    def status(self): return {'player_hp':self.hp[0],'pet_hp':self.hp[1],'shells':len(self.shells),'turn':'player' if self.turn==0 else 'pet'}
    def _shot(self, shooter,target, live):
        # 弹仓打空后自动重新装填，避免空弹仓导致游戏崩溃。
        if not self.shells:
            self._reload()
        shell=self.shells.pop(0)
        if shell: self.hp[target]-=1
        # blank returns turn to shooter; live passes turn.
        if self.hp[target]<=0: self.over=True; self.winner=shooter
        elif not shell: self.turn=shooter
        else: self.turn=target
        return shell
    def player_action(self, target='pet'):
        if self.over: return {'ok':False,'reason':'游戏已经结束'}
        if self.turn!=0: return {'ok':False,'reason':'现在是桌宠回合'}
        live=self._shot(0,1,target=='pet')
        result={'ok':True,'live':live,'status':self.status()}
        if self.over: result['result']='player_win'; return result
        return result
    def ai_action(self):
        if self.over: return {'result':self.winner}
        # Simple AI: usually shoot player; occasionally choose self when HP is low.
        target=1 if self.hp[1]<=1 and random.random()<.25 else 0
        live=self._shot(1,target,True)
        r={'live':live,'target':'self' if target==1 else 'player','status':self.status()}
        if self.over: r['result']='ai_win'
        return r
