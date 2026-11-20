"""Stratégies locales et lancement sur fenêtre, temps en heures."""
RULES = {"due", "fifo", "family_fifo", "batch_fifo"}


def release_time(arrival, due, window):
    return max(arrival, due-window)


def select_batch(queue, family, deadline, current, size, min_size, wait, now, rule):
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
    # Taille minimale de lot : on attend d'avoir min_size OF de la famille,
    # sauf si le plus ancien a attendu `wait` heures (borne anti-blocage).
    # min_size = 1 -> aucune attente (lot = ce qui est présent, plafonné à size).
    eligible = [name for name, group in groups.items()
                if len(group) >= min_size or min(t for t, _ in group) + wait <= now]
    if not eligible:
        return []
    name = current if rule == "family_fifo" and current in eligible else eligible[0]
    # La série est plafonnée à size ; les arrivées de même famille pendant le
    # traitement rejoignent la série jusqu'à size (voir run_congestion.ajouter).
    return groups[name][:size]
