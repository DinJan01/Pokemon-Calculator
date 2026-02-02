import re
from collections import defaultdict


# ------------------------------------------------------------
# Regex definitions (all in one place)
# ------------------------------------------------------------

TEAM_HEADER_REGEX = re.compile(r"^(?P<player>.+)'s team:$")
TEAM_LIST_REGEX = re.compile(r"^(?P<team>.+(?: / .+)+)$")

SENDOUT_REGEX = re.compile(
    r"^(?:The opposing )?(?:\w+ )?sent out (?P<nickname>[A-Za-z0-9\-']+)"
    r"(?: \((?P<species>[A-Za-z0-9\-]+)\))?!"
)

MOVE_REGEX = re.compile(
    r"^(?:The opposing )?(?P<attacker>[A-Za-z0-9\-]+) used "
)

DAMAGE_REGEX = re.compile(
    r"^\((?:The opposing )?(?P<target>[A-Za-z0-9\-]+) lost \d+% of its health!\)"
)

FAINT_REGEX = re.compile(
    r"^(?:The opposing )?(?P<fainted>[A-Za-z0-9\-]+) fainted!"
)

PASSIVE_DAMAGE_REGEX = re.compile(
    r"was hurt by its burn|was hurt by poison|lost some of its HP|hung on using its Focus Sash"
)


# ------------------------------------------------------------
# Phase 1 — Extract team ownership (species -> player)
# ------------------------------------------------------------

def extract_team_info(lines):
    species_to_player = {}
    current_player = None

    for line in lines:
        line = line.strip()

        header_match = TEAM_HEADER_REGEX.search(line)
        if header_match:
            current_player = header_match.group("player")
            continue

        list_match = TEAM_LIST_REGEX.search(line)
        if list_match and current_player:
            team_line = list_match.group("team")
            pokemon_list = [p.strip() for p in team_line.split("/")]

            for species in pokemon_list:
                species_to_player[species] = current_player

    return species_to_player


# ------------------------------------------------------------
# Helper — determine correct killer from attack history
# ------------------------------------------------------------

def find_valid_killer(fainted, attack_history, nickname_to_species, species_to_player):
    history = attack_history.get(fainted, [])
    victim_species = nickname_to_species.get(fainted, fainted)
    victim_player = species_to_player.get(victim_species)

    # Check attackers from most recent backwards
    for attacker in reversed(history):
        attacker_species = nickname_to_species.get(attacker, attacker)
        attacker_player = species_to_player.get(attacker_species)

        if attacker_player != victim_player:
            return attacker

    return None


# ------------------------------------------------------------
# Phase 2 — Main battle parsing
# ------------------------------------------------------------

def parse_battle(lines, species_to_player):
    kills = {}
    deaths = {}

    nickname_to_species = {}
    attack_history = defaultdict(list)

    current_attacker = None
    last_move_used = None
    last_final_gambit_target = None

    for line in lines:
        line = line.strip()

        # ------------------ Send out (nickname -> species)
        sendout_match = SENDOUT_REGEX.search(line)
        if sendout_match:
            nickname = sendout_match.group("nickname")
            species = sendout_match.group("species") or nickname
            nickname_to_species[nickname] = species
            continue

        # ------------------ Move used
        move_match = MOVE_REGEX.search(line)
        if move_match:
            current_attacker = move_match.group("attacker")
            last_move_used = line.split(" used ", 1)[1].rstrip("!") if " used " in line else None
            last_final_gambit_target = None
            continue

        # ------------------ Ignore passive damage
        if PASSIVE_DAMAGE_REGEX.search(line):
            continue

        # ------------------ Damage dealt
        damage_match = DAMAGE_REGEX.search(line)
        if damage_match and current_attacker:
            target = damage_match.group("target")

            if target != current_attacker:
                attack_history[target].append(current_attacker)

                if last_move_used == "Final Gambit":
                    last_final_gambit_target = target
            continue

        # ------------------ Faint handling
        faint_match = FAINT_REGEX.search(line)
        if faint_match:
            fainted = faint_match.group("fainted")
            fainted_species = nickname_to_species.get(fainted, fainted)

            # Record death
            deaths[fainted_species] = deaths.get(fainted_species, 0) + 1

            # Determine killer from history
            killer = find_valid_killer(
                fainted,
                attack_history,
                nickname_to_species,
                species_to_player
            )

            # Special case: Final Gambit self-KO
            if killer is None and fainted == current_attacker and last_move_used == "Final Gambit":
                killer = last_final_gambit_target

            # Record kill if valid
            if killer:
                killer_species = nickname_to_species.get(killer, killer)
                kills[killer_species] = kills.get(killer_species, 0) + 1

            # Clear history for this Pokémon
            attack_history.pop(fainted, None)
            last_final_gambit_target = None
            continue

    return kills, deaths


# ------------------------------------------------------------
# Entry point
# ------------------------------------------------------------

def parse_log(log_text):
    lines = log_text.splitlines()

    species_to_player = extract_team_info(lines)
    kills, deaths = parse_battle(lines, species_to_player)

    return kills, deaths


# ------------------------------------------------------------
# Run
# ------------------------------------------------------------

if __name__ == "__main__":
    with open("gamelog.txt", "r", encoding="utf-8") as f:
        log_text = f.read()

    kills, deaths = parse_log(log_text)

    print("KILLS")
    for pokemon, count in kills.items():
        print(f"{pokemon}: {count}")

    print("\nDEATHS")
    for pokemon, count in deaths.items():
        print(f"{pokemon}: {count}")
