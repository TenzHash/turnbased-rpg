import random
import time
import sys
import json
import os

# --- CONFIGURATION & DATA ---

MAP_SIZE = 5

BIOMES = [
    {"name": "Whispering Woods", "theme": "Fantasy", "desc": "Violet leaves fall around you."},
    {"name": "Neon Slums", "theme": "Sci-Fi", "desc": "Holographic ads flicker in the rain."},
    {"name": "Cursed Crypt", "theme": "Horror", "desc": "Fog rolls over ancient tombstones."},
    {"name": "Sunken Grotto", "theme": "Adventure", "desc": "The sound of rushing water echoes."}
]

ENEMIES = {
    "Fantasy": ["Goblin Scout", "Corrupted Wolf", "Bandit King"],
    "Sci-Fi": ["Rogue Drone", "Cyber-Punk", "Security Bot"],
    "Horror": ["Restless Spirit", "Zombie", "Vampire Fledgling"],
    "Adventure": ["Giant Crab", "Pirate", "Slime"]
}

# Added descriptions to items
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

SAVE_FILE = "rpg_save_v8.json"

# --- UI HELPERS ---

def draw_ui(title, lines):
    """Draws a neat box around text."""
    width = 60
    print("\n" + "╔" + "═" * width + "╗")
    print(f"║ {title.center(width-2)} ║")
    print("╠" + "═" * width + "╣")
    for line in lines:
        print(f"║ {line.ljust(width-2)} ║")
    print("╚" + "═" * width + "╝")

def type_text(text, speed=0.02):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(speed)
    print()

# --- CLASSES ---

class Player:
    def __init__(self):
        self.name = "Hero"
        self.state = "alive"
        self.hp = 100; self.max_hp = 100
        self.mp = 40; self.max_mp = 40
        self.base_attack = 10
        self.gold = 100
        self.xp = 0; self.level = 1; self.xp_to_next_level = 100
        self.potions = 2
        self.mana_potions = 2
        self.inventory = [] 
        self.equipped_weapon = None
        self.equipped_armor = None
        self.active_quest = None
        self.town_upgrades = [] # List of built buildings
        self.x = 2; self.y = 2

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
            print(f"   🧪 Glug... HP restored to {self.hp}/{self.max_hp}.")
        else:
            print("   ❌ You have no Health Potions.")

    def drink_mana_potion(self):
        if self.mana_potions > 0:
            self.mp = min(self.max_mp, self.mp + 30)
            self.mana_potions -= 1
            print(f"   🧪 Glug... MP restored to {self.mp}/{self.max_mp}.")
        else:
            print("   ❌ You have no Mana Potions.")

    def gain_xp(self, amount):
        self.xp += amount
        if self.xp >= self.xp_to_next_level:
            self.level_up()

    def level_up(self):
        self.xp -= self.xp_to_next_level
        self.level += 1
        self.xp_to_next_level = int(self.xp_to_next_level * 1.5)
        self.max_hp += 20; self.max_mp += 10
        self.hp = self.max_hp; self.mp = self.max_mp
        self.base_attack += 3
        draw_ui("LEVEL UP!", [f"You are now Level {self.level}!", f"Stats increased.", f"HP/MP Fully Restored."])

    def to_dict(self): return self.__dict__
    def from_dict(self, data):
        for k, v in data.items(): setattr(self, k, v)
        # Defaults
        if not hasattr(self, 'town_upgrades'): self.town_upgrades = []

