from .tictactoe import TicTacToe
from .gomoku import Gomoku
from .idiom_chain import IdiomChain
from .uno import Uno
from .deal_or_no_deal import DealOrNoDeal
from .buckshot import Buckshot
from .russian_roulette import RussianRoulette
from .farmland import FarmGame

GAMES={
 'tictactoe':TicTacToe,
 'gomoku':Gomoku,
 'idiom':IdiomChain,
 'uno':Uno,
 'deal':DealOrNoDeal,
 'buckshot':Buckshot,
 'roulette':RussianRoulette,
 'farmland':FarmGame,
}

class GameManager:
    """桌宠小游戏统一入口。所有对局均默认为玩家 vs 桌宠，互不共享状态。"""
    def __init__(self): self.current=None
    def start(self, game_id, **kwargs):
        if game_id not in GAMES: raise ValueError(f'未知游戏: {game_id}')
        self.current=GAMES[game_id](**kwargs); return self.current
    def stop(self): self.current=None
