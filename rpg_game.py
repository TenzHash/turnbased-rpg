import random
import time
import sys
import json
import os

# --- CONFIGURATION & DATA ---

# Biome Templates
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

BOSSES = {
    "Fantasy": {"name": "Elder Dragon", "hp": 150, "atk": 20, "xp": 100},
    "Sci-Fi": {"name": "Mecha-Titan", "hp": 160, "atk": 18, "xp": 110},
    "Horror": {"name": "Lich Lord", "hp": 140, "atk": 22, "xp": 120},
    "Adventure": {"name": "Kraken", "hp": 180, "atk": 15, "xp": 130}
}

ITEMS = {
    "Iron Sword": {"type": "weapon", "value": 5, "cost": 50},
    "Plasma Rifle": {"type": "weapon", "value": 10, "cost": 120},
    "Demon Blade": {"type": "weapon", "value": 15, "cost": 250},
    "Leather Armor": {"type": "armor", "value": 2, "cost": 40},
    "Nano-Suit": {"type": "armor", "value": 5, "cost": 100},
    "Dragon Plate": {"type": "armor", "value": 8, "cost": 300}
}

SPELLS = {
    "1": {"name": "Fireball", "cost": 12, "dmg_mult": 2.5, "desc": "Huge Damage"},
    "2": {"name": "Lightning", "cost": 8, "dmg_mult": 1.5, "desc": "Reliable Hit"},
    "3": {"name": "Holy Light", "cost": 15, "heal": 60, "desc": "Restores HP"}
}

SAVE_FILE = "rpg_save.json"
MAP_SIZE = 5

# --- CLASSES ---

class Player:
    def __init__(self):
        self.name = ""
        self.state = "alive"
        self.hp = 100; self.max_hp = 100
        self.mp = 40; self.max_mp = 40
        self.base_attack = 10
        self.gold = 50
        self.xp = 0; self.level = 1; self.xp_to_next_level = 100
        self.potions = 1; self.mana_potions = 1
        self.inventory = [] 
        self.equipped_weapon = None; self.equipped_armor = None
        self.active_quest = None
        # NEW: Coordinates
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
            self.hp = min(self.max_hp, self.hp + 30); self.potions -= 1
            print(f"🧪 HP: {self.hp}/{self.max_hp}")
        else: print("❌ No HP Potions!")

    def drink_mana_potion(self):
        if self.mana_potions > 0:
            self.mp = min(self.max_mp, self.mp + 20); self.mana_potions -= 1
            print(f"🧪 MP: {self.mp}/{self.max_mp}")
        else: print("❌ No MP Potions!")

    def take_damage(self, dmg):
        actual_dmg = max(1, dmg - self.defense)
        self.hp -= actual_dmg
        if self.hp <= 0: self.hp = 0; self.state = "dead"
        print(f"   🔻 Took {actual_dmg} dmg. HP: {self.hp}/{self.max_hp}")

    def gain_xp(self, amount):
        self.xp += amount
        if self.xp >= self.xp_to_next_level: self.level_up()

    def level_up(self):
        self.xp -= self.xp_to_next_level
        self.level += 1; self.xp_to_next_level = int(self.xp_to_next_level * 1.5)
        self.max_hp += 20; self.max_mp += 10
        self.hp = self.max_hp; self.mp = self.max_mp; self.base_attack += 3
        print(f"\n🌟 LEVEL UP! Now Level {self.level}!")

    def check_quest(self, enemy_name):
        if self.active_quest and self.active_quest['target'] == enemy_name:
            self.active_quest['progress'] += 1
            print(f"   📜 Quest: {self.active_quest['progress']}/{self.active_quest['count']}")
            if self.active_quest['progress'] >= self.active_quest['count']:
                print(f"🎉 QUEST COMPLETE! +{self.active_quest['reward']} Gold, +{self.active_quest['xp']} XP")
                self.gold += self.active_quest['reward']
                self.gain_xp(self.active_quest['xp'])
                self.active_quest = None

    def to_dict(self): return self.__dict__
    
    def from_dict(self, data):
        for k, v in data.items(): setattr(self, k, v)
        if not hasattr(self, 'x'): self.x = 2
        if not hasattr(self, 'y'): self.y = 2

class Game:
    def __init__(self):
        self.player = Player()
        self.running = True
        self.turn_count = 0
        # NEW: Map Generation
        self.world_map = [] 
        self.generate_map()

    def generate_map(self):
        # Create a 5x5 grid of random biomes
        self.world_map = [[random.choice(BIOMES) for _ in range(MAP_SIZE)] for _ in range(MAP_SIZE)]
        # Force center to be a Safe Zone/Shop
        self.world_map[2][2] = {"name": "Town Square", "theme": "Shop", "desc": "A safe place to rest and trade."}

    def type_text(self, text, speed=0.03):
        for char in text:
            sys.stdout.write(char); sys.stdout.flush(); time.sleep(speed)
        print()

    def get_input(self, choices):
        while True:
            c = input(f"\n> Choose ({'/'.join(choices)}): ").lower().strip()
            if c in choices: return c
            print("Invalid choice.")

    # --- SAVE SYSTEM UPDATED FOR MAP ---
    def save_game(self):
        data = {
            "player": self.player.to_dict(),
            "turn_count": self.turn_count,
            "world_map": self.world_map
        }
        with open(SAVE_FILE, "w") as f: json.dump(data, f)
        print("\n💾 Game Saved!")

    def load_game(self):
        if not os.path.exists(SAVE_FILE): print("\n❌ No save found!"); return False
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
            self.player.from_dict(data["player"])
            self.turn_count = data["turn_count"]
            self.world_map = data.get("world_map", [])
            if not self.world_map: self.generate_map() # Safety for old saves
        print(f"\n📂 Save loaded!"); return True

    # --- DISPLAY & NAVIGATION ---
    def draw_map(self):
        print(f"\n🗺️  WORLD MAP ({self.player.x}, {self.player.y})")
        print("   " + " ".join([str(i) for i in range(MAP_SIZE)]))
        for y in range(MAP_SIZE):
            row = f"{y} "
            for x in range(MAP_SIZE):
                if x == self.player.x and y == self.player.y:
                    row += "[P]" # Player
                elif self.world_map[y][x]['theme'] == "Shop":
                    row += "[S]" # Shop
                else:
                    row += "[ ]"
            print(row)

    def main_menu(self):
        self.type_text("=== RPG v7.0: WORLD EXPLORER ===")
        print("1. New Game"); print("2. Load Game")
        if self.get_input(['1', '2']) == '2':
            if self.load_game(): self.main_loop()
            else: self.setup_new_game()
        else: self.setup_new_game()

    def setup_new_game(self):
        self.player.name = input("\nEnter name: ")
        print("1. Warrior (HP) | 2. Rogue (Atk) | 3. Mage (MP)")
        c = self.get_input(['1', '2', '3'])
        if c == '1': self.player.max_hp = 130; self.player.hp = 130
        elif c == '2': self.player.base_attack = 14
        elif c == '3': self.player.max_mp = 70; self.player.mp = 70
        self.main_loop()

    # --- CORE LOOP ---
    def main_loop(self):
        while self.running and self.player.state == "alive":
            self.turn_count += 1
            
            # 1. Show Status and Map
            current_tile = self.world_map[self.player.y][self.player.x]
            print("\n" + "="*50)
            q_str = f"| Quest: {self.player.active_quest['target']} " if self.player.active_quest else ""
            print(f"TURN {self.turn_count} | {current_tile['name']} | HP:{self.player.hp} {q_str}")
            self.draw_map()
            self.type_text(current_tile['desc'])

            # 2. Boss Check (Time Based)
            if self.turn_count % 10 == 0: # Slower boss spawn in map mode
                self.boss_event(current_tile['theme'])
                continue

            # 3. Player Action
            print("\n[COMMANDS]")
            print("move: n/s/e/w (Travel)")
            print("look: Search area (Fight/Loot)")
            print("menu: inv/save/quit")
            
            action = input("> ").lower().strip()

            if action in ['n', 'north']: self.move(0, -1)
            elif action in ['s', 'south']: self.move(0, 1)
            elif action in ['e', 'east']: self.move(1, 0)
            elif action in ['w', 'west']: self.move(-1, 0)
            elif action == 'look': self.explore_event(current_tile)
            elif action == 'inv': self.inventory_menu()
            elif action == 'save': self.save_game()
            elif action == 'quit': self.running = False
            else: print("Unknown command.")

        if self.player.state == "dead": self.type_text("\n💀 GAME OVER.")

    def move(self, dx, dy):
        nx, ny = self.player.x + dx, self.player.y + dy
        if 0 <= nx < MAP_SIZE and 0 <= ny < MAP_SIZE:
            self.player.x = nx
            self.player.y = ny
            # 20% chance of ambush when moving
            if random.random() < 0.2:
                print("⚠️ Ambush while travelling!")
                tile = self.world_map[ny][nx]
                if tile['theme'] != "Shop":
                    self.combat_event(tile['theme'])
        else:
            print("🚫 You cannot go that way.")

    def explore_event(self, tile):
        if tile['theme'] == "Shop":
            self.shop_event()
        else:
            roll = random.random()
            if roll < 0.1: self.npc_quest_event(tile['theme'])
            elif roll < 0.7: self.combat_event(tile['theme'])
            else: self.loot_event()

    # --- EVENTS (Abbreviated from v6 logic) ---
    def npc_quest_event(self, theme):
        if self.player.active_quest: print("You see a survivor."); return
        t = random.choice(ENEMIES[theme])
        print(f"🗣️ NPC: 'Kill 3 {t}s for me?' (y/n)")
        if input("> ") == 'y':
            self.player.active_quest = {'target': t, 'count': 3, 'progress': 0, 'reward': 150, 'xp': 100}
            print("📜 Quest Accepted!")

    def shop_event(self):
        print("\n🏪 SHOP: 1.HP(50g) 2.MP(60g) 3.Gear x.Exit")
        c = input("> ")
        if c=='1' and self.player.gold>=50: self.player.gold-=50; self.player.potions+=1; print("Bought HP.")
        elif c=='2' and self.player.gold>=60: self.player.gold-=60; self.player.mana_potions+=1; print("Bought MP.")
        elif c=='3':
             for i, d in ITEMS.items(): print(f"{i} ({d['cost']}g)")
             b = input("Name > ")
             if b in ITEMS and self.player.gold>=ITEMS[b]['cost']: 
                 self.player.gold-=ITEMS[b]['cost']; self.player.inventory.append(b); print("Bought!")

    def loot_event(self):
        print("📦 You found a chest! (open/leave)")
        if input("> ") == 'open':
            if random.random()>0.3: g=random.randint(20,50); self.player.gold+=g; print(f"Found {g}g.")
            else: self.player.take_damage(10); print("Trap!")

    def boss_event(self, theme):
        if theme == "Shop": return
        b = BOSSES[theme]
        print(f"\n⚠️ BOSS: {b['name']}!")
        self.battle_logic(b['name'], b['hp'], b['atk'], b['xp'], True)

    def combat_event(self, theme):
        e = random.choice(ENEMIES[theme])
        self.battle_logic(e, random.randint(30,60), 10, 30)

    def battle_logic(self, name, hp, atk, xp, is_boss=False):
        print(f"⚔️ FIGHT: {name} (HP:{hp})")
        while hp>0 and self.player.state=="alive":
            print(f"HP:{self.player.hp} MP:{self.player.mp}")
            a = self.get_input(['attack', 'magic', 'potion', 'run']) if not is_boss else self.get_input(['attack', 'magic', 'potion'])
            dmg = 0
            if a=='attack': dmg=random.randint(self.player.total_attack-2, self.player.total_attack+2); print(f"Hit {dmg}")
            elif a=='magic': 
                for k,v in SPELLS.items(): print(f"{k}.{v['name']} ({v['cost']}MP)")
                c=input("Spell> ")
                if c in SPELLS and self.player.mp>=SPELLS[c]['cost']:
                    self.player.mp-=SPELLS[c]['cost']; 
                    if c=='3': self.player.hp+=60; print("Healed.")
                    else: dmg=int(self.player.total_attack*SPELLS[c]['dmg_mult']); print(f"Blast {dmg}")
            elif a=='potion': self.player.drink_potion()
            elif a=='run': 
                 if random.random()>0.5: print("Escaped!"); return
                 print("Failed run.")
            
            hp -= dmg
            if hp > 0: self.player.take_damage(random.randint(atk-3, atk+3))
        
        if self.player.state=="alive":
             self.player.gold += 50
             self.player.gain_xp(xp)
             self.player.check_quest(name)
             print("Victory!")

    def inventory_menu(self):
        print(f"🎒 Inv: {', '.join(self.player.inventory)}")
        # Simple equip logic can be added here as per previous versions

if __name__ == "__main__":
    game = Game()
    game.main_menu()