import random
import time
import sys
import json
import os

# --- CONFIGURATION & DATA ---

LOCATIONS = [
    {"name": "The Whispering Woods", "theme": "Fantasy", "desc": "Trees with violet leaves whisper secrets."},
    {"name": "Sector 7 Slums", "theme": "Sci-Fi", "desc": "Neon lights flicker over wet pavement."},
    {"name": "The Cursed Crypt", "theme": "Horror", "desc": "The air is cold and smells of stale dust."},
    {"name": "The Sunken Grotto", "theme": "Adventure", "desc": "Water drips from glowing stalactites."}
]

ENEMIES = {
    "Fantasy": ["Goblin Scout", "Corrupted Wolf", "Bandit King"],
    "Sci-Fi": ["Rogue Drone", "Cyber-Punk", "Security Bot"],
    "Horror": ["Restless Spirit", "Zombie", "Vampire Fledgling"],
    "Adventure": ["Giant Crab", "Pirate", "Slime"]
}

BOSSES = {
    "Fantasy": {"name": "Elder Dragon", "hp": 80, "atk": 20, "xp": 100},
    "Sci-Fi": {"name": "Mecha-Titan", "hp": 90, "atk": 18, "xp": 110},
    "Horror": {"name": "Lich Lord", "hp": 75, "atk": 22, "xp": 120},
    "Adventure": {"name": "Kraken", "hp": 100, "atk": 15, "xp": 130}
}

ITEMS = {
    "Iron Sword": {"type": "weapon", "value": 5, "cost": 50},
    "Plasma Rifle": {"type": "weapon", "value": 10, "cost": 120},
    "Demon Blade": {"type": "weapon", "value": 15, "cost": 250},
    "Leather Armor": {"type": "armor", "value": 2, "cost": 40},
    "Nano-Suit": {"type": "armor", "value": 5, "cost": 100},
    "Dragon Plate": {"type": "armor", "value": 8, "cost": 300}
}

SAVE_FILE = "rpg_save.json"

# --- CLASSES ---

class Player:
    def __init__(self):
        self.name = ""
        self.hp = 100
        self.max_hp = 100
        self.base_attack = 10
        self.potions = 1
        self.gold = 50
        self.state = "alive"
        # Inventory
        self.inventory = [] 
        self.equipped_weapon = None
        self.equipped_armor = None
        # NEW: Progression Stats
        self.xp = 0
        self.level = 1
        self.xp_to_next_level = 100

    @property
    def total_attack(self):
        bonus = ITEMS[self.equipped_weapon]['value'] if self.equipped_weapon else 0
        return self.base_attack + bonus

    @property
    def defense(self):
        return ITEMS[self.equipped_armor]['value'] if self.equipped_armor else 0

    def heal(self):
        if self.potions > 0:
            heal_amount = 30
            self.hp = min(self.max_hp, self.hp + heal_amount)
            self.potions -= 1
            print(f"\n✨ You drank a potion! HP restored to {self.hp}/{self.max_hp}.")
        else:
            print("\n❌ You are out of potions!")

    def take_damage(self, dmg):
        actual_dmg = max(1, dmg - self.defense)
        self.hp -= actual_dmg
        if self.hp <= 0:
            self.hp = 0
            self.state = "dead"
        print(f"   You took {actual_dmg} damage (reduced by {self.defense})! HP: {self.hp}/{self.max_hp}")

    # NEW: XP Handling
    def gain_xp(self, amount):
        self.xp += amount
        print(f"   ✨ Gained {amount} XP! ({self.xp}/{self.xp_to_next_level})")
        
        while self.xp >= self.xp_to_next_level:
            self.level_up()

    def level_up(self):
        self.xp -= self.xp_to_next_level
        self.level += 1
        self.xp_to_next_level = int(self.xp_to_next_level * 1.5) # Harder to level up each time
        
        # Stat boosts
        self.max_hp += 20
        self.hp = self.max_hp # Full heal on level up
        self.base_attack += 3
        
        print(f"\n🌟🌟 LEVEL UP! You are now Level {self.level}! 🌟🌟")
        print(f"   Max HP increased to {self.max_hp}")
        print(f"   Base Attack increased to {self.base_attack}")
        print(f"   Health fully restored!")

    def to_dict(self):
        return {
            "name": self.name,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "base_attack": self.base_attack,
            "potions": self.potions,
            "gold": self.gold,
            "inventory": self.inventory,
            "equipped_weapon": self.equipped_weapon,
            "equipped_armor": self.equipped_armor,
            "xp": self.xp,
            "level": self.level,
            "xp_to_next_level": self.xp_to_next_level
        }

    def from_dict(self, data):
        self.name = data["name"]
        self.hp = data["hp"]
        self.max_hp = data["max_hp"]
        self.base_attack = data["base_attack"]
        self.potions = data["potions"]
        self.gold = data["gold"]
        self.inventory = data.get("inventory", [])
        self.equipped_weapon = data.get("equipped_weapon", None)
        self.equipped_armor = data.get("equipped_armor", None)
        # Use .get() for backwards compatibility with old saves
        self.xp = data.get("xp", 0)
        self.level = data.get("level", 1)
        self.xp_to_next_level = data.get("xp_to_next_level", 100)

class Game:
    def __init__(self):
        self.player = Player()
        self.running = True
        self.turn_count = 0

    def type_text(self, text, speed=0.03):
        for char in text:
            sys.stdout.write(char)
            sys.stdout.flush()
            time.sleep(speed)
        print()

    def get_input(self, choices):
        while True:
            choice = input(f"\n> Choose ({'/'.join(choices)}): ").lower().strip()
            if choice in choices:
                return choice
            print("Invalid choice. Try again.")

    def save_game(self):
        data = {"player": self.player.to_dict(), "turn_count": self.turn_count}
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)
        print("\n💾 Game Saved!")

    def load_game(self):
        if not os.path.exists(SAVE_FILE):
            print("\n❌ No save file found!")
            return False
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
            self.player.from_dict(data["player"])
            self.turn_count = data["turn_count"]
        print(f"\n📂 Save loaded! Welcome back, {self.player.name} (Lvl {self.player.level}).")
        return True

    def main_menu(self):
        self.type_text("=== RANDOM RPG v4.0 (ASCENSION UPDATE) ===")
        print("1. New Game")
        print("2. Load Game")
        c = self.get_input(['1', '2'])
        if c == '2':
            if self.load_game():
                self.main_loop()
            else:
                self.setup_new_game()
        else:
            self.setup_new_game()

    def setup_new_game(self):
        self.player.name = input("\nEnter your hero's name: ")
        print("\nChoose your Class:")
        print("1. Warrior (High HP)")
        print("2. Rogue (High Attack)")
        c = self.get_input(['1', '2'])
        if c == '1':
            self.player.max_hp = 120
            self.player.hp = 120
            self.player.base_attack = 12
        else:
            self.player.base_attack = 18
            self.player.potions = 2
        self.main_loop()

    def inventory_menu(self):
        print(f"\n🎒 --- {self.player.name} (Lvl {self.player.level}) ---")
        print(f"XP: {self.player.xp}/{self.player.xp_to_next_level}")
        print(f"Gold: {self.player.gold}")
        print(f"Stats: {self.player.total_attack} ATK | {self.player.defense} DEF")
        print("Items:", ", ".join(self.player.inventory) if self.player.inventory else "Empty")
        
        equippables = [i for i in self.player.inventory]
        if equippables:
            print("\nTo equip item, type number. To exit, type 'x'.")
            for idx, item in enumerate(equippables):
                print(f"{idx+1}. {item} ({ITEMS[item]['type'].upper()})")
            
            choice = input("> ")
            if choice.isdigit() and 1 <= int(choice) <= len(equippables):
                item_name = equippables[int(choice)-1]
                if ITEMS[item_name]['type'] == 'weapon':
                    self.player.equipped_weapon = item_name
                elif ITEMS[item_name]['type'] == 'armor':
                    self.player.equipped_armor = item_name
                print(f"✅ Equipped {item_name}!")

    def shop_event(self):
        self.type_text("\n🏪 A Merchant has set up camp.")
        while True:
            print(f"\nGold: {self.player.gold}")
            print("0. Buy Potion (50g)")
            shop_items = list(ITEMS.keys())
            for idx, item in enumerate(shop_items):
                stats = f"Atk+{ITEMS[item]['value']}" if ITEMS[item]['type'] == 'weapon' else f"Def+{ITEMS[item]['value']}"
                print(f"{idx+1}. {item} ({stats}) - {ITEMS[item]['cost']}g")
            
            print("Type number to buy, or 'x' to leave.")
            choice = input("> ")

            if choice == 'x': break
            elif choice == '0':
                if self.player.gold >= 50:
                    self.player.gold -= 50
                    self.player.potions += 1
                    print("✅ Purchased Potion.")
                else: print("❌ Not enough gold.")
            elif choice.isdigit() and 1 <= int(choice) <= len(shop_items):
                item_name = shop_items[int(choice)-1]
                cost = ITEMS[item_name]['cost']
                if self.player.gold >= cost:
                    self.player.gold -= cost
                    self.player.inventory.append(item_name)
                    print(f"✅ Bought {item_name}!")
                else: print("❌ Not enough gold.")

    def main_loop(self):
        while self.running and self.player.state == "alive":
            self.turn_count += 1
            print("\n" + "="*50)
            print(f"TURN {self.turn_count} | Lvl {self.player.level} | HP: {self.player.hp}/{self.player.max_hp}")
            print("="*50)
            
            loc = random.choice(LOCATIONS)
            self.type_text(f"\nLocation: {loc['name']}")
            self.type_text(loc['desc'])

            if self.turn_count % 5 == 0:
                self.boss_event(loc['theme'])
            else:
                roll = random.randint(1, 10)
                if roll <= 4: self.combat_event(loc['theme'])
                elif roll <= 6: self.shop_event()
                else: self.loot_event()

            if self.player.state == "alive":
                print("\n[ACTION MENU]")
                c = self.get_input(['continue', 'inventory', 'save', 'quit'])
                if c == 'inventory': self.inventory_menu()
                elif c == 'save': self.save_game()
                elif c == 'quit': self.running = False

        if self.player.state == "dead":
            self.type_text("\n💀 You have fallen.")

    def boss_event(self, theme):
        boss = BOSSES[theme]
        name, hp, atk, xp_reward = boss["name"], boss["hp"], boss["atk"], boss["xp"]
        self.type_text(f"\n⚠️⚠️ BOSS BATTLE: {name}! ⚠️⚠️")
        
        while hp > 0 and self.player.state == "alive":
            print(f"Boss HP: {hp}")
            action = self.get_input(['attack', 'heal'])
            if action == 'attack':
                dmg = random.randint(self.player.total_attack, self.player.total_attack + 5)
                hp -= dmg
                print(f"⚔️ Hit for {dmg}!")
            elif action == 'heal': self.player.heal()
            
            if hp > 0: self.player.take_damage(random.randint(atk - 5, atk + 5))

        if self.player.state == "alive":
            print(f"\n🏆 SLAIN! Rewards: 200 Gold, {xp_reward} XP.")
            self.player.gold += 200
            self.player.gain_xp(xp_reward)

    def combat_event(self, theme):
        enemy = random.choice(ENEMIES[theme])
        hp = random.randint(30 + (self.player.level*5), 60 + (self.player.level*5)) # Enemies scale slightly with level
        atk = random.randint(8, 15)
        xp_reward = random.randint(20, 50)
        
        self.type_text(f"\n⚔️ Combat: {enemy} (HP: {hp})")
        while hp > 0 and self.player.state == "alive":
            action = self.get_input(['attack', 'heal', 'run'])
            if action == 'attack':
                dmg = random.randint(self.player.total_attack - 2, self.player.total_attack + 2)
                hp -= dmg
                print(f"   Hit for {dmg}!")
            elif action == 'heal': self.player.heal()
            elif action == 'run':
                if random.random() > 0.5: print("🏃 Escaped!"); return
                print("❌ Failed to run!")
            
            if hp > 0: self.player.take_damage(random.randint(atk - 2, atk + 2))

        if self.player.state == "alive":
            gold = random.randint(15, 40)
            self.player.gold += gold
            print(f"🏆 Victory! Found {gold} gold.")
            self.player.gain_xp(xp_reward)

    def loot_event(self):
        self.type_text("\nA chest sits before you.")
        if self.get_input(['open', 'leave']) == 'open':
            if random.random() > 0.4:
                gold = random.randint(20, 80)
                self.player.gold += gold
                print(f"💰 Found {gold} gold!")
            else:
                self.type_text("💥 It's a trap!")
                self.player.take_damage(15)

if __name__ == "__main__":
    game = Game()
    game.main_menu()