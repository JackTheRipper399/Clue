import tkinter as tk
from ui.app import ClueApp
from logic.game_engine import GameEngine


def main():
    root = tk.Tk()
    root.title("Clue: Python Edition")
    # adjust AI count as you like
    engine = GameEngine(human_name="You", ai_count=2)
    app = ClueApp(root, engine)
    app.pack(fill="both", expand=True)
    root.minsize(1000, 650)
    root.mainloop()


if __name__ == "__main__":
    main()
