import random
import time
import sys
import json
import os
import hashlib

# --- CONFIGURATION & DATA ---

MAP_SIZE = 5

BIOMES = [
    {"name": "Whispering Woods", "theme": "Fantasy", "desc": "Violet leaves fall gently around you."},
    {"name": "Neon Slums", "theme": "Sci-Fi", "desc": "Holographic ads flicker in the pouring rain."},
    {"name": "Cursed Crypt", "theme": "Horror", "desc": "A cold fog rolls over ancient tombstones."},
    {"name": "Sunken Grotto", "theme": "Adventure", "desc": "The sound of rushing water echoes in the dark."}
]

ENEMIES = {
    "Fantasy": ["Goblin Scout", "Corrupted Wolf", "Bandit King"],
    "Sci-Fi": ["Rogue Drone", "Cyber-Punk", "Security Bot"],
    "Horror": ["Restless Spirit", "Zombie", "Vampire Fledgling"],
    "Adventure": ["Giant Crab", "Pirate", "Slime"]
}

ROAMING_BOSSES = {
    "Fantasy": "Elder Dragon",
    "Sci-Fi": "Mecha-Titan",
    "Horror": "Lich Lord",
    "Adventure": "Kraken"
}

ITEMS = {
    "Iron Sword":     {"type": "weapon", "value": 5, "cost": 50,  "tier": 0, "desc": "A standard soldier's blade."},
    "Plasma Rifle":   {"type": "weapon", "value": 10,"cost": 150, "tier": 1, "desc": "Shoots superheated energy bolts."},
    "Demon Blade":    {"type": "weapon", "value": 20,"cost": 400, "tier": 2, "desc": "Glows with a cursed red aura."},
    "Leather Armor":  {"type": "armor",  "value": 2, "cost": 40,  "tier": 0, "desc": "Basic protection against cuts."},
    "Nano-Suit":      {"type": "armor",  "value": 6, "cost": 120, "tier": 1, "desc": "Lightweight synthetic plating."},
    "Dragon Plate":   {"type": "armor",  "value": 12,"cost": 450, "tier": 2, "desc": "Forged from the scales of an Elder Dragon."}
}

SPELLS = {
    "1": {"name": "Fireball",    "cost": 12, "dmg_mult": 2.5, "desc": "Hurls a massive ball of flame."},
    "2": {"name": "Lightning",   "cost": 8,  "dmg_mult": 1.5, "desc": "A quick, accurate zap of electricity."},
    "3": {"name": "Holy Light",  "cost": 15, "heal": 60,      "desc": "Divinely restores a large chunk of HP."},
    "4": {"name": "Armageddon",  "cost": 50, "dmg_mult": 5.0, "desc": "Ultimate magic. Requires Magic Tower."} 
}

BUILDINGS = {
    "Blacksmith":  {"cost": 300, "desc": "Unlocks Tier 2 Weapons/Armor in Shop."},
    "Temple":      {"cost": 250, "desc": "Restores full HP/MP for free upon visiting Town."},
    "Magic Tower": {"cost": 500, "desc": "Unlocks the 'Armageddon' spell."}
}

# --- UI & UTILS ---

def draw_ui(title, lines):
    """Draws a box around text for cleaner menus."""
    width = 60
    print("\n" + "╔" + "═" * width + "╗")
    print(f"║ {title.center(width-2)} ║")
    print("╠" + "═" * width + "╣")
    for line in lines:
        print(f"║ {line.ljust(width-2)} ║")
    print("╚" + "═" * width + "╝")

def type_text(text, speed=0.02):
    """Typing effect for description text."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(speed)
    print()

def hash_password(password):
    """Securely hash passwords so they aren't stored as plain text."""
    return hashlib.sha256(password.encode()).hexdigest()

# --- PLAYER CLASS ---

