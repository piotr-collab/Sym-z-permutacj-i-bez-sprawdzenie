# RSA dimery: permutacja vs bez permutacji

Projekt sprawdza, czy dla prostej symulacji RSA dimerow na kratce 100x100 wyniki roznia sie miedzy dwiema seriami:

- bez wstepnej permutacji kandydatow,
- z losowa permutacja pelnej listy mozliwych polozen dimeru.

Zgodnie z promptem wykonano po 500 pelnych przebiegow dla kazdej metody.

## Najwazniejszy wynik

Nie znaleziono istotnej roznicy miedzy metodami dla pokrycia przy perkolacji `Cp` ani dla pokrycia przy jammmingu `Cj`.

| Wielkosc | Bez permutacji | Z permutacja | Roznica | p approx. |
|---|---:|---:|---:|---:|
| Cp | 0.551877 | 0.550310 | -0.001567 | 0.112 |
| Cj | 0.906565 | 0.906510 | -0.000055 | 0.727 |

Interpretacja: permutacja zmienia sposob organizacji losowania i koszt obliczeniowy, ale nie powinna zmieniac rozkladu `Cp` i `Cj`, o ile lista kandydatow, warunki brzegowe i kryterium akceptacji sa takie same.

## Pliki

- `scripts/rsa_permutation_comparison.py` - program wykonujacy symulacje i generujacy CSV oraz wykresy.
- `scripts/build_reports.py` - program skladajacy dokumenty DOCX.
- `data/rsa_500_runs_per_method.csv` - wszystkie 1000 przebiegow.
- `data/rsa_summary_statistics.csv` - statystyki opisowe.
- `data/rsa_method_comparison.csv` - porownanie metod.
- `figures/` - histogramy, boxplot, wskazniki i konfiguracje perkolacji/jammingu.
- `logs/dziennik_symulacji.md` - dziennik wykonania.
- `reports/raport_wyniki_RSA_dimery_permutacja_vs_bez.docx` - raport z wynikami.
- `reports/opracowanie_permutacja_w_RSA_wyjasnienie_i_dyskusja.docx` - osobne opracowanie o permutacji i jej wplywie.

## Uwaga o zrodle promptu

Repozytorium GitHub wskazane w poleceniu bylo puste podczas pracy, dlatego tresc promptu zostala pobrana z lokalnego pliku:

`/Users/piotrlunkiewicz/Desktop/Doktorat UAM/Zadania/Permutacja sprawdzamy/###Symulacja permutacja czy coś zmienia?`
