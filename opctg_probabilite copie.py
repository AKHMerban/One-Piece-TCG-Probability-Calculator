"""
Calculateur de probabilite de pioche - One Piece Card Game
=============================================================
Onglets :
  1. Standard              - calcul hypergeometrique de base (saisie libre)
  2. Vie du Leader          - deck effectif = deck - vie du leader (3/4/5/6)
                              + position 1er/2e joueur + axe X (cartes/tour)
  3. Cout DON!!             - tour ideal pour jouer une carte selon son cout
  4. Effets supplementaires - recherche (top 3/5) et pioche X/defausse X,
                              cumulables, ajoutes aux cartes vues
  5. Combinaisons           - probabilite de piocher une combinaison de
                              jusqu'a 5 cartes (avec un nombre minimum de
                              copies requis pour chacune, ex: 2x la meme
                              carte + 1x une autre)

Formule de base : loi hypergeometrique
    P(au moins 1) = 1 - C(N-K, n) / C(N, n)
    N = taille du deck (effectif), K = copies de la carte, n = cartes vues

Pour les combinaisons (plusieurs cartes, avec minimum requis par carte),
on utilise la loi hypergeometrique multivariee, calculee par sommation
directe sur toutes les repartitions possibles (nombre de cartes limite
donc calcul rapide).
"""

import tkinter as tk
from tkinter import ttk, messagebox
from math import comb
from itertools import product

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


# ---------------------------------------------------------------------------
# Logique de calcul
# ---------------------------------------------------------------------------

def proba_au_moins_une(N: int, K: int, n: int) -> float:
    """% de chance d'avoir au moins 1 copie d'une carte (K copies dans un
    deck de N cartes) parmi n cartes vues."""
    if n > N or K > N or n < 0 or K < 0:
        raise ValueError("Parametres invalides")
    if n == 0 or K == 0:
        return 0.0
    proba_aucune = comb(N - K, n) / comb(N, n)
    return (1 - proba_aucune) * 100


def proba_combo(N: int, cartes, n: int) -> float:
    """
    Probabilite (%) d'avoir simultanement, parmi n cartes vues, au moins
    r_i copies de chaque carte i (K_i copies dans le deck).

    cartes : liste de tuples (K_i, r_i) - copies dans le deck, minimum requis.
    """
    total_K = sum(k for k, r in cartes)
    if total_K > N or n > N or n < 0:
        raise ValueError("Parametres invalides")
    autres = N - total_K
    denom = comb(N, n)
    if denom == 0:
        return 0.0

    ranges = [range(r, k + 1) for k, r in cartes]
    total = 0
    for combo_a in product(*ranges):
        tires_succes = sum(combo_a)
        reste = n - tires_succes
        if reste < 0 or reste > autres:
            continue
        ways = comb(autres, reste)
        if ways == 0:
            continue
        for (k, r), a in zip(cartes, combo_a):
            ways *= comb(k, a)
            if ways == 0:
                break
        total += ways

    return (total / denom) * 100


# ---------------------------------------------------------------------------
# Helpers UI reutilisables
# ---------------------------------------------------------------------------

def build_position_and_drawpoints_block(parent, row, starting_hand_var, calc_callback):
    """
    Cree le bloc 'Position' (saisie manuelle / 1er joueur / 2e joueur) qui
    remplit automatiquement le champ 'cartes vues' selon la regle OPTCG :
    le 1er joueur ne pioche pas au tour 1, le 2e joueur pioche des le tour 1.

    Retourne un dict avec les variables/widgets crees et la ligne suivante.
    """
    ttk.Label(parent, text="Position :").grid(row=row, column=0, padx=5, pady=5, sticky="w")
    position_var = tk.StringVar(value="manuel")
    pos_frame = ttk.Frame(parent)
    pos_frame.grid(row=row, column=1, columnspan=3, sticky="w")

    row += 1
    draw_points_label = ttk.Label(parent, text="Cartes vues (separees par des virgules) :")
    draw_points_label.grid(row=row, column=0, padx=5, pady=5, sticky="w")
    draw_points_var = tk.StringVar(value="5,6,7,10,15,20")
    draw_points_entry = ttk.Entry(parent, textvariable=draw_points_var, width=32)
    draw_points_entry.grid(row=row, column=1, columnspan=2, padx=5, pady=5, sticky="w")

    def on_change():
        pos = position_var.get()
        if pos == "manuel":
            draw_points_entry.config(state="normal")
            draw_points_label.config(text="Cartes vues (separees par des virgules) :")
        else:
            hand = starting_hand_var.get()
            values = []
            for turn in range(1, 11):
                seen = hand + (max(0, turn - 1) if pos == "p1" else turn)
                values.append(seen)
            draw_points_var.set(",".join(str(v) for v in values))
            draw_points_label.config(text="Cartes vues par tour (1 a 10, calcule auto) :")
            draw_points_entry.config(state="disabled")
        calc_callback()

    ttk.Radiobutton(pos_frame, text="Saisie manuelle", value="manuel",
                     variable=position_var, command=on_change).grid(row=0, column=0, padx=4, sticky="w")
    ttk.Radiobutton(pos_frame, text="1er joueur (pas de pioche T1)", value="p1",
                     variable=position_var, command=on_change).grid(row=0, column=1, padx=4, sticky="w")
    ttk.Radiobutton(pos_frame, text="2e joueur (pioche des T1)", value="p2",
                     variable=position_var, command=on_change).grid(row=0, column=2, padx=4, sticky="w")

    return {
        "position_var": position_var,
        "draw_points_var": draw_points_var,
        "draw_points_entry": draw_points_entry,
        "draw_points_label": draw_points_label,
        "next_row": row + 1,
    }