class Player:
    def __init__(self):
        self.name = "Hero"
        self.state = "alive"
        # Stats
        self.hp = 100
        self.max_hp = 100
        self.mp = 40
        self.max_mp = 40
        self.base_attack = 10
        self.gold = 100
        self.xp = 0
        self.level = 1
        self.xp_to_next_level = 100
        # Inventory
        self.potions = 2
        self.mana_potions = 2
        self.inventory = [] 
        self.equipped_weapon = None
        self.equipped_armor = None
        # World State
        self.active_quest = None 
        self.town_upgrades = [] 
        self.x = 2
        self.y = 2

    @property
    def total_attack(self):
        bonus = ITEMS[self.equipped_weapon]['value'] if self.equipped_weapon else 0
        return self.base_attack + bonus

    @property
    def defense(self):
        return ITEMS[self.equipped_armor]['value'] if self.equipped_armor else 0

    def drink_potion(self):
        if self.potions > 0:
            self.hp = min(self.max_hp, self.hp + 40)
            self.potions -= 1
            print(f"   🧪 You drank a Health Potion. HP: {self.hp}/{self.max_hp}.")
        else:
            print("   ❌ You have no Health Potions left!")

    def drink_mana_potion(self):
        if self.mana_potions > 0:
            self.mp = min(self.max_mp, self.mp + 30)
            self.mana_potions -= 1
            print(f"   🧪 You drank a Mana Potion. MP: {self.mp}/{self.max_mp}.")
        else:
            print("   ❌ You have no Mana Potions left!")

    def gain_xp(self, amount):
        self.xp += amount
        if self.xp >= self.xp_to_next_level:
            self.level_up()

    def level_up(self):
        self.xp -= self.xp_to_next_level
        self.level += 1
        self.xp_to_next_level = int(self.xp_to_next_level * 1.5)
        # Stat Increases
        self.max_hp += 20
        self.max_mp += 10
        self.base_attack += 3
        # Full Restore
        self.hp = self.max_hp
        self.mp = self.max_mp
        draw_ui("LEVEL UP!", [f"You are now Level {self.level}!", f"Max HP increased to {self.max_hp}", f"HP and MP fully restored!"])

    def check_quest(self, enemy_name):
        if self.active_quest and self.active_quest['target'] == enemy_name:
            self.active_quest['progress'] += 1
            print(f"   📜 Quest Update: {self.active_quest['target']} ({self.active_quest['progress']}/{self.active_quest['count']})")
            
            if self.active_quest['progress'] >= self.active_quest['count']:
                r_gold = self.active_quest['reward']
                r_xp = self.active_quest['xp']
                draw_ui("QUEST COMPLETE!", [f"You hunted down all {self.active_quest['target']}s!", f"Reward: {r_gold} Gold, {r_xp} XP"])
                self.gold += r_gold
                self.gain_xp(r_xp)
                self.active_quest = None

    def to_dict(self):
        return self.__dict__

    def from_dict(self, data):
        for k, v in data.items():
            setattr(self, k, v)
        # Safety defaults for older saves
        if not hasattr(self, 'town_upgrades'): self.town_upgrades = []
        if not hasattr(self, 'active_quest'): self.active_quest = None

# --- GAME ENGINE ---

