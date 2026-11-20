"""Stratégies locales et lancement sur fenêtre, temps en heures."""
RULES = {"due", "fifo", "family_fifo", "batch_fifo"}


def release_time(arrival, due, window):
    return max(arrival, due-window)


def select_batch(queue, family, deadline, current, size, rule):
    if rule not in RULES:
        raise ValueError(f"Règle inconnue {rule}")
    if rule == "fifo":
        return sorted(queue)[:1]
    groups = {}
    key = (lambda entry: (deadline(entry[1]), *entry)) if rule == "due" else None
    for entry in sorted(queue, key=key):
        groups.setdefault(family(entry[1]), []).append(entry)
    if not groups:
        return []
    name = current if rule == "family_fifo" and current in groups else next(iter(groups))
    # Pas d'attente : le poste regroupe ce qu'il a au poste, plafonné à size
    # (2 OF de même famille avec size=8 -> lot de 2). La série peut ensuite grossir
    # jusqu'à size pendant le traitement (voir run_congestion.ajouter).
    return groups[name][:size]
