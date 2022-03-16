import os


def printProgressBar(iteration, total, stage='', decimals=2, length=50, fill='█'):
    # Print a progressbar to keep track of progression
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))

    try:  # on récupère la taille de la fenêtre du terminal
        length = os.get_terminal_size().columns - 70
    except OSError:  # sinon c'est 50, parce que suivant le terminal ça fonctionne pas
        pass

    # Combien faut-il remplir la barre
    filledLength = int(length * iteration // total)
    # On crée la barre sous forme de chaîne de caractère
    bar = fill * filledLength + '░' * (length - filledLength)
    # on l'a print, le \r permet de réécrire sur la même ligne
    print(f'\r│{bar}│ {percent}% ({iteration:,} / {total:,}) {stage}', end="", flush=True)

    # si on a atteint le max on retourne à la ligne
    if iteration == total:
        print("\n")
    return None