class Game:
    def __init__(self):
        self.player = Player()
        self.running = True
        self.turn_count = 0
        self.world_map = []
        self.generate_map()
        self.void_gate_open = False

    def generate_map(self):
        self.world_map = [[random.choice(BIOMES) for _ in range(MAP_SIZE)] for _ in range(MAP_SIZE)]
        self.world_map[2][2] = {"name": "Town Square", "theme": "Town", "desc": "Home base."}

    def save_game(self):
        data = {"player": self.player.to_dict(), "turn_count": self.turn_count, "map": self.world_map, "void": self.void_gate_open}
        with open(SAVE_FILE, "w") as f: json.dump(data, f)
        print("💾 Game Saved.")

    def load_game(self):
        if not os.path.exists(SAVE_FILE): print("❌ No save found."); return False
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
            self.player.from_dict(data["player"])
            self.turn_count = data["turn_count"]
            self.world_map = data["map"]
            self.void_gate_open = data.get("void", False)
        return True

    # --- INVENTORY SYSTEM (UPDATED) ---
    def inventory_menu(self):
        while True:
            lines = [
                f"Gold: {self.player.gold} | Lvl: {self.player.level}",
                f"HP: {self.player.hp}/{self.player.max_hp} | MP: {self.player.mp}/{self.player.max_mp}",
                f"Atk: {self.player.total_attack} | Def: {self.player.defense}",
                "-" * 56,
                "CONSUMABLES:",
                f"1. Health Potion x{self.player.potions} (Restores 40 HP)",
                f"2. Mana Potion x{self.player.mana_potions} (Restores 30 MP)",
                "-" * 56,
                "EQUIPPED:",
                f"Weapon: {self.player.equipped_weapon or 'None'}",
                f"Armor:  {self.player.equipped_armor or 'None'}",
                "-" * 56,
                "BACKPACK:"
            ]
            if not self.player.inventory: lines.append(" (Empty)")
            else:
                for item in self.player.inventory:
                    desc = ITEMS[item]['desc']
                    lines.append(f" - {item}: {desc}")
            
            draw_ui(f"{self.player.name}'s Inventory", lines)
            
            print("\nCommands: (1)Drink HP, (2)Drink MP, (e)quip [name], (x)exit")
            cmd = input("> ").strip().lower()
            
            if cmd == 'x': break
            elif cmd == '1': self.player.drink_potion()
            elif cmd == '2': self.player.drink_mana_potion()
            elif cmd.startswith('e '):
                item_name = input("Type item name exactly: ") # Simplified input for text parsing
                if item_name in self.player.inventory:
                    itype = ITEMS[item_name]['type']
                    if itype == 'weapon': self.player.equipped_weapon = item_name
                    elif itype == 'armor': self.player.equipped_armor = item_name
                    print(f"✅ Equipped {item_name}.")
                else: print("❌ Item not in backpack.")
            else: print("Unknown command.")

    # --- TOWN BUILDING SYSTEM ---
    def town_menu(self):
        # Auto-heal if Temple is built
        if "Temple" in self.player.town_upgrades:
            self.player.hp = self.player.max_hp
            self.player.mp = self.player.max_mp
            print("\n✨ The Temple priests fully restored your health!")

        while True:
            buildings_str = ", ".join(self.player.town_upgrades) if self.player.town_upgrades else "None"
            draw_ui("TOWN SQUARE", [
                "1. Visit Shop",
                "2. Build / Upgrade",
                "3. Rest (Save Game)",
                "4. Leave Town",
                f"Built: {buildings_str}"
            ])
            
            c = input("> ")
            if c == '1': self.shop_menu()
            elif c == '2': self.build_menu()
            elif c == '3': self.save_game(); self.player.hp = min(self.player.max_hp, self.player.hp + 10); print("You rested.")
            elif c == '4': break

    def build_menu(self):
        while True:
            lines = [f"Gold: {self.player.gold}"]
            opts = []
            for b_name, data in BUILDINGS.items():
                status = "[OWNED]" if b_name in self.player.town_upgrades else f"{data['cost']}g"
                lines.append(f"{b_name}: {status} - {data['desc']}")
                opts.append(b_name.lower())
            
            draw_ui("CONSTRUCTION", lines)
            print("Type building name to build, or 'x' to exit.")
            choice = input("> ").title() # capitalize input
            
            if choice == 'X': break
            if choice in BUILDINGS:
                if choice in self.player.town_upgrades:
                    print("❌ Already built!")
                elif self.player.gold >= BUILDINGS[choice]['cost']:
                    self.player.gold -= BUILDINGS[choice]['cost']
                    self.player.town_upgrades.append(choice)
                    print(f"🔨 Constructed {choice}!")
                else:
                    print("❌ Not enough gold.")

    def shop_menu(self):
        print("\nMerchant: 'Welcome!'")
        # Check Blacksmith upgrade
        max_tier = 2 if "Blacksmith" in self.player.town_upgrades else 0
        
        while True:
            print(f"\nGold: {self.player.gold}")
            print("1. HP Potion (50g)")
            print("2. MP Potion (60g)")
            print("--- EQUIPMENT ---")
            available_items = []
            for name, data in ITEMS.items():
                if data['tier'] <= max_tier:
                    print(f"- {name} ({data['cost']}g) : {data['desc']}")
                    available_items.append(name)
            
            print("(Type item name to buy, or 'x' to exit)")
            buy = input("> ")
            
            if buy == 'x': break
            elif buy == '1': 
                if self.player.gold >= 50: self.player.gold-=50; self.player.potions+=1; print("Bought HP Potion.")
            elif buy == '2': 
                if self.player.gold >= 60: self.player.gold-=60; self.player.mana_potions+=1; print("Bought MP Potion.")
            elif buy in available_items:
                cost = ITEMS[buy]['cost']
                if self.player.gold >= cost:
                    self.player.gold -= cost
                    self.player.inventory.append(buy)
                    print(f"✅ Bought {buy}!")
                else: print("❌ Too expensive.")

    # --- MAIN LOOP & EVENTS ---
    
    def main_loop(self):
        while self.running and self.player.state == "alive":
            self.turn_count += 1
            
            # End Game Trigger
            if self.player.level >= 8 and not self.void_gate_open:
                self.void_gate_open = True
                draw_ui("⚠️ WARNING ⚠️", ["The sky turns red...", "The VOID GATE has opened at Coordinates (4,4)!", "The Final Boss awaits."])
                self.world_map[4][4] = {"name": "VOID GATE", "theme": "Boss", "desc": "The end of the world."}

            # Map Draw
            tile = self.world_map[self.player.y][self.player.x]
            print("\n" + f" Turn {self.turn_count} ".center(60, "="))
            print(f" Loc: {tile['name']} ({self.player.x},{self.player.y})".center(60))
            self.draw_mini_map()
            type_text(tile['desc'])
            
            # Action Menu
            print("\nCommands: (n/s/e/w)Move, (l)ook, (i)nventory, (m)enu")
            cmd = input("> ").lower().strip()

            if cmd in ['n','s','e','w']: self.move(cmd)
            elif cmd == 'l': self.explore(tile)
            elif cmd == 'i': self.inventory_menu()
            elif cmd == 'm': 
                c = input("1.Save 2.Quit > ")
                if c=='1': self.save_game()
                elif c=='2': self.running=False
            
        if self.player.state == "dead":
            draw_ui("GAME OVER", ["Your legend ends here."])
        elif self.player.state == "won":
            draw_ui("VICTORY!", ["You defeated the World Eater!", "Peace returns to the land.", "Thank you for playing!"])

    def move(self, direction):
        dx, dy = 0, 0
        if direction == 'n': dy = -1
        elif direction == 's': dy = 1
        elif direction == 'e': dx = 1
        elif direction == 'w': dx = -1
        
        nx, ny = self.player.x + dx, self.player.y + dy
        if 0 <= nx < MAP_SIZE and 0 <= ny < MAP_SIZE:
            self.player.x, self.player.y = nx, ny
            # Encounter chance (0% in Town)
            if self.world_map[ny][nx]['theme'] != "Town" and random.random() < 0.25:
                self.combat(self.world_map[ny][nx]['theme'])
        else: print("🚫 Blocked.")

    def explore(self, tile):
        if tile['theme'] == "Town": self.town_menu()
        elif tile['theme'] == "Boss": self.final_boss()
        else:
            r = random.random()
            if r < 0.6: self.combat(tile['theme'])
            else: self.loot()

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

    def combat(self, theme):
        enemy = random.choice(ENEMIES.get(theme, ["Monster"]))
        hp = random.randint(30, 60) + (self.player.level * 10)
        atk = 10 + (self.player.level * 2)
        
        draw_ui("COMBAT STARTED", [f"Enemy: {enemy}", f"HP: {hp} | Atk: {atk}"])
        
        while hp > 0 and self.player.state == "alive":
            print(f"\nYOU: {self.player.hp} HP | {self.player.mp} MP")
            print("1.Attack  2.Magic  3.Item  4.Run")
            c = input("> ")
            
            dmg = 0
            if c == '1': 
                dmg = random.randint(self.player.total_attack-2, self.player.total_attack+2)
                print(f"⚔️ You hit for {dmg}!")
            elif c == '2':
                dmg = self.magic_menu()
                if dmg == -1: continue # Cancelled
            elif c == '3':
                self.inventory_menu() # Open full inventory
                continue # Skip enemy turn if just viewing? No, let's say using item takes turn.
                # Simplified: Inventory handles usage, but we need to track if action was taken.
                # For this version, opening inventory is "free" but using potion inside it is instant.
            elif c == '4':
                if random.random() > 0.5: print("🏃 Escaped!"); return
                print("❌ Failed to run!")
            
            hp -= dmg
            if hp > 0:
                edmg = max(1, random.randint(atk-3, atk+3) - self.player.defense)
                self.player.hp -= edmg
                print(f"🔻 Enemy hit you for {edmg}.")
                if self.player.hp <= 0: self.player.state = "dead"

        if self.player.state == "alive":
            gold = random.randint(20, 50)
            self.player.gold += gold
            self.player.gain_xp(40)
            print(f"🏆 Won! +{gold}g")

    def magic_menu(self):
        print("\n🔮 SPELLS:")
        has_tower = "Magic Tower" in self.player.town_upgrades
        for k, v in SPELLS.items():
            if k == "4" and not has_tower: continue # Skip ult if no tower
            print(f"{k}. {v['name']} ({v['cost']} MP): {v['desc']}")
        c = input("> ")
        if c in SPELLS:
            s = SPELLS[c]
            if c == "4" and not has_tower: return 0
            if self.player.mp >= s['cost']:
                self.player.mp -= s['cost']
                if 'heal' in s: 
                    self.player.hp = min(self.player.max_hp, self.player.hp + s['heal'])
                    print("✨ Healed!"); return 0
                else: return int(self.player.total_attack * s['dmg_mult'])
            else: print("❌ Low Mana."); return -1
        return -1

    def loot(self):
        print("📦 Found a chest!")
        if input("Open? (y/n)> ") == 'y':
            g = random.randint(30, 100)
            self.player.gold += g
            print(f"💰 Found {g} Gold.")

    def final_boss(self):
        draw_ui("THE FINAL BATTLE", ["THE WORLD EATER APPEARS!", "HP: 500 | Atk: 30", "Defeat him to save the world!"])
        hp = 500
        atk = 30
        while hp > 0 and self.player.state == "alive":
            print(f"\nBOSS HP: {hp} | YOUR HP: {self.player.hp}")
            c = input("1.Attack 2.Magic 3.Inv > ")
            dmg = 0
            if c == '1': dmg = self.player.total_attack
            elif c == '2': dmg = max(0, self.magic_menu())
            elif c == '3': self.inventory_menu(); continue
            
            hp -= dmg
            print(f"💥 You dealt {dmg} damage!")
            
            if hp > 0:
                hit = max(5, atk - self.player.defense)
                self.player.hp -= hit
                print(f"🔥 BOSS ATTACKS for {hit} damage!")
                if self.player.hp <= 0: self.player.state = "dead"
        
        if self.player.state == "alive":
            self.player.state = "won"

    def setup_new_game(self):
        self.player.name = input("Enter Name: ")
        self.main_loop()

if __name__ == "__main__":
    g = Game()
    g.setup_new_game()