SPT DeskPet + Games

Files:
- index.py: SPT DeskPet with integrated Games panel/menu/tray entry.
- games/: local game rules package.

Integrated games:
1. 井字棋 / Tic-Tac-Toe
2. 五子棋 / Gomoku
3. 成语接龙 / Idiom Chain
4. UNO
5. 一掷千金 / Deal or No Deal
6. Buckshot Roulette
7. 俄罗斯轮盘 / Russian Roulette

The games package is imported by index.py. When building with PyInstaller,
the imported Python package should be collected automatically by Analysis.
