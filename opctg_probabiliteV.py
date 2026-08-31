"""
Calculateur de probabilité de pioche - One Piece Card Game
=============================================================
Calcule la probabilité de piocher au moins une copie d'une carte donnée,
en fonction du nombre de copies dans le deck (2, 3 ou 4) et du nombre
de cartes vues (main de départ, tours suivants, etc.)

Formule utilisée : loi hypergéométrique
    P(au moins 1) = 1 - C(N-K, n) / C(N, n)

    N = taille du deck (ou deck effectif si vie du leader prise en compte)
    K = nombre de copies de la carte dans le deck
    n = nombre de cartes piochées (vues)

Onglet 2 : au début d'une partie de One Piece TCG, le Leader a une vie
de 3, 4, 5 ou 6. Ce nombre de cartes est retiré du dessus du deck et mis
de côté, face cachée, comme "cartes de vie" (elles ne sont vues que si le
leader/personnage subit des dégâts). Le deck jouable/piochable pour le
reste de la partie est donc réduit d'autant : N_effectif = N - Vie.
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
    proba_aucune = comb(N - K, n) / comb(N, n)
    return (1 - proba_aucune) * 100


# ---------------------------------------------------------------------------
# Composant réutilisable : un panneau complet (inputs + table + graphique)
# ---------------------------------------------------------------------------

class ProbaPanel(ttk.Frame):
    """
    Panneau générique affichant : paramètres, tableau de résultats, graphique.
    use_life=True ajoute le champ "Vie du Leader" et retire cette valeur
    de la taille du deck avant le calcul (deck effectif).
    """

    def __init__(self, master, use_life: bool = False):
        super().__init__(master)
        self.use_life = use_life

        self._build_inputs()
        self._build_table()
        self._build_chart()
        self.calculer()

    # -------------------------------------------------------------- inputs
    def _build_inputs(self):
        frame = ttk.LabelFrame(self, text="Paramètres du deck")
        frame.pack(fill="x", padx=10, pady=10)

        row = 0

        # Taille du deck
        ttk.Label(frame, text="Taille du deck :").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        self.deck_size_var = tk.IntVar(value=50)
        ttk.Entry(frame, textvariable=self.deck_size_var, width=8).grid(row=row, column=1, padx=5, pady=5)

        # Main de départ
        ttk.Label(frame, text="Main de départ :").grid(row=row, column=2, padx=5, pady=5, sticky="w")
        self.starting_hand_var = tk.IntVar(value=5)
        ttk.Entry(frame, textvariable=self.starting_hand_var, width=8).grid(row=row, column=3, padx=5, pady=5)

        if self.use_life:
            row += 1
            ttk.Label(frame, text="Vie du Leader :").grid(row=row, column=0, padx=5, pady=5, sticky="w")
            self.life_var = tk.IntVar(value=5)
            life_frame = ttk.Frame(frame)
            life_frame.grid(row=row, column=1, columnspan=3, sticky="w")
            for i, v in enumerate([3, 4, 5, 6]):
                ttk.Radiobutton(life_frame, text=f"{v} vies", value=v, variable=self.life_var,
                                command=self.calculer).grid(row=0, column=i, padx=8)

            row += 1
            self.deck_effectif_label = ttk.Label(frame, text="", foreground="#0a6b2d", font=("TkDefaultFont", 9, "bold"))
            self.deck_effectif_label.grid(row=row, column=0, columnspan=4, padx=5, pady=(0, 5), sticky="w")

        # Nombre de copies à comparer (checkboxes)
        row += 1
        ttk.Label(frame, text="Copies dans le deck à comparer :").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        self.copies_vars = {}
        copies_frame = ttk.Frame(frame)
        copies_frame.grid(row=row, column=1, columnspan=3, sticky="w")
        for i, k in enumerate([1, 2, 3, 4]):
            var = tk.BooleanVar(value=(k in (2, 3, 4)))
            self.copies_vars[k] = var
            ttk.Checkbutton(copies_frame, text=f"{k}x", variable=var).grid(row=0, column=i, padx=8)

        # Points de pioche (cartes vues) à afficher dans le tableau
        row += 1
        ttk.Label(frame, text="Cartes vues (séparées par des virgules) :").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        self.draw_points_var = tk.StringVar(value="5,6,7,10,15,20")
        ttk.Entry(frame, textvariable=self.draw_points_var, width=30).grid(row=row, column=1, columnspan=2, padx=5, pady=5, sticky="w")

        ttk.Button(frame, text="Calculer", command=self.calculer).grid(row=row, column=3, padx=5, pady=5)

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

        self.figure = Figure(figsize=(7, 3.8), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    # -------------------------------------------------------------- logic
    def calculer(self):
        try:
            N_deck = self.deck_size_var.get()

            # Deck effectif = deck total - vie du leader (cartes cachées, non piochables)
            if self.use_life:
                life = self.life_var.get()
                N = N_deck - life
                if N <= 0:
                    messagebox.showerror("Erreur", "La vie du leader ne peut pas dépasser/égaler la taille du deck.")
                    return
                self.deck_effectif_label.config(
                    text=f"→ Deck effectif (piochable) : {N_deck} - {life} (cartes de vie) = {N} cartes"
                )
            else:
                N = N_deck

            draw_points = [int(x.strip()) for x in self.draw_points_var.get().split(",") if x.strip()]
            copies_selected = [k for k, v in self.copies_vars.items() if v.get()]

            if not copies_selected:
                messagebox.showwarning("Attention", "Sélectionne au moins un nombre de copies (1x, 2x, 3x ou 4x).")
                return
            if not draw_points:
                messagebox.showwarning("Attention", "Indique au moins un nombre de cartes vues.")
                return
            if max(draw_points) > N:
                messagebox.showerror("Erreur", "Le nombre de cartes vues ne peut pas dépasser la taille du deck effectif.")
                return

            results = {}
            for K in copies_selected:
                results[K] = [proba_au_moins_une(N, K, n) for n in draw_points]

            self._update_table(draw_points, results)
            self._update_chart(N, N_deck, draw_points, results)

        except ValueError:
            messagebox.showerror("Erreur", "Vérifie que les champs numériques sont valides (entiers).")

    def _update_table(self, draw_points, results):
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

    def _update_chart(self, N, N_deck, draw_points, results):
        self.ax.clear()
        for k, probs in results.items():
            self.ax.plot(draw_points, probs, marker="o", label=f"{k} copies dans le deck")

        title = f"Probabilité de piocher au moins 1 copie (deck effectif de {N} cartes)" \
            if self.use_life else f"Probabilité de piocher au moins 1 copie (deck de {N} cartes)"
        self.ax.set_title(title, fontsize=10)
        self.ax.set_xlabel("Nombre de cartes vues")
        self.ax.set_ylabel("Probabilité (%)")
        self.ax.set_ylim(0, 100)
        self.ax.grid(True, linestyle="--", alpha=0.5)
        self.ax.legend()
        self.canvas.draw()


# ---------------------------------------------------------------------------
# Fenêtre principale avec onglets
# ---------------------------------------------------------------------------

class OPCGApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("One Piece TCG - Calculateur de probabilité de pioche")
        self.geometry("900x760")
        self.configure(bg="#f4f4f4")
        self.resizable(True, True)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)

        tab_standard = ProbaPanel(notebook, use_life=False)
        tab_life = ProbaPanel(notebook, use_life=True)

        notebook.add(tab_standard, text="Standard")
        notebook.add(tab_life, text="Avec vie du Leader")


if __name__ == "__main__":
    app = OPCGApp()
    app.mainloop()
