import random

class DealOrNoDeal:
    name='Deal or No Deal'
    VALUES=[0.01,1,5,10,25,50,75,100,200,300,400,500,750,1000,5000,10000,25000,50000,75000,100000,200000,300000,400000,500000,750000,1000000]
    ROUNDS=[6,5,4,3,2,1,1,1,1]
    DISCOUNT=[.25,.35,.45,.55,.65,.75,.85,.92,1.0]
    def __init__(self):
        self.cases=list(range(1,27)); random.shuffle(self.cases)
        self.values=dict(zip(self.cases,random.sample(self.VALUES,len(self.VALUES))))
        self.player_case=None; self.opened=set(); self.round=0; self.offer=None; self.over=False; self.result=None

    def choose_case(self, case):
        if self.player_case is not None:
            return {'ok':False,'reason':'已经选择过最终箱子'}
        try:
            case=int(case)
        except (TypeError, ValueError):
            return {'ok':False,'reason':'无效的箱子'}
        if case not in self.cases:
            return {'ok':False,'reason':'不存在的箱子'}
        self.player_case=case
        return {'ok':True,'player_case':case}

    def remaining(self): return [c for c in self.cases if c not in self.opened and c!=self.player_case]
    def _offer(self):
        vals=[self.values[c] for c in self.remaining()]+[self.values[self.player_case]]
        avg=sum(vals)/len(vals)
        return round(avg*self.DISCOUNT[min(self.round,len(self.DISCOUNT)-1)],2)
    def open(self, nums):
        if self.over:
            return {'ok':False,'reason':'游戏已经结束'}
        if self.player_case is None:
            return {'ok':False,'reason':'请先选择你的最终箱子'}
        if self.offer is not None:
            return {'ok':False,'reason':'请先回应庄家报价'}
        try:
            nums=[int(n) for n in nums]
        except (TypeError, ValueError):
            return {'ok':False,'reason':'无效的箱子'}

        needed=self.ROUNDS[min(self.round,len(self.ROUNDS)-1)]
        if len(nums) != needed:
            return {'ok':False,'reason':f'本轮需要开启 {needed} 个箱子'}
        if len(set(nums)) != len(nums):
            return {'ok':False,'reason':'不能重复选择同一个箱子'}

        bad=[n for n in nums if n not in self.remaining()]
        if bad:
            return {'ok':False,'reason':f'不能开启这些箱子: {bad}'}

        for n in nums:
            self.opened.add(n)

        opened=[(n,self.values[n]) for n in nums]

        if len(self.opened) >= 24:
            self.offer=None
            final=self._finish_preview()
            final['opened']=opened
            return final

        self.round += 1
        self.offer=self._offer()
        return {'ok':True,'opened':opened,'offer':self.offer,'remaining':self.remaining(),
                'next_open':self.ROUNDS[min(self.round,len(self.ROUNDS)-1)]}
    def _finish_preview(self):
        left=[self.player_case]+self.remaining()
        if len(left)==2:
            self.offer=self._offer()
            return {'ok':True,'endgame':True,'offer':self.offer,'remaining':left}
        return {'ok':True}
    def respond(self, deal):
        if self.offer is None: return {'ok':False,'reason':'现在没有报价'}
        if deal:
            self.over=True; self.result=self.offer; return {'ok':True,'result':'deal','value':self.offer}
        self.offer=None
        if len(self.remaining())<=1:
            return {'ok':True,'result':'final_choice','remaining':self.remaining(),'player_case':self.player_case}
        return {'ok':True,'result':'nodeal','next_open':self.ROUNDS[min(self.round,len(self.ROUNDS)-1)]}
    def swap_or_reveal(self, swap=None):
        if self.player_case is None:
            return {'ok':False,'reason':'请先选择你的最终箱子'}
        if self.player_case is None:
            return {'ok':False,'reason':'请先选择你的最终箱子'}
        left=self.remaining()
        if len(left)==1:
            other=left[0]
            if swap is True: self.player_case=other
            val=self.values[self.player_case]; self.over=True; self.result=val
            return {'ok':True,'result':'final','value':val,'player_case':self.player_case}
        return {'ok':True,'result':'continue','remaining':left}
    def status(self):
        return {'player_case_hidden':self.player_case is None,'player_case':self.player_case,'opened':len(self.opened),'remaining_count':len(self.remaining()),'offer':self.offer,'round':self.round}
