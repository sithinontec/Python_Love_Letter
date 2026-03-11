import tkinter as tk

from .constants import BG
from .game import LoveLetterGame
from .screens import SetupScreen, GameScreen


class App(tk.Tk):
    """Root application window. Manages screen transitions."""

    def __init__(self):
        super().__init__()
        self.title("Love Letter")
        self.configure(bg=BG)
        self.geometry("1060x680")
        self.minsize(900, 600)
        self.current_screen: tk.Frame | None = None
        self._show_setup()

    def _show_setup(self):
        self._swap_screen(SetupScreen(self, self._start_game))

    def _start_game(self, names):
        game = LoveLetterGame(names)
        game.start_round()
        game.draw_card(game.current_player)
        screen = GameScreen(self, game, self._show_setup)
        self._swap_screen(screen)
        screen._show_pass_screen()

    def _swap_screen(self, new_screen: tk.Frame):
        if self.current_screen:
            self.current_screen.destroy()
        new_screen.pack(fill="both", expand=True)
        self.current_screen = new_screen