def build_xaxis_toggle(parent, row, calc_callback):
    ttk.Label(parent, text="Axe X du graphique :").grid(row=row, column=0, padx=5, pady=5, sticky="w")
    xaxis_var = tk.StringVar(value="cartes")
    xframe = ttk.Frame(parent)
    xframe.grid(row=row, column=1, columnspan=3, sticky="w")
    ttk.Radiobutton(xframe, text="Cartes vues", value="cartes",
                     variable=xaxis_var, command=calc_callback).grid(row=0, column=0, padx=6, sticky="w")
    ttk.Radiobutton(xframe, text="Tour (si position choisie)", value="tour",
                     variable=xaxis_var, command=calc_callback).grid(row=0, column=1, padx=6, sticky="w")
    return xaxis_var, row + 1


def parse_draw_points(text):
    return [int(x.strip()) for x in text.split(",") if x.strip()]


# ---------------------------------------------------------------------------
# Onglet 1 & 2 : Standard / Vie du Leader
# ---------------------------------------------------------------------------

class ProbaPanel(ttk.Frame):
    def __init__(self, master, use_life: bool = False):
        super().__init__(master)
        self.use_life = use_life
        self.turns_for_points = None
        self._build_inputs()
        self._build_table()
        self._build_chart()
        self.calculer()

    def _build_inputs(self):
        frame = ttk.LabelFrame(self, text="Parametres du deck")
        frame.pack(fill="x", padx=10, pady=10)
        row = 0

        ttk.Label(frame, text="Taille du deck :").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        self.deck_size_var = tk.IntVar(value=50)
        ttk.Entry(frame, textvariable=self.deck_size_var, width=8).grid(row=row, column=1, padx=5, pady=5)

        ttk.Label(frame, text="Main de depart :").grid(row=row, column=2, padx=5, pady=5, sticky="w")
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
            block = build_position_and_drawpoints_block(frame, row, self.starting_hand_var, self.calculer)
            self.position_var = block["position_var"]
            self.draw_points_var = block["draw_points_var"]
            self.draw_points_entry = block["draw_points_entry"]
            self.draw_points_label = block["draw_points_label"]
            row = block["next_row"]

            self.xaxis_var, row = build_xaxis_toggle(frame, row, self.calculer)

            self.deck_effectif_label = ttk.Label(frame, text="", foreground="#0a6b2d", font=("TkDefaultFont", 9, "bold"))
            self.deck_effectif_label.grid(row=row, column=0, columnspan=4, padx=5, pady=(0, 5), sticky="w")
            row += 1
        else:
            row += 1
            ttk.Label(frame, text="Cartes vues (separees par des virgules) :").grid(row=row, column=0, padx=5, pady=5, sticky="w")
            self.draw_points_var = tk.StringVar(value="5,6,7,10,15,20")
            ttk.Entry(frame, textvariable=self.draw_points_var, width=32).grid(row=row, column=1, columnspan=2, padx=5, pady=5, sticky="w")
            row += 1

        ttk.Label(frame, text="Copies dans le deck a comparer :").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        self.copies_vars = {}
        copies_frame = ttk.Frame(frame)
        copies_frame.grid(row=row, column=1, columnspan=3, sticky="w")
        for i, k in enumerate([1, 2, 3, 4]):
            var = tk.BooleanVar(value=(k in (2, 3, 4)))
            self.copies_vars[k] = var
            ttk.Checkbutton(copies_frame, text=f"{k}x", variable=var).grid(row=0, column=i, padx=8)

        row += 1
        ttk.Button(frame, text="Calculer", command=self.calculer).grid(row=row, column=3, padx=5, pady=8, sticky="e")

    def _build_table(self):
        frame = ttk.LabelFrame(self, text="Resultats (% de chance d'avoir piochE au moins 1 copie)")
        frame.pack(fill="both", expand=False, padx=10, pady=5)
        self.tree = ttk.Treeview(frame, show="headings", height=6)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

    def _build_chart(self):
        frame = ttk.LabelFrame(self, text="Graphique")
        frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.figure = Figure(figsize=(7, 3.6), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    def calculer(self):
        try:
            N_deck = self.deck_size_var.get()

            if self.use_life:
                life = self.life_var.get()
                N = N_deck - life
                if N <= 0:
                    messagebox.showerror("Erreur", "La vie du leader ne peut pas depasser/egaler la taille du deck.")
                    return
                self.deck_effectif_label.config(
                    text=f"-> Deck effectif (piochable) : {N_deck} - {life} (cartes de vie) = {N} cartes"
                )
                position = self.position_var.get()
            else:
                N = N_deck
                position = "manuel"

            draw_points = parse_draw_points(self.draw_points_var.get())
            copies_selected = [k for k, v in self.copies_vars.items() if v.get()]

            if not copies_selected:
                messagebox.showwarning("Attention", "Selectionne au moins un nombre de copies (1x, 2x, 3x ou 4x).")
                return
            if not draw_points:
                messagebox.showwarning("Attention", "Indique au moins un nombre de cartes vues.")
                return
            if max(draw_points) > N:
                messagebox.showerror("Erreur", "Le nombre de cartes vues ne peut pas depasser la taille du deck effectif.")
                return

            self.turns_for_points = list(range(1, len(draw_points) + 1)) if position in ("p1", "p2") else None

            results = {K: [proba_au_moins_une(N, K, n) for n in draw_points] for K in copies_selected}

            self._update_table(draw_points, results)
            self._update_chart(N, draw_points, results)

        except ValueError:
            messagebox.showerror("Erreur", "Verifie que les champs numeriques sont valides (entiers).")

    def _update_table(self, draw_points, results):
        show_turn = self.use_life and self.turns_for_points is not None
        columns = (["tour"] if show_turn else []) + ["cartes_vues"] + [f"{k}x_copies" for k in results]
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = columns

        if show_turn:
            self.tree.heading("tour", text="Tour")
            self.tree.column("tour", width=60, anchor="center")
        self.tree.heading("cartes_vues", text="Cartes vues")
        self.tree.column("cartes_vues", width=100, anchor="center")
        for k in results:
            self.tree.heading(f"{k}x_copies", text=f"{k}x dans le deck")
            self.tree.column(f"{k}x_copies", width=130, anchor="center")

        for i, n in enumerate(draw_points):
            row = ([self.turns_for_points[i]] if show_turn else []) + [n] + [f"{results[k][i]:.1f}%" for k in results]
            self.tree.insert("", "end", values=row)

    def _update_chart(self, N, draw_points, results):
        self.ax.clear()
        use_turn_axis = self.use_life and self.xaxis_var.get() == "tour" and self.turns_for_points is not None
        x_values = self.turns_for_points if use_turn_axis else draw_points

        for k, probs in results.items():
            self.ax.plot(x_values, probs, marker="o", label=f"{k} copies dans le deck")

        title = f"Probabilite de piocher au moins 1 copie (deck effectif de {N} cartes)" \
            if self.use_life else f"Probabilite de piocher au moins 1 copie (deck de {N} cartes)"
        self.ax.set_title(title, fontsize=10)
        self.ax.set_xlabel("Tour" if use_turn_axis else "Nombre de cartes vues")
        self.ax.set_ylabel("Probabilite (%)")
        self.ax.set_ylim(0, 100)
        self.ax.grid(True, linestyle="--", alpha=0.5)
        self.ax.legend()
        self.canvas.draw()


# ---------------------------------------------------------------------------
# Onglet 3 : Moment ideal pour jouer une carte selon son cout en DON!!
# ---------------------------------------------------------------------------

class DonPanel(ttk.Frame):
    MAX_TURN = 10

    def __init__(self, master):
        super().__init__(master)
        self._build_inputs()
        self._build_table()
        self._build_chart()
        self.calculer()

    def _build_inputs(self):
        frame = ttk.LabelFrame(self, text="Parametres")
        frame.pack(fill="x", padx=10, pady=10)

        row = 0
        ttk.Label(frame, text="Taille du deck :").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        self.deck_size_var = tk.IntVar(value=50)
        ttk.Entry(frame, textvariable=self.deck_size_var, width=8).grid(row=row, column=1, padx=5, pady=5)

        ttk.Label(frame, text="Vie du Leader :").grid(row=row, column=2, padx=5, pady=5, sticky="w")
        self.life_var = tk.IntVar(value=5)
        life_frame = ttk.Frame(frame)
        life_frame.grid(row=row, column=3, sticky="w")
        for i, v in enumerate([3, 4, 5, 6]):
            ttk.Radiobutton(life_frame, text=str(v), value=v, variable=self.life_var,
                             command=self.calculer).grid(row=0, column=i, padx=3)

        row += 1
        ttk.Label(frame, text="Position :").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        self.position_var = tk.StringVar(value="p1")
        pos_frame = ttk.Frame(frame)
        pos_frame.grid(row=row, column=1, columnspan=3, sticky="w")
        ttk.Radiobutton(pos_frame, text="1er joueur (pas de pioche T1)", value="p1",
                         variable=self.position_var, command=self.calculer).grid(row=0, column=0, padx=4, sticky="w")
        ttk.Radiobutton(pos_frame, text="2e joueur (pioche des T1)", value="p2",
                         variable=self.position_var, command=self.calculer).grid(row=0, column=1, padx=4, sticky="w")

        row += 1
        ttk.Label(frame, text="Copies de la carte dans le deck :").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        self.copies_var = tk.IntVar(value=4)
        copies_frame = ttk.Frame(frame)
        copies_frame.grid(row=row, column=1, columnspan=3, sticky="w")
        for i, k in enumerate([1, 2, 3, 4]):
            ttk.Radiobutton(copies_frame, text=f"{k}x", value=k, variable=self.copies_var,
                             command=self.calculer).grid(row=0, column=i, padx=8)

        row += 1
        ttk.Label(frame, text="Cout en DON!! de la carte :").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        self.cost_var = tk.IntVar(value=4)
        ttk.Spinbox(frame, from_=0, to=10, textvariable=self.cost_var, width=6,
                    command=self.calculer).grid(row=row, column=1, padx=5, pady=5, sticky="w")

        row += 1
        self.reserve_check_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Garder du DON!! en reserve pour autre chose (ex : contre, effet actif) :",
                        variable=self.reserve_check_var, command=self.calculer).grid(
            row=row, column=0, columnspan=2, padx=5, pady=5, sticky="w")
        self.reserve_var = tk.IntVar(value=1)
        ttk.Spinbox(frame, from_=0, to=9, textvariable=self.reserve_var, width=6,
                    command=self.calculer).grid(row=row, column=2, padx=5, pady=5, sticky="w")

        row += 1
        ttk.Button(frame, text="Calculer", command=self.calculer).grid(row=row, column=0, padx=5, pady=8, sticky="w")

        row += 1
        self.result_label = ttk.Label(frame, text="", foreground="#0a4d8c", font=("TkDefaultFont", 10, "bold"),
                                       wraplength=820, justify="left")
        self.result_label.grid(row=row, column=0, columnspan=4, padx=5, pady=(0, 8), sticky="w")

        row += 1
        note = ttk.Label(
            frame,
            text=("Hypothese : DON!! disponible au tour N = min(N, 10) (1 de plus par tour, plafond 10).\n"
                  "Ce calcul ignore volontairement le jeu adverse (blocage, KO, effets) - c'est le tour "
                  "'ideal dans l'absolu', a ajuster selon la partie reelle."),
            font=("TkDefaultFont", 8), foreground="#666666", justify="left", wraplength=820,
        )
        note.grid(row=row, column=0, columnspan=4, padx=5, pady=(0, 5), sticky="w")

    def _build_table(self):
        frame = ttk.LabelFrame(self, text="Detail tour par tour")
        frame.pack(fill="both", expand=False, padx=10, pady=5)
        self.tree = ttk.Treeview(
            frame, show="headings", height=8,
            columns=("tour", "don", "cartes_vues", "proba", "jouable")
        )
        for col, label, width in [
            ("tour", "Tour", 60),
            ("don", "DON!! dispo", 100),
            ("cartes_vues", "Cartes vues", 100),
            ("proba", "Proba d'avoir la carte en main", 220),
            ("jouable", "Jouable ce tour ?", 140),
        ]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

    def _build_chart(self):
        frame = ttk.LabelFrame(self, text="Graphique")
        frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.figure = Figure(figsize=(7, 3.4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    def calculer(self):
        try:
            N_deck = self.deck_size_var.get()
            life = self.life_var.get()
            N = N_deck - life
            if N <= 0:
                messagebox.showerror("Erreur", "La vie du leader ne peut pas depasser/egaler la taille du deck.")
                return

            K = self.copies_var.get()
            cost = self.cost_var.get()
            reserve = self.reserve_var.get() if self.reserve_check_var.get() else 0
            position = self.position_var.get()
            hand = 5

            turns = list(range(1, self.MAX_TURN + 1))
            don_dispo = [min(t, 10) for t in turns]
            cartes_vues = [min(hand + (max(0, t - 1) if position == "p1" else t), N) for t in turns]
            probas = [proba_au_moins_une(N, K, n) for n in cartes_vues]
            seuil = cost + reserve
            jouable = [d >= seuil for d in don_dispo]
            tour_ideal = next((t for t, ok in zip(turns, jouable) if ok), None)

            self._update_table(turns, don_dispo, cartes_vues, probas, jouable)
            self._update_chart(turns, don_dispo, probas, tour_ideal, seuil)

            if tour_ideal:
                proba_a_ce_tour = probas[tour_ideal - 1]
                extra = f" (en gardant {reserve} DON!! de reserve)" if reserve else ""
                self.result_label.config(
                    text=(f"-> Tour ideal pour jouer cette carte a {cost} DON!!{extra} : Tour {tour_ideal} "
                          f"(vous auriez alors {don_dispo[tour_ideal-1]} DON!! disponibles). "
                          f"A ce tour-la, probabilite de l'avoir deja piochee : {proba_a_ce_tour:.1f}%.")
                )
            else:
                self.result_label.config(
                    text=f"-> Avec un cout de {cost} + {reserve} de reserve = {seuil} DON!!, "
                         f"ce n'est jouable a aucun tour dans les {self.MAX_TURN} premiers tours."
                )

        except ValueError:
            messagebox.showerror("Erreur", "Verifie que les champs numeriques sont valides (entiers).")

    def _update_table(self, turns, don_dispo, cartes_vues, probas, jouable):
        self.tree.delete(*self.tree.get_children())
        for t, d, c, p, j in zip(turns, don_dispo, cartes_vues, probas, jouable):
            self.tree.insert("", "end", values=(t, d, c, f"{p:.1f}%", "Oui" if j else "Non"))

    def _update_chart(self, turns, don_dispo, probas, tour_ideal, seuil):
        self.ax.clear()
        self.ax.plot(turns, don_dispo, marker="s", color="#c0392b", label="DON!! disponible")
        self.ax.axhline(seuil, color="#c0392b", linestyle="--", alpha=0.5, label=f"Cout requis ({seuil})")

        ax2 = self.ax.twinx()
        ax2.plot(turns, probas, marker="o", color="#2471a3", label="Proba carte en main (%)")
        ax2.set_ylabel("Probabilite (%)", color="#2471a3")
        ax2.set_ylim(0, 100)

        if tour_ideal:
            self.ax.axvline(tour_ideal, color="#0a6b2d", linestyle=":", alpha=0.7)

        self.ax.set_xlabel("Tour")
        self.ax.set_ylabel("DON!! disponible", color="#c0392b")
        self.ax.set_xticks(turns)
        self.ax.grid(True, linestyle="--", alpha=0.3)

        lines1, labels1 = self.ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        self.ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8)

        self.canvas.draw()


# ---------------------------------------------------------------------------
# Onglet 4 : Effets supplementaires (recherche top X / pioche X-defausse X)
# ---------------------------------------------------------------------------

EFFECT_TYPES = [
    "Recherche (regarder les X premieres cartes du deck)",
    "Pioche X / Defausse X",
]


class EffectsPanel(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.effects = []  # liste de dicts {type, valeur, utilisations}
        self._build_inputs()
        self._build_effects_list()
        self._build_table()
        self._build_chart()
        self.calculer()

    def _build_inputs(self):
        frame = ttk.LabelFrame(self, text="Parametres du deck")
        frame.pack(fill="x", padx=10, pady=10)
        row = 0

        ttk.Label(frame, text="Taille du deck :").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        self.deck_size_var = tk.IntVar(value=50)
        ttk.Entry(frame, textvariable=self.deck_size_var, width=8).grid(row=row, column=1, padx=5, pady=5)

        ttk.Label(frame, text="Vie du Leader :").grid(row=row, column=2, padx=5, pady=5, sticky="w")
        self.life_var = tk.IntVar(value=5)
        life_frame = ttk.Frame(frame)
        life_frame.grid(row=row, column=3, sticky="w")
        for i, v in enumerate([3, 4, 5, 6]):
            ttk.Radiobutton(life_frame, text=str(v), value=v, variable=self.life_var,
                             command=self.calculer).grid(row=0, column=i, padx=3)

        row += 1
        self.starting_hand_var = tk.IntVar(value=5)
        block = build_position_and_drawpoints_block(frame, row, self.starting_hand_var, self.calculer)
        self.position_var = block["position_var"]
        self.draw_points_var = block["draw_points_var"]
        row = block["next_row"]

        self.xaxis_var, row = build_xaxis_toggle(frame, row, self.calculer)

        ttk.Label(frame, text="Copies dans le deck a comparer :").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        self.copies_vars = {}
        copies_frame = ttk.Frame(frame)
        copies_frame.grid(row=row, column=1, columnspan=3, sticky="w")
        for i, k in enumerate([1, 2, 3, 4]):
            var = tk.BooleanVar(value=(k in (2, 3, 4)))
            self.copies_vars[k] = var
            ttk.Checkbutton(copies_frame, text=f"{k}x", variable=var).grid(row=0, column=i, padx=8)

        row += 1
        self.deck_effectif_label = ttk.Label(frame, text="", foreground="#0a6b2d", font=("TkDefaultFont", 9, "bold"))
        self.deck_effectif_label.grid(row=row, column=0, columnspan=4, padx=5, pady=(0, 5), sticky="w")

    def _build_effects_list(self):
        frame = ttk.LabelFrame(self, text="Effets supplementaires (recherche / pioche-defausse) - cumulables")
        frame.pack(fill="x", padx=10, pady=5)

        form = ttk.Frame(frame)
        form.pack(fill="x", padx=5, pady=5)

        ttk.Label(form, text="Type :").grid(row=0, column=0, padx=4, sticky="w")
        self.effect_type_var = tk.StringVar(value=EFFECT_TYPES[0])
        ttk.Combobox(form, textvariable=self.effect_type_var, values=EFFECT_TYPES,
                     state="readonly", width=42).grid(row=0, column=1, padx=4)

        ttk.Label(form, text="Valeur X :").grid(row=0, column=2, padx=4, sticky="w")
        self.effect_valeur_var = tk.IntVar(value=3)
        ttk.Spinbox(form, from_=1, to=10, textvariable=self.effect_valeur_var, width=5).grid(row=0, column=3, padx=4)

        ttk.Label(form, text="Utilisations :").grid(row=0, column=4, padx=4, sticky="w")
        self.effect_uses_var = tk.IntVar(value=1)
        ttk.Spinbox(form, from_=1, to=10, textvariable=self.effect_uses_var, width=5).grid(row=0, column=5, padx=4)

        ttk.Button(form, text="Ajouter", command=self._add_effect).grid(row=0, column=6, padx=8)

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="x", padx=5, pady=5)
        self.effects_tree = ttk.Treeview(list_frame, show="headings", height=4,
                                          columns=("type", "valeur", "utilisations", "cartes"))
        for col, label, width in [
            ("type", "Type", 320), ("valeur", "Valeur X", 80),
            ("utilisations", "Utilisations", 90), ("cartes", "Cartes ajoutees", 110),
        ]:
            self.effects_tree.heading(col, text=label)
            self.effects_tree.column(col, width=width, anchor="center")
        self.effects_tree.pack(fill="x", side="left", expand=True)

        ttk.Button(list_frame, text="Supprimer\nla selection", command=self._remove_effect).pack(side="left", padx=8)

        self.total_extra_label = ttk.Label(frame, text="Total cartes ajoutees par les effets : 0",
                                            font=("TkDefaultFont", 9, "bold"))
        self.total_extra_label.pack(anchor="w", padx=5, pady=(0, 5))

    def _add_effect(self):
        self.effects.append({
            "type": self.effect_type_var.get(),
            "valeur": self.effect_valeur_var.get(),
            "utilisations": self.effect_uses_var.get(),
        })
        self._refresh_effects_tree()
        self.calculer()

    def _remove_effect(self):
        sel = self.effects_tree.selection()
        if not sel:
            return
        idx = self.effects_tree.index(sel[0])
        del self.effects[idx]
        self._refresh_effects_tree()
        self.calculer()

    def _refresh_effects_tree(self):
        self.effects_tree.delete(*self.effects_tree.get_children())
        for e in self.effects:
            cartes = e["valeur"] * e["utilisations"]
            self.effects_tree.insert("", "end", values=(e["type"], e["valeur"], e["utilisations"], cartes))

    def _total_extra_cartes(self):
        return sum(e["valeur"] * e["utilisations"] for e in self.effects)

    def _build_table(self):
        frame = ttk.LabelFrame(self, text="Resultats")
        frame.pack(fill="both", expand=False, padx=10, pady=5)
        self.tree = ttk.Treeview(frame, show="headings", height=6)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

    def _build_chart(self):
        frame = ttk.LabelFrame(self, text="Graphique")
        frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.figure = Figure(figsize=(7, 3.4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    def calculer(self):
        try:
            N_deck = self.deck_size_var.get()
            life = self.life_var.get()
            N = N_deck - life
            if N <= 0:
                messagebox.showerror("Erreur", "La vie du leader ne peut pas depasser/egaler la taille du deck.")
                return
            self.deck_effectif_label.config(
                text=f"-> Deck effectif (piochable) : {N_deck} - {life} (cartes de vie) = {N} cartes"
            )

            base_points = parse_draw_points(self.draw_points_var.get())
            copies_selected = [k for k, v in self.copies_vars.items() if v.get()]
            if not copies_selected:
                messagebox.showwarning("Attention", "Selectionne au moins un nombre de copies (1x, 2x, 3x ou 4x).")
                return
            if not base_points:
                messagebox.showwarning("Attention", "Indique au moins un nombre de cartes vues.")
                return

            extra = self._total_extra_cartes()
            self.total_extra_label.config(text=f"Total cartes ajoutees par les effets : {extra}")

            position = self.position_var.get()
            self.turns_for_points = list(range(1, len(base_points) + 1)) if position in ("p1", "p2") else None

            total_points = [min(n + extra, N) for n in base_points]

            results = {K: [proba_au_moins_une(N, K, n) for n in total_points] for K in copies_selected}

            self._update_table(base_points, extra, total_points, results)
            self._update_chart(N, total_points, results)

        except ValueError:
            messagebox.showerror("Erreur", "Verifie que les champs numeriques sont valides (entiers).")

    def _update_table(self, base_points, extra, total_points, results):
        show_turn = self.turns_for_points is not None
        columns = (["tour"] if show_turn else []) + ["base", "effets", "total"] + [f"{k}x_copies" for k in results]
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = columns

        if show_turn:
            self.tree.heading("tour", text="Tour")
            self.tree.column("tour", width=55, anchor="center")
        self.tree.heading("base", text="Cartes vues (base)")
        self.tree.column("base", width=120, anchor="center")
        self.tree.heading("effets", text="+ Effets")
        self.tree.column("effets", width=80, anchor="center")
        self.tree.heading("total", text="Total vues")
        self.tree.column("total", width=90, anchor="center")
        for k in results:
            self.tree.heading(f"{k}x_copies", text=f"{k}x dans le deck")
            self.tree.column(f"{k}x_copies", width=130, anchor="center")

        for i, n in enumerate(base_points):
            row = ([self.turns_for_points[i]] if show_turn else []) + [n, extra, total_points[i]] + \
                  [f"{results[k][i]:.1f}%" for k in results]
            self.tree.insert("", "end", values=row)

    def _update_chart(self, N, total_points, results):
        self.ax.clear()
        use_turn_axis = self.xaxis_var.get() == "tour" and self.turns_for_points is not None
        x_values = self.turns_for_points if use_turn_axis else total_points

        for k, probs in results.items():
            self.ax.plot(x_values, probs, marker="o", label=f"{k} copies dans le deck")

        self.ax.set_title(f"Probabilite avec effets inclus (deck effectif de {N} cartes)", fontsize=10)
        self.ax.set_xlabel("Tour" if use_turn_axis else "Total cartes vues (pioche + effets)")
        self.ax.set_ylabel("Probabilite (%)")
        self.ax.set_ylim(0, 100)
        self.ax.grid(True, linestyle="--", alpha=0.5)
        self.ax.legend()
        self.canvas.draw()


# ---------------------------------------------------------------------------
# Onglet 5 : Combinaisons (jusqu'a 5 cartes, minimum requis par carte)
# ---------------------------------------------------------------------------

class ComboPanel(ttk.Frame):
    MAX_CARDS = 5

    def __init__(self, master):
        super().__init__(master)
        self.cards = []  # liste de dicts {nom, copies, minimum}
        self._build_inputs()
        self._build_cards_list()
        self._build_table()
        self._build_chart()
        self.calculer()

    def _build_inputs(self):
        frame = ttk.LabelFrame(self, text="Parametres du deck")
        frame.pack(fill="x", padx=10, pady=10)
        row = 0

        ttk.Label(frame, text="Taille du deck :").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        self.deck_size_var = tk.IntVar(value=50)
        ttk.Entry(frame, textvariable=self.deck_size_var, width=8).grid(row=row, column=1, padx=5, pady=5)

        ttk.Label(frame, text="Vie du Leader :").grid(row=row, column=2, padx=5, pady=5, sticky="w")
        self.life_var = tk.IntVar(value=5)
        life_frame = ttk.Frame(frame)
        life_frame.grid(row=row, column=3, sticky="w")
        for i, v in enumerate([3, 4, 5, 6]):
            ttk.Radiobutton(life_frame, text=str(v), value=v, variable=self.life_var,
                             command=self.calculer).grid(row=0, column=i, padx=3)

        row += 1
        self.starting_hand_var = tk.IntVar(value=5)
        block = build_position_and_drawpoints_block(frame, row, self.starting_hand_var, self.calculer)
        self.position_var = block["position_var"]
        self.draw_points_var = block["draw_points_var"]
        row = block["next_row"]

        self.xaxis_var, row = build_xaxis_toggle(frame, row, self.calculer)

        self.deck_effectif_label = ttk.Label(frame, text="", foreground="#0a6b2d", font=("TkDefaultFont", 9, "bold"))
        self.deck_effectif_label.grid(row=row, column=0, columnspan=4, padx=5, pady=(0, 5), sticky="w")

    def _build_cards_list(self):
        frame = ttk.LabelFrame(self, text=f"Cartes de la combinaison (jusqu'a {self.MAX_CARDS})")
        frame.pack(fill="x", padx=10, pady=5)

        form = ttk.Frame(frame)
        form.pack(fill="x", padx=5, pady=5)

        ttk.Label(form, text="Nom (optionnel) :").grid(row=0, column=0, padx=4, sticky="w")
        self.card_name_var = tk.StringVar(value="")
        ttk.Entry(form, textvariable=self.card_name_var, width=18).grid(row=0, column=1, padx=4)

        ttk.Label(form, text="Copies dans le deck :").grid(row=0, column=2, padx=4, sticky="w")
        self.card_copies_var = tk.IntVar(value=4)
        ttk.Spinbox(form, from_=1, to=4, textvariable=self.card_copies_var, width=5).grid(row=0, column=3, padx=4)

        ttk.Label(form, text="Minimum requis :").grid(row=0, column=4, padx=4, sticky="w")
        self.card_min_var = tk.IntVar(value=1)
        ttk.Spinbox(form, from_=1, to=4, textvariable=self.card_min_var, width=5).grid(row=0, column=5, padx=4)

        ttk.Button(form, text="Ajouter la carte", command=self._add_card).grid(row=0, column=6, padx=8)

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="x", padx=5, pady=5)
        self.cards_tree = ttk.Treeview(list_frame, show="headings", height=5,
                                        columns=("nom", "copies", "minimum"))
        for col, label, width in [("nom", "Nom", 220), ("copies", "Copies dans le deck", 140),
                                   ("minimum", "Minimum requis", 130)]:
            self.cards_tree.heading(col, text=label)
            self.cards_tree.column(col, width=width, anchor="center")
        self.cards_tree.pack(fill="x", side="left", expand=True)

        ttk.Button(list_frame, text="Supprimer\nla selection", command=self._remove_card).pack(side="left", padx=8)

        self.cards_summary_label = ttk.Label(frame, text="", font=("TkDefaultFont", 9))
        self.cards_summary_label.pack(anchor="w", padx=5, pady=(0, 5))

    def _add_card(self):
        if len(self.cards) >= self.MAX_CARDS:
            messagebox.showwarning("Attention", f"Maximum {self.MAX_CARDS} cartes dans une combinaison.")
            return
        copies = self.card_copies_var.get()
        minimum = self.card_min_var.get()
        if minimum > copies:
            messagebox.showerror("Erreur", "Le minimum requis ne peut pas depasser le nombre de copies dans le deck.")
            return
        nom = self.card_name_var.get().strip() or f"Carte {len(self.cards) + 1}"
        self.cards.append({"nom": nom, "copies": copies, "minimum": minimum})
        self._refresh_cards_tree()
        self.card_name_var.set("")
        self.calculer()

    def _remove_card(self):
        sel = self.cards_tree.selection()
        if not sel:
            return
        idx = self.cards_tree.index(sel[0])
        del self.cards[idx]
        self._refresh_cards_tree()
        self.calculer()

    def _refresh_cards_tree(self):
        self.cards_tree.delete(*self.cards_tree.get_children())
        for c in self.cards:
            self.cards_tree.insert("", "end", values=(c["nom"], c["copies"], c["minimum"]))

    def _build_table(self):
        frame = ttk.LabelFrame(self, text="Resultats")
        frame.pack(fill="both", expand=False, padx=10, pady=5)
        self.tree = ttk.Treeview(frame, show="headings", height=6, columns=("tour", "cartes_vues", "proba"))
        self.tree.heading("tour", text="Tour")
        self.tree.column("tour", width=60, anchor="center")
        self.tree.heading("cartes_vues", text="Cartes vues")
        self.tree.column("cartes_vues", width=110, anchor="center")
        self.tree.heading("proba", text="Probabilite de la combinaison")
        self.tree.column("proba", width=220, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

    def _build_chart(self):
        frame = ttk.LabelFrame(self, text="Graphique")
        frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.figure = Figure(figsize=(7, 3.4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    def calculer(self):
        try:
            N_deck = self.deck_size_var.get()
            life = self.life_var.get()
            N = N_deck - life
            if N <= 0:
                messagebox.showerror("Erreur", "La vie du leader ne peut pas depasser/egaler la taille du deck.")
                return
            self.deck_effectif_label.config(
                text=f"-> Deck effectif (piochable) : {N_deck} - {life} (cartes de vie) = {N} cartes"
            )

            if len(self.cards) < 1:
                self.cards_summary_label.config(text="Ajoute au moins une carte pour lancer le calcul (2+ pour une vraie combinaison).")
                self.tree.delete(*self.tree.get_children())
                self.ax.clear()
                self.canvas.draw()
                return

            total_K = sum(c["copies"] for c in self.cards)
            if total_K > N:
                messagebox.showerror("Erreur", "Le total de copies des cartes selectionnees depasse le deck effectif.")
                return
            self.cards_summary_label.config(
                text=f"{len(self.cards)} carte(s) - {total_K} copies au total utilisees sur {N} cartes du deck effectif."
            )

            draw_points = parse_draw_points(self.draw_points_var.get())
            if not draw_points:
                messagebox.showwarning("Attention", "Indique au moins un nombre de cartes vues.")
                return
            draw_points = [n for n in draw_points if n <= N]
            if not draw_points:
                messagebox.showerror("Erreur", "Aucun point de pioche valide (superieur a la taille du deck effectif).")
                return

            position = self.position_var.get()
            self.turns_for_points = list(range(1, len(draw_points) + 1)) if position in ("p1", "p2") else None

            cartes_combo = [(c["copies"], c["minimum"]) for c in self.cards]
            probas = [proba_combo(N, cartes_combo, n) for n in draw_points]

            self._update_table(draw_points, probas)
            self._update_chart(N, draw_points, probas)

        except ValueError:
            messagebox.showerror("Erreur", "Verifie que les champs numeriques sont valides (entiers).")

    def _update_table(self, draw_points, probas):
        self.tree.delete(*self.tree.get_children())
        show_turn = self.turns_for_points is not None
        for i, n in enumerate(draw_points):
            tour = self.turns_for_points[i] if show_turn else "-"
            self.tree.insert("", "end", values=(tour, n, f"{probas[i]:.1f}%"))

    def _update_chart(self, N, draw_points, probas):
        self.ax.clear()
        use_turn_axis = self.xaxis_var.get() == "tour" and self.turns_for_points is not None
        x_values = self.turns_for_points if use_turn_axis else draw_points

        noms = " + ".join(f"{c['minimum']}x {c['nom']}" for c in self.cards)
        self.ax.plot(x_values, probas, marker="o", color="#8e44ad", label=noms)

        self.ax.set_title(f"Probabilite de la combinaison (deck effectif de {N} cartes)", fontsize=9)
        self.ax.set_xlabel("Tour" if use_turn_axis else "Nombre de cartes vues")
        self.ax.set_ylabel("Probabilite (%)")
        self.ax.set_ylim(0, 100)
        self.ax.grid(True, linestyle="--", alpha=0.5)
        self.ax.legend(fontsize=8)
        self.canvas.draw()


# ---------------------------------------------------------------------------
# Fenetre principale
# ---------------------------------------------------------------------------

class OPCGApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("One Piece TCG - Calculateur de probabilite de pioche")
        self.geometry("960x820")
        self.configure(bg="#f4f4f4")
        self.resizable(True, True)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)

        notebook.add(ProbaPanel(notebook, use_life=False), text="Standard")
        notebook.add(ProbaPanel(notebook, use_life=True), text="Vie du Leader")
        notebook.add(DonPanel(notebook), text="Cout DON!!")
        notebook.add(EffectsPanel(notebook), text="Effets supplementaires")
        notebook.add(ComboPanel(notebook), text="Combinaisons")


if __name__ == "__main__":
    app = OPCGApp()
    app.mainloop()
