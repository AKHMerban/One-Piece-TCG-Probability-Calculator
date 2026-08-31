"""
Calculateur de probabilité de pioche - One Piece Card Game
=============================================================
Calcule la probabilité de piocher au moins une copie d'une carte donnée,
en fonction du nombre de copies dans le deck (2, 3 ou 4) et du nombre
de cartes vues (main de départ, tours suivants, etc.)

Formule utilisée : loi hypergéométrique
    P(au moins 1) = 1 - C(N-K, n) / C(N, n)

    N = taille du deck
    K = nombre de copies de la carte dans le deck
    n = nombre de cartes piochées (vues)
"""

import tkinter as tk
from tkinter import ttk, messagebox
from math import comb

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


# ---------------------------------------------------------------------------
# Logique de calcul (loi hypergéométrique)
# ---------------------------------------------------------------------------

def proba_au_moins_une(N: int, K: int, n: int) -> float:
    """
    Retourne la probabilité (en %) de piocher au moins une copie
    d'une carte présente K fois dans un deck de taille N, en piochant n cartes.
    """
    if n > N or K > N or n < 0 or K < 0:
        raise ValueError("Paramètres invalides")
    if n == 0:
        return 0.0
    # Probabilité de ne piocher AUCUNE copie de la carte
    proba_aucune = comb(N - K, n) / comb(N, n)
    return (1 - proba_aucune) * 100


# ---------------------------------------------------------------------------
# Interface graphique
# ---------------------------------------------------------------------------

class OPCGApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("One Piece TCG - Calculateur de probabilité de pioche")
        self.geometry("880x680")
        self.configure(bg="#f4f4f4")
        self.resizable(True, True)

        self._build_inputs()
        self._build_table()
        self._build_chart()

        # Calcul initial avec valeurs par défaut
        self.calculer()

    # -------------------------------------------------------------- inputs
    def _build_inputs(self):
        frame = ttk.LabelFrame(self, text="Paramètres du deck")
        frame.pack(fill="x", padx=10, pady=10)

        # Taille du deck
        ttk.Label(frame, text="Taille du deck :").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.deck_size_var = tk.IntVar(value=50)
        ttk.Entry(frame, textvariable=self.deck_size_var, width=8).grid(row=0, column=1, padx=5, pady=5)

        # Main de départ
        ttk.Label(frame, text="Main de départ :").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.starting_hand_var = tk.IntVar(value=5)
        ttk.Entry(frame, textvariable=self.starting_hand_var, width=8).grid(row=0, column=3, padx=5, pady=5)

        # Nombre de copies à comparer (checkboxes)
        ttk.Label(frame, text="Copies dans le deck à comparer :").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.copies_vars = {}
        copies_frame = ttk.Frame(frame)
        copies_frame.grid(row=1, column=1, columnspan=3, sticky="w")
        for i, k in enumerate([1, 2, 3, 4]):
            var = tk.BooleanVar(value=(k in (2, 3, 4)))
            self.copies_vars[k] = var
            ttk.Checkbutton(copies_frame, text=f"{k}x", variable=var).grid(row=0, column=i, padx=8)

        # Points de pioche (cartes vues) à afficher dans le tableau
        ttk.Label(frame, text="Cartes vues (séparées par des virgules) :").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.draw_points_var = tk.StringVar(value="5,6,7,10,15,20")
        ttk.Entry(frame, textvariable=self.draw_points_var, width=30).grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="w")

        ttk.Button(frame, text="Calculer", command=self.calculer).grid(row=2, column=3, padx=5, pady=5)

    # -------------------------------------------------------------- table
    def _build_table(self):
        frame = ttk.LabelFrame(self, text="Résultats (% de chance d'avoir piochÉ au moins 1 copie)")
        frame.pack(fill="both", expand=False, padx=10, pady=5)

        self.tree = ttk.Treeview(frame, show="headings", height=6)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

    # -------------------------------------------------------------- chart
    def _build_chart(self):
        frame = ttk.LabelFrame(self, text="Graphique")
        frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.figure = Figure(figsize=(7, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    # -------------------------------------------------------------- logic
    def calculer(self):
        try:
            N = self.deck_size_var.get()
            draw_points = [int(x.strip()) for x in self.draw_points_var.get().split(",") if x.strip()]
            copies_selected = [k for k, v in self.copies_vars.items() if v.get()]

            if not copies_selected:
                messagebox.showwarning("Attention", "Sélectionne au moins un nombre de copies (1x, 2x, 3x ou 4x).")
                return
            if not draw_points:
                messagebox.showwarning("Attention", "Indique au moins un nombre de cartes vues.")
                return
            if max(draw_points) > N:
                messagebox.showerror("Erreur", "Le nombre de cartes vues ne peut pas dépasser la taille du deck.")
                return

            results = {}  # {K: [proba1, proba2, ...]}
            for K in copies_selected:
                results[K] = [proba_au_moins_une(N, K, n) for n in draw_points]

            self._update_table(draw_points, results)
            self._update_chart(N, draw_points, results)

        except ValueError:
            messagebox.showerror("Erreur", "Vérifie que les champs numériques sont valides (entiers).")

    def _update_table(self, draw_points, results):
        # Reset colonnes
        columns = ["cartes_vues"] + [f"{k}x_copies" for k in results]
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = columns

        self.tree.heading("cartes_vues", text="Cartes vues")
        self.tree.column("cartes_vues", width=100, anchor="center")
        for k in results:
            self.tree.heading(f"{k}x_copies", text=f"{k}x dans le deck")
            self.tree.column(f"{k}x_copies", width=130, anchor="center")

        for i, n in enumerate(draw_points):
            row = [n] + [f"{results[k][i]:.1f}%" for k in results]
            self.tree.insert("", "end", values=row)

    def _update_chart(self, N, draw_points, results):
        self.ax.clear()
        for k, probs in results.items():
            self.ax.plot(draw_points, probs, marker="o", label=f"{k} copies dans le deck")

        self.ax.set_title(f"Probabilité de piocher au moins 1 copie (deck de {N} cartes)")
        self.ax.set_xlabel("Nombre de cartes vues")
        self.ax.set_ylabel("Probabilité (%)")
        self.ax.set_ylim(0, 100)
        self.ax.grid(True, linestyle="--", alpha=0.5)
        self.ax.legend()
        self.canvas.draw()


if __name__ == "__main__":
    app = OPCGApp()
    app.mainloop()