class Game:
    def __init__(self):
        self.player = Player()
        self.running = True
        self.turn_count = 0
        self.world_map = []
        self.void_gate_open = False
        
        # Login Data
        self.username = None
        self.password_hash = None
        self.save_filename = None

    # --- LOGIN SYSTEM ---
    
    def start_app(self):
        """Entry point for the application."""
        while True:
            draw_ui("RPG v11.0: LOGIN SYSTEM", ["1. Login", "2. Register New User", "3. Exit"])
            c = input("> ").strip()
            
            if c == '1':
                if self.login():
                    self.main_menu()
            elif c == '2':
                self.register()
            elif c == '3':
                print("Goodbye.")
                sys.exit()
    
    def get_save_path(self, username):
        return f"rpg_save_{username}.json"

    def register(self):
        print("\n--- CREATE ACCOUNT ---")
        user = input("Choose Username: ").strip()
        if not user:
            print("Invalid username.")
            return
        
        filename = self.get_save_path(user)
        if os.path.exists(filename):
            print("❌ Username already exists! Please login instead.")
            return
        
        pw = input("Choose Password: ").strip()
        if not pw:
            print("Password cannot be empty.")
            return
        
        # Initialize fresh user
        self.username = user
        self.password_hash = hash_password(pw)
        self.save_filename = filename
        
        # Create empty game state
        self.player = Player()
        self.generate_map()
        self.turn_count = 0
        self.void_gate_open = False
        
        # Save to create the file
        self.save_game(verbose=False)
        print(f"✅ User '{user}' registered successfully! Please login now.")

    def login(self):
        print("\n--- LOGIN ---")
        user = input("Username: ").strip()
        filename = self.get_save_path(user)
        
        if not os.path.exists(filename):
            print("❌ User not found.")
            return False
        
        pw = input("Password: ").strip()
        attempt_hash = hash_password(pw)
        
        try:
            with open(filename, "r") as f:
                data = json.load(f)
                stored_hash = data.get("meta", {}).get("password_hash")
                
                if stored_hash == attempt_hash:
                    self.username = user
                    self.password_hash = stored_hash
                    self.save_filename = filename
                    print(f"✅ Login successful! Welcome, {user}.")
                    return True
                else:
                    print("❌ Incorrect Password.")
                    return False
        except Exception as e:
            print(f"Error reading save file: {e}")
            return False

    # --- SAVE / LOAD ---

    def generate_map(self):
        self.world_map = [[random.choice(BIOMES) for _ in range(MAP_SIZE)] for _ in range(MAP_SIZE)]
        self.world_map[2][2] = {"name": "Town Square", "theme": "Town", "desc": "A bustling safe haven with shops and an inn."}

    def save_game(self, verbose=True):
        if not self.save_filename: return
        
        data = {
            "meta": {
                "username": self.username,
                "password_hash": self.password_hash
            },
            "game_data": {
                "player": self.player.to_dict(),
                "turn_count": self.turn_count,
                "map": self.world_map,
                "void": self.void_gate_open
            }
        }
        with open(self.save_filename, "w") as f:
            json.dump(data, f)
        if verbose:
            print(f"💾 Game saved to '{self.save_filename}'.")

    def load_game_data(self):
        """Loads gameplay data into the active session."""
        if not self.save_filename or not os.path.exists(self.save_filename):
            return False
        
        with open(self.save_filename, "r") as f:
            full_data = json.load(f)
            game_data = full_data.get("game_data", {})
            
            if "player" in game_data:
                self.player.from_dict(game_data["player"])
                self.turn_count = game_data["turn_count"]
                self.world_map = game_data["map"]
                self.void_gate_open = game_data.get("void", False)
                return True
            return False

    # --- GAME MENUS ---

    def main_menu(self):
        while True:
            draw_ui(f"PROFILE: {self.username}", ["1. Continue Run", "2. Start New Run (Resets Progress)", "3. Logout"])
            c = input("> ").strip()
            
            if c == '1':
                if self.load_game_data():
                    self.running = True
                    self.main_loop()
                else:
                    print("No active run found. Please start a new run.")
            elif c == '2':
                confirm = input("Are you sure? This deletes your previous run! (y/n): ")
                if confirm.lower() == 'y':
                    self.setup_new_game()
            elif c == '3':
                print("Logging out...")
                break 

    def setup_new_game(self):
        self.player = Player() # Reset stats
        self.generate_map()    # Reset world
        self.turn_count = 0
        self.void_gate_open = False
        
        print("\n--- NEW CHARACTER ---")
        self.player.name = input("Enter Character Name: ")
        
        draw_ui("CHOOSE CLASS", [
            "1. Warrior (Starts with 140 HP)",
            "2. Rogue   (Starts with High Attack)",
            "3. Mage    (Starts with 80 MP)"
        ])
        c = input("> ")
        if c == '1':
            self.player.max_hp = 140
            self.player.hp = 140
            print("Selected Warrior.")
        elif c == '2':
            self.player.base_attack = 14
            print("Selected Rogue.")
        elif c == '3':
            self.player.max_mp = 80
            self.player.mp = 80
            print("Selected Mage.")
        
        self.running = True
        self.save_game(verbose=False) # Auto-save init state
        self.main_loop()

    # --- GAMEPLAY FEATURES ---

    def inventory_menu(self):
        while True:
            # Quest Info
            q_line = "No Active Quest"
            if self.player.active_quest:
                q = self.player.active_quest
                q_line = f"Quest: Kill {q['target']} ({q['progress']}/{q['count']})"

            lines = [
                f"Gold: {self.player.gold} | Lvl: {self.player.level}",
                f"HP: {self.player.hp}/{self.player.max_hp} | MP: {self.player.mp}/{self.player.max_mp}",
                f"Atk: {self.player.total_attack} | Def: {self.player.defense}",
                q_line,
                "-" * 56,
                f"1. HP Potion x{self.player.potions} (Restores 40 HP)",
                f"2. MP Potion x{self.player.mana_potions} (Restores 30 MP)",
                "-" * 56,
                f"Weapon: {self.player.equipped_weapon or 'None'}",
                f"Armor:  {self.player.equipped_armor or 'None'}",
                "-" * 56,
                "BACKPACK:"
            ]
            if not self.player.inventory:
                lines.append(" (Empty)")
            else:
                for item in self.player.inventory:
                    desc = ITEMS[item]['desc']
                    lines.append(f" - {item}: {desc}")
            
            draw_ui(f"INVENTORY OF {self.player.name}", lines)
            print("\nCommands: (1)Drink HP, (2)Drink MP, (e)quip [name], (x)exit")
            cmd = input("> ").strip().lower()
            
            if cmd == 'x': break
            elif cmd == '1': self.player.drink_potion()
            elif cmd == '2': self.player.drink_mana_potion()
            elif cmd.startswith('e '):
                item_name = input("Type item name exactly to equip: ") 
                if item_name in self.player.inventory:
                    itype = ITEMS[item_name]['type']
                    if itype == 'weapon': self.player.equipped_weapon = item_name
                    elif itype == 'armor': self.player.equipped_armor = item_name
                    print(f"✅ You equipped the {item_name}.")
                else:
                    print("❌ Item not found in your backpack.")

    def town_menu(self):
        # Temple Logic
        if "Temple" in self.player.town_upgrades:
            self.player.hp = self.player.max_hp
            self.player.mp = self.player.max_mp
            print("\n✨ The Temple priests tend to your wounds. Full HP/MP restored!")

        while True:
            b_str = ", ".join(self.player.town_upgrades) if self.player.town_upgrades else "None"
            draw_ui("TOWN SQUARE", [
                "1. Visit Shop",
                "2. Construct Buildings",
                "3. Rest at Inn (Save Game)",
                "4. Leave Town",
                f"Built: {b_str}"
            ])
            c = input("> ")
            if c == '1': self.shop_menu()
            elif c == '2': self.build_menu()
            elif c == '3':
                self.save_game()
                self.player.hp = min(self.player.max_hp, self.player.hp + 10)
                print("💤 You slept at the Inn. Game Saved.")
            elif c == '4': break

    def build_menu(self):
        while True:
            lines = [f"Current Gold: {self.player.gold}"]
            for b_name, data in BUILDINGS.items():
                status = "[OWNED]" if b_name in self.player.town_upgrades else f"{data['cost']} Gold"
                lines.append(f"{b_name}: {status} - {data['desc']}")
            draw_ui("CONSTRUCTION", lines)
            print("Type the name of the building to build, or 'x' to exit.")
            choice = input("> ").title()
            
            if choice == 'X': break
            if choice in BUILDINGS:
                if choice in self.player.town_upgrades:
                    print("❌ You already own this building.")
                elif self.player.gold >= BUILDINGS[choice]['cost']:
                    self.player.gold -= BUILDINGS[choice]['cost']
                    self.player.town_upgrades.append(choice)
                    print(f"🔨 Work is complete! You built the {choice}!")
                else:
                    print("❌ You don't have enough Gold.")

    def shop_menu(self):
        max_tier = 2 if "Blacksmith" in self.player.town_upgrades else 0
        while True:
            print(f"\nMerchant: 'Got some rare things on sale, stranger!' (Gold: {self.player.gold})")
            print("1. Health Potion (50g)")
            print("2. Mana Potion (60g)")
            print("--- EQUIPMENT ---")
            
            available_items = []
            for name, data in ITEMS.items():
                if data['tier'] <= max_tier:
                    print(f"- {name} ({data['cost']}g)")
                    available_items.append(name)
            
            print("(Type item name to buy, or 'x' to leave)")
            buy = input("> ")
            
            if buy == 'x': break
            elif buy == '1': 
                if self.player.gold >= 50:
                    self.player.gold -= 50
                    self.player.potions += 1
                    print("✅ Purchased Health Potion.")
                else: print("❌ Not enough gold.")
            elif buy == '2': 
                if self.player.gold >= 60:
                    self.player.gold -= 60
                    self.player.mana_potions += 1
                    print("✅ Purchased Mana Potion.")
                else: print("❌ Not enough gold.")
            elif buy in available_items:
                cost = ITEMS[buy]['cost']
                if self.player.gold >= cost:
                    self.player.gold -= cost
                    self.player.inventory.append(buy)
                    print(f"✅ You bought the {buy}!")
                else: print("❌ That is too expensive for you.")

    # --- MAIN LOOP ---

    def main_loop(self):
        while self.running and self.player.state == "alive":
            self.turn_count += 1
            
            # End Game Trigger
            if self.player.level >= 8 and not self.void_gate_open:
                self.void_gate_open = True
                draw_ui("⚠️ WARNING ⚠️", [
                    "The sky turns blood red...",
                    "The VOID GATE has opened at Coordinates (4,4)!",
                    "The Final Boss awaits your challenge."
                ])
                self.world_map[4][4] = {"name": "VOID GATE", "theme": "Boss", "desc": "The end of the world."}

            # Draw Map and Info
            tile = self.world_map[self.player.y][self.player.x]
            print("\n" + f" Turn {self.turn_count} ".center(60, "="))
            print(f" User: {self.username} | Char: {self.player.name} ".center(60))
            print(f" Location: {tile['name']} ({self.player.x},{self.player.y})".center(60))
            
            self.draw_mini_map()
            type_text(tile['desc'])
            
            print("\n[COMMANDS]")
            print("(n)orth, (s)outh, (e)ast, (w)est  - Move")
            print("(l)ook    - Explore the area (Fight/Loot)")
            print("(i)nventory - Check gear/Use potions")
            print("(m)enu    - Save/Quit")
            
            cmd = input("> ").lower().strip()

            if cmd in ['n','s','e','w']:
                self.move(cmd)
            elif cmd == 'l':
                self.explore(tile)
            elif cmd == 'i':
                self.inventory_menu()
            elif cmd == 'm': 
                c = input("1. Save Game  2. Quit to Main Menu > ")
                if c=='1': self.save_game()
                elif c=='2': self.running=False

        # Handle Death or Victory
        if self.player.state == "dead":
            draw_ui("GAME OVER", ["Your legend ends here.", "Try a new run?"])
            self.running = False
        elif self.player.state == "won":
            draw_ui("VICTORY!", ["You defeated the World Eater!", "The realm is safe.", "Thank you for playing!"])
            self.running = False

    def move(self, direction):
        dx, dy = 0, 0
        if direction == 'n': dy = -1
        elif direction == 's': dy = 1
        elif direction == 'e': dx = 1
        elif direction == 'w': dx = -1
        
        nx, ny = self.player.x + dx, self.player.y + dy
        if 0 <= nx < MAP_SIZE and 0 <= ny < MAP_SIZE:
            self.player.x, self.player.y = nx, ny
            # Ambush Chance
            if self.world_map[ny][nx]['theme'] != "Town" and random.random() < 0.25:
                print("\n⚠️ You are ambushed while travelling!")
                self.combat(self.world_map[ny][nx]['theme'])
        else:
            print("🚫 The path is blocked.")

    def explore(self, tile):
        theme = tile['theme']
        if theme == "Town":
            self.town_menu()
        elif theme == "Boss":
            self.final_boss()
        else:
            roll = random.random()
            # 15% Quest NPC
            if roll < 0.15: 
                self.npc_quest_event(theme)
            # 5% Roaming Boss
            elif roll < 0.20:
                print("\n⚠️ You feel a terrifying presence nearby...")
                boss_name = ROAMING_BOSSES[theme]
                self.combat(theme, boss_override=boss_name)
            # 50% Standard Combat
            elif roll < 0.70: 
                self.combat(theme)
            # 30% Loot
            else: 
                self.loot()

    def npc_quest_event(self, theme):
        if self.player.active_quest:
            print("\n🗣️ You see a survivor, but you are too busy with your current quest.")
            return
        
        target = random.choice(ENEMIES[theme])
        count = random.randint(2, 4)
        gold = count * 35
        xp = count * 25
        
        draw_ui("QUEST OFFER", [
            f"Survivor: 'Please help! The {target}s are destroying everything!'",
            f"Task: Hunt down {count} {target}s",
            f"Reward: {gold} Gold, {xp} XP"
        ])
        if input("Accept Quest? (y/n)> ") == 'y':
            self.player.active_quest = {'target': target, 'count': count, 'progress': 0, 'reward': gold, 'xp': xp}
            print("📜 Quest Accepted! Check your inventory to see progress.")

    def draw_mini_map(self):
        print("   " + " ".join([str(i) for i in range(MAP_SIZE)]))
        for y in range(MAP_SIZE):
            row = f"{y} "
            for x in range(MAP_SIZE):
                char = "[ ]"
                if x == self.player.x and y == self.player.y: char = "[P]"
                elif self.world_map[y][x]['theme'] == "Town": char = "[T]"
                elif self.world_map[y][x]['theme'] == "Boss": char = "[!]"
                row += char
            print(row)

    def combat(self, theme, boss_override=None):
        if boss_override:
            enemy = boss_override
            hp = 200
            atk = 25
            is_roaming_boss = True
        else:
            enemy = random.choice(ENEMIES.get(theme, ["Monster"]))
            hp = random.randint(30, 60) + (self.player.level * 10)
            atk = 10 + (self.player.level * 2)
            is_roaming_boss = False
        
        draw_ui("COMBAT STARTED", [f"Enemy: {enemy}", f"HP: {hp} | Atk: {atk}"])
        
        while hp > 0 and self.player.state == "alive":
            print(f"\nYOU: {self.player.hp} HP | {self.player.mp} MP")
            print("1. Attack  2. Magic  3. Inventory  4. Run")
            c = input("> ")
            
            dmg = 0
            if c == '1': 
                dmg = random.randint(self.player.total_attack-2, self.player.total_attack+2)
                print(f"⚔️ You strike the {enemy} for {dmg} damage!")
            elif c == '2':
                dmg = self.magic_menu()
                if dmg == -1: continue # Cancelled
            elif c == '3':
                self.inventory_menu()
                continue # Using item takes a "turn" in inventory menu logic, but let's loop back
            elif c == '4':
                if is_roaming_boss:
                    print("❌ You cannot run from a Boss!")
                    continue
                if random.random() > 0.5:
                    print("🏃 You managed to escape!")
                    return
                print("❌ Failed to escape!")
            
            # Enemy Turn
            hp -= dmg
            if hp > 0:
                edmg = max(1, random.randint(atk-3, atk+3) - self.player.defense)
                self.player.hp -= edmg
                print(f"🔥 The {enemy} attacks you for {edmg} damage!")
                if self.player.hp <= 0:
                    self.player.state = "dead"

        if self.player.state == "alive":
            gold = random.randint(20, 50)
            xp = 40
            if is_roaming_boss:
                gold *= 4
                xp *= 4
                print("🏆 ROAMING BOSS DEFEATED!")
            
            self.player.gold += gold
            self.player.gain_xp(xp)
            print(f"🏆 Victory! You found {gold} Gold and gained {xp} XP.")
            self.player.check_quest(enemy)

    def magic_menu(self):
        print("\n🔮 SPELLS:")
        has_tower = "Magic Tower" in self.player.town_upgrades
        for k, v in SPELLS.items():
            if k == "4" and not has_tower: continue
            print(f"{k}. {v['name']} ({v['cost']} MP): {v['desc']}")
        
        c = input("> ")
        if c in SPELLS:
            s = SPELLS[c]
            if c == "4" and not has_tower: return 0
            
            if self.player.mp >= s['cost']:
                self.player.mp -= s['cost']
                if 'heal' in s:
                    heal_amt = s['heal']
                    self.player.hp = min(self.player.max_hp, self.player.hp + heal_amt)
                    print(f"✨ You cast Holy Light and healed {heal_amt} HP!")
                    return 0
                else:
                    return int(self.player.total_attack * s['dmg_mult'])
            else:
                print("❌ Not enough Mana.")
                return -1
        return -1

    def loot(self):
        print("📦 You found a mysterious chest!")
        if input("Open it? (y/n)> ") == 'y':
            g = random.randint(30, 100)
            self.player.gold += g
            print(f"💰 Inside, you find {g} Gold!")

    def final_boss(self):
        draw_ui("THE FINAL BATTLE", [
            "THE WORLD EATER APPEARS!",
            "HP: 500 | Atk: 30",
            "This is the fight for your life."
        ])
        hp = 500
        atk = 30
        
        while hp > 0 and self.player.state == "alive":
            print(f"\nBOSS HP: {hp} | YOUR HP: {self.player.hp}")
            c = input("1. Attack  2. Magic  3. Inventory > ")
            dmg = 0
            
            if c == '1': dmg = self.player.total_attack
            elif c == '2': dmg = max(0, self.magic_menu())
            elif c == '3': self.inventory_menu(); continue
            
            hp -= dmg
            print(f"💥 You dealt {dmg} massive damage!")
            
            if hp > 0:
                hit = max(5, atk - self.player.defense)
                self.player.hp -= hit
                print(f"🔥 THE WORLD EATER SMASHES YOU for {hit} damage!")
                if self.player.hp <= 0:
                    self.player.state = "dead"
        
        if self.player.state == "alive":
            self.player.state = "won"

if __name__ == "__main__":
    g = Game()
    g.start_app()