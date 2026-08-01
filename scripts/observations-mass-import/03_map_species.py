#!/usr/bin/env python3
"""
Paso 8 del proceso de importación masiva de observaciones.

Mapea el campo `species` (texto libre) a species_id de Rainmapper para cada
fila de review_table.json. Gestiona casos simples, multi-especie y sin perfil.

Campos que añade/actualiza en review_table.json:
    species_ids            — lista de species_id mapeados ([] si ninguno)
    species_unmapped       — partes de la especie sin perfil en Rainmapper
    species_mapping_status — resultado del mapeo (ver tabla abajo)

species_mapping_status values:
    "mapped"         — 1 especie, tiene perfil → importable directamente
    "no_profile"     — 1 especie, sin perfil en Rainmapper
    "multi_full"     — varias especies, todas con perfil → genera N observaciones
    "multi_partial"  — varias especies, algunas con perfil → genera obs solo para las mapeadas
    "multi_none"     — varias especies, ninguna con perfil
    "unidentified"   — no identificada, no importar

Uso:
    .venv/bin/python scripts/observations-mass-import/03_map_species.py \\
        --review-table "/ruta/a/candidates/review_table.json" \\
        --profiles docker-data/mushroom-data/mushroom_profiles.json

    # Dry-run (no escribe):
    .venv/bin/python scripts/observations-mass-import/03_map_species.py \\
        --review-table "/ruta/a/candidates/review_table.json" \\
        --profiles docker-data/mushroom-data/mushroom_profiles.json \\
        --dry-run
"""

import argparse
import json
import re
from collections import Counter


def build_name_index(profiles):
    """Construye mapa nombre científico (lowercase) -> species_id."""
    index = {}
    for p in profiles:
        sid = p['species_id']
        sci = p.get('scientific_name', '').strip()
        if sci:
            index[sci.lower()] = sid
        for syn in p.get('synonyms', []):
            index[syn.strip().lower()] = sid
    return index


def split_species(species_str):
    """
    Divide una cadena de especies por '+', ignorando los '+' dentro de paréntesis.
    Ej: "Boletus sp. (mix: aereus + edulis)" → ["Boletus sp. (mix: aereus + edulis)"]
    Ej: "Boletus aereus + Amanita caesarea"  → ["Boletus aereus", "Amanita caesarea"]
    """
    parts = []
    depth = 0
    current = []
    for ch in species_str:
        if ch == '(':
            depth += 1
            current.append(ch)
        elif ch == ')':
            depth -= 1
            current.append(ch)
        elif ch == '+' and depth == 0:
            parts.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append(''.join(current).strip())
    return [p for p in parts if p]


def clean_name(name):
    """Limpia sufijos como '?' y espacios extra para la búsqueda en el índice."""
    name = re.sub(r'\(.*?\)', '', name)  # elimina contenido entre paréntesis
    name = name.strip().rstrip('?').strip()
    return name


# Aliases de nombre propios del usuario: especies "sp." que este usuario
# identifica siempre a nivel de especie concreta. Se aplican antes que las
# reglas contextuales, tanto en fotos simples como en partes de multi-especie.
USER_NAME_ALIASES = {
    'tricholoma sp': 'tricholoma_terreum',      # el único Tricholoma que recoge
    'morchella sp':  'morchella_elata_complex', # todas sus morcillas son elata complex
    'russula sp':    'russula_virescens',        # pendiente de revisión individual
}

AUTUMN_MONTHS = {9, 10, 11}


def resolve_boletus_sp(row):
    """
    Resuelve 'Boletus sp.' usando altitud y época:
      < 1000 m                  → boletus_aereus
      >= 1000 m + otoño (sep-nov) → boletus_edulis
      >= 1000 m + otra época      → boletus_pinophilus
    """
    alt_raw = row.get('alt') or ''
    try:
        alt = float(str(alt_raw).replace('m', '').strip())
    except (ValueError, TypeError):
        alt = None

    date = row.get('date') or ''
    try:
        month = int(date[5:7])
    except (ValueError, IndexError):
        month = None

    if alt is not None and alt < 1000:
        return 'boletus_aereus'
    if alt is not None and alt >= 1000:
        if month in AUTUMN_MONTHS:
            return 'boletus_edulis'
        return 'boletus_pinophilus'
    return None  # sin datos suficientes

# Reglas de desambiguación contextual:
# Si una parte no tiene perfil propio, pero las demás partes de la misma foto
# cumplen la condición, se resuelve al species_id indicado.
# Formato: (patron_sin_perfil, species_id_acompañante) -> species_id_resuelto
CONTEXT_RULES = [
    # Boletus sp. junto a Amanita caesarea → Boletus aereus
    # (co-fructificación en encinar mediterráneo)
    ('boletus sp', 'amanita_caesarea',    'boletus_aereus'),
    # Boletus sp. junto a Lactarius deliciosus → Boletus edulis (por época)
    ('boletus sp', 'lactarius_deliciosus', 'boletus_edulis'),
    # Boletus sp. junto a Tricholoma terreum → Boletus edulis (por época)
    ('boletus sp', 'tricholoma_terreum',  'boletus_edulis'),
    # Boletus sp. junto a Boletus edulis → el mismo, Boletus edulis
    ('boletus sp', 'boletus_edulis',      'boletus_edulis'),
]


def apply_context_rules(parts_clean, mapped_ids, unmapped_parts):
    """
    Intenta resolver partes sin perfil usando reglas contextuales.
    Devuelve (mapped_ids, unmapped_parts) actualizados.
    """
    resolved_mapped = list(mapped_ids)
    resolved_unmapped = []

    for part in unmapped_parts:
        resolved = False
        for pattern, companion_id, target_id in CONTEXT_RULES:
            if pattern in part.lower() and companion_id in resolved_mapped:
                resolved_mapped.append(target_id)
                resolved = True
                break
        if not resolved:
            resolved_unmapped.append(part)

    return resolved_mapped, resolved_unmapped


def map_row(row, name_index):
    sp = (row.get('species') or '').strip()
    conf = row.get('confidence', '')

    if conf == 'unidentified' or not sp or sp.lower() == 'indeterminada':
        return [], [], 'unidentified'

    parts = split_species(sp)

    mapped, unmapped = [], []
    for part in parts:
        clean = clean_name(part)
        key = clean.lower()
        sid = name_index.get(key)
        if not sid:
            # alias de usuario por prefijo
            for alias_key, alias_id in USER_NAME_ALIASES.items():
                if key.startswith(alias_key):
                    sid = alias_id
                    break
        if not sid and key.startswith('boletus sp'):
            # resolver por altitud y época
            sid = resolve_boletus_sp(row)
        if sid:
            mapped.append(sid)
        else:
            unmapped.append(clean)

    # Aplicar reglas contextuales para resolver partes sin perfil
    if len(parts) > 1 and unmapped:
        mapped, unmapped = apply_context_rules(parts, mapped, unmapped)

    if len(parts) == 1:
        if mapped:
            status = 'mapped'
        else:
            status = 'no_profile'
    else:
        if mapped and not unmapped:
            status = 'multi_full'
        elif mapped and unmapped:
            status = 'multi_partial'
        else:
            status = 'multi_none'

    return mapped, unmapped, status


def main():
    parser = argparse.ArgumentParser(description='Mapea species a species_id de Rainmapper')
    parser.add_argument('--review-table', required=True, help='Ruta a review_table.json')
    parser.add_argument('--profiles', required=True, help='Ruta a mushroom_profiles.json')
    parser.add_argument('--dry-run', action='store_true', help='No escribir cambios')
    args = parser.parse_args()

    with open(args.review_table) as f:
        table = json.load(f)
    with open(args.profiles) as f:
        profiles_data = json.load(f)

    name_index = build_name_index(profiles_data['species_profiles'])
    stats = Counter()

    for row in table:
        mapped, unmapped, status = map_row(row, name_index)
        row['species_ids'] = mapped
        row['species_unmapped'] = unmapped
        row['species_mapping_status'] = status
        stats[status] += 1

    print("Resultado del mapeo:")
    print(f"  mapped         (1 especie, con perfil):            {stats['mapped']}")
    print(f"  multi_full     (varias especies, todas con perfil): {stats['multi_full']}")
    print(f"  multi_partial  (varias especies, algunas sin perfil): {stats['multi_partial']}")
    print(f"  multi_none     (varias especies, ninguna con perfil): {stats['multi_none']}")
    print(f"  no_profile     (1 especie, sin perfil):             {stats['no_profile']}")
    print(f"  unidentified   (no identificadas):                  {stats['unidentified']}")

    importable = stats['mapped'] + stats['multi_full'] + stats['multi_partial']
    obs_count = stats['mapped']
    for row in table:
        if row['species_mapping_status'] in ('multi_full', 'multi_partial'):
            obs_count += len(row['species_ids'])
    print(f"\nObservaciones importables (tras split multi-especie): {obs_count}")
    print(f"Fotos no importables (sin perfil + unidentified):      {stats['no_profile'] + stats['unidentified'] + stats['multi_none']}")

    no_profile_species = Counter()
    for row in table:
        for sp in row.get('species_unmapped', []):
            if sp:
                no_profile_species[sp] += 1
    if no_profile_species:
        print(f"\nEspecies sin perfil ({len(no_profile_species)} distintas):")
        for sp, n in no_profile_species.most_common():
            print(f"  {n:3}  {sp}")

    if not args.dry_run:
        with open(args.review_table, 'w') as f:
            json.dump(table, f, ensure_ascii=False, indent=2)
        print(f"\nEscrito: {args.review_table}")
    else:
        print("\nDry-run: no se ha escrito nada.")


if __name__ == '__main__':
    main()
