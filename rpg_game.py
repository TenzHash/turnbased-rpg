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

# --- CLASSES ---

class Player:
    def __init__(self):
        self.name = ""
        self.state = "alive"
        self.hp = 100
        self.max_hp = 100
        self.mp = 40
        self.max_mp = 40
        self.base_attack = 10
        self.gold = 50
        self.xp = 0
        self.level = 1
        self.xp_to_next_level = 100
        self.potions = 1
        self.mana_potions = 1
        self.inventory = [] 
        self.equipped_weapon = None
        self.equipped_armor = None
        # NEW: Quest Attributes
        self.active_quest = None # Stores dict: {'target': 'Goblin', 'count': 3, 'progress': 0, 'reward': 100}

    @property
    def total_attack(self):
        bonus = ITEMS[self.equipped_weapon]['value'] if self.equipped_weapon else 0
        return self.base_attack + bonus

    @property
    def defense(self):
        return ITEMS[self.equipped_armor]['value'] if self.equipped_armor else 0

    def drink_potion(self):
        if self.potions > 0:
            heal_amount = 30
            self.hp = min(self.max_hp, self.hp + heal_amount)
            self.potions -= 1
            print(f"\n🧪 Glug... HP restored to {self.hp}/{self.max_hp}.")
        else:
            print("\n❌ Out of Health Potions!")

    def drink_mana_potion(self):
        if self.mana_potions > 0:
            mana_amount = 20
            self.mp = min(self.max_mp, self.mp + mana_amount)
            self.mana_potions -= 1
            print(f"\n🧪 Glug... MP restored to {self.mp}/{self.max_mp}.")
        else:
            print("\n❌ Out of Mana Potions!")

    def take_damage(self, dmg):
        actual_dmg = max(1, dmg - self.defense)
        self.hp -= actual_dmg
        if self.hp <= 0:
            self.hp = 0
            self.state = "dead"
        print(f"   🔻 Took {actual_dmg} dmg (Def: {self.defense}). HP: {self.hp}/{self.max_hp}")

    def gain_xp(self, amount):
        self.xp += amount
        print(f"   ✨ Gained {amount} XP! ({self.xp}/{self.xp_to_next_level})")
        while self.xp >= self.xp_to_next_level:
            self.level_up()

    def level_up(self):
        self.xp -= self.xp_to_next_level
        self.level += 1
        self.xp_to_next_level = int(self.xp_to_next_level * 1.5)
        self.max_hp += 20
        self.max_mp += 10
        self.hp = self.max_hp
        self.mp = self.max_mp
        self.base_attack += 3
        print(f"\n🌟 LEVEL UP! You are now Level {self.level}! 🌟")

    # NEW: Quest Progress Check
    def check_quest(self, enemy_name):
        if self.active_quest:
            if self.active_quest['target'] == enemy_name:
                self.active_quest['progress'] += 1
                print(f"   📜 Quest Update: {self.active_quest['target']} slain ({self.active_quest['progress']}/{self.active_quest['count']})")
                
                if self.active_quest['progress'] >= self.active_quest['count']:
                    self.complete_quest()

    def complete_quest(self):
        reward = self.active_quest['reward']
        xp_reward = self.active_quest['xp']
        print(f"\n🎉 QUEST COMPLETE! You slew all {self.active_quest['target']}s!")
        print(f"   💰 Reward: {reward} Gold, {xp_reward} XP")
        self.gold += reward
        self.gain_xp(xp_reward)
        self.active_quest = None

    def to_dict(self):
        return self.__dict__

    def from_dict(self, data):
        for key, value in data.items():
            setattr(self, key, value)
        # Defaults for backward compatibility
        if not hasattr(self, 'mp'): self.mp = 40
        if not hasattr(self, 'max_mp'): self.max_mp = 40
        if not hasattr(self, 'mana_potions'): self.mana_potions = 0
        if not hasattr(self, 'active_quest'): self.active_quest = None

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
            print("Invalid choice.")

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
        print(f"\n📂 Save loaded! Welcome back, {self.player.name}.")
        return True

    def main_menu(self):
        self.type_text("=== RPG v6.0: THE QUEST UPDATE ===")
        print("1. New Game")
        print("2. Load Game")
        c = self.get_input(['1', '2'])
        if c == '2':
            if self.load_game(): self.main_loop()
            else: self.setup_new_game()
        else: self.setup_new_game()

    def setup_new_game(self):
        self.player.name = input("\nEnter name: ")
        print("1. Warrior (HP+)")
        print("2. Rogue (Atk+)")
        print("3. Mage (MP+)")
        c = self.get_input(['1', '2', '3'])
        if c == '1': self.player.max_hp = 130; self.player.hp = 130
        elif c == '2': self.player.base_attack = 14
        elif c == '3': self.player.max_mp = 70; self.player.mp = 70
        self.main_loop()

    # --- EVENTS ---

    def npc_quest_event(self, theme):
        self.type_text("\n🗣️ You encounter a ragged survivor.")
        
        # Generate random quest based on current theme
        target = random.choice(ENEMIES[theme])
        count = random.randint(2, 4)
        gold_reward = count * 30
        xp_reward = count * 20
        
        print(f"Survivor: 'Those {target}s are everywhere... Can you take out {count} of them for me?'")
        print(f"Rewards: {gold_reward} Gold, {xp_reward} XP")
        
        c = self.get_input(['yes', 'no'])
        if c == 'yes':
            self.player.active_quest = {
                'target': target,
                'count': count,
                'progress': 0,
                'reward': gold_reward,
                'xp': xp_reward
            }
            print("Survivor: 'Thank you, hero!'")
            self.type_text("📜 Quest Accepted!")
        else:
            print("Survivor: 'A shame...'")

    def cast_spell(self, target_name):
        print(f"\n🔮 MP: {self.player.mp}/{self.player.max_mp}")
        for k, v in SPELLS.items():
            desc = f"Dmg x{v['dmg_mult']}" if 'dmg_mult' in v else f"Heal {v['heal']}"
            print(f"{k}. {v['name']} ({v['cost']} MP) - {desc}")
        print("x. Cancel")
        c = input("> ")
        if c in SPELLS:
            spell = SPELLS[c]
            if self.player.mp >= spell['cost']:
                self.player.mp -= spell['cost']
                print(f"⚡ Cast {spell['name']}!")
                if c == "3":
                    self.player.hp = min(self.player.max_hp, self.player.hp + spell['heal'])
                    print(f"   ✨ Restored {spell['heal']} HP!")
                    return 0
                else:
                    dmg = int(self.player.total_attack * spell['dmg_mult'])
                    print(f"   🔥 Hit {target_name} for {dmg} damage!")
                    return dmg
            else: print("❌ Not enough Mana!"); return -1
        return -1

    def battle_logic(self, enemy_name, hp, atk, xp_reward, is_boss=False):
        self.type_text(f"\n⚔️ BATTLE: {enemy_name} (HP: {hp})")
        while hp > 0 and self.player.state == "alive":
            print(f"\nHP: {self.player.hp} | MP: {self.player.mp}")
            options = ['attack', 'magic', 'potion', 'run']
            if is_boss: options.remove('run')
            
            action = self.get_input(options)
            player_dmg = 0
            
            if action == 'attack':
                player_dmg = random.randint(self.player.total_attack - 2, self.player.total_attack + 2)
                print(f"⚔️ Swing: {player_dmg} dmg!")
            elif action == 'magic':
                s_dmg = self.cast_spell(enemy_name)
                if s_dmg == -1: continue
                player_dmg = s_dmg
            elif action == 'potion':
                p = self.get_input(['health', 'mana'])
                if p == 'health': self.player.drink_potion()
                else: self.player.drink_mana_potion()
            elif action == 'run':
                if random.random() > 0.5: print("🏃 Escaped!"); return
                print("❌ Run failed!")

            hp -= player_dmg
            if hp > 0:
                enemy_dmg = random.randint(atk - 3, atk + 3)
                self.player.take_damage(max(1, enemy_dmg))

        if self.player.state == "alive":
            gold = random.randint(20, 60)
            if is_boss: gold *= 3
            self.player.gold += gold
            self.player.gain_xp(xp_reward)
            print(f"🏆 Victory! Looted {gold} Gold.")
            
            # CHECK QUEST PROGRESS
            self.player.check_quest(enemy_name)

    def main_loop(self):
        while self.running and self.player.state == "alive":
            self.turn_count += 1
            print("\n" + "="*50)
            q_text = f" | Quest: {self.player.active_quest['target']} ({self.player.active_quest['progress']}/{self.player.active_quest['count']})" if self.player.active_quest else ""
            print(f"TURN {self.turn_count} | Lvl {self.player.level}{q_text}")
            print("="*50)
            
            loc = random.choice(LOCATIONS)
            self.type_text(f"\nLocation: {loc['name']}")
            
            # Event Roll
            roll = random.randint(1, 20)
            
            if self.turn_count % 5 == 0:
                boss = BOSSES[loc['theme']]
                self.type_text(f"⚠️ BOSS: {boss['name']}!")
                self.battle_logic(boss['name'], boss['hp'], boss['atk'], boss['xp'], is_boss=True)
            elif roll <= 2: # 10% chance for Quest NPC
                if not self.player.active_quest:
                    self.npc_quest_event(loc['theme'])
                else:
                    print("You see a survivor, but you are already on a mission.")
            elif roll <= 10: # 40% chance for Combat
                enemy = random.choice(ENEMIES[loc['theme']])
                hp = random.randint(30, 60) + (self.player.level * 5)
                self.battle_logic(enemy, hp, 10 + self.player.level, 30)
            elif roll <= 14: # 20% Chance for Shop
                self.shop_event()
            else: # Rest is Loot
                self.loot_event()

            if self.player.state == "alive":
                c = self.get_input(['continue', 'inventory', 'save', 'quit'])
                if c == 'inventory': self.inventory_menu()
                elif c == 'save': self.save_game()
                elif c == 'quit': self.running = False

        if self.player.state == "dead":
            self.type_text("\n💀 GAME OVER.")

    def inventory_menu(self):
        print(f"\n🎒 INVENTORY")
        print(f"HP: {self.player.hp}/{self.player.max_hp}")
        print(f"MP: {self.player.mp}/{self.player.max_mp}")
        if self.player.active_quest:
            q = self.player.active_quest
            print(f"📜 Quest: Kill {q['target']} ({q['progress']}/{q['count']})")
        else:
            print("📜 Quest: None")
        print("Items:", ", ".join(self.player.inventory) or "None")

    def shop_event(self):
        self.type_text("\n🏪 Merchant")
        while True:
            print(f"\nGold: {self.player.gold}")
            print("1. HP Potion (50g)")
            print("2. MP Potion (60g)")
            print("3. Equipment")
            print("x. Leave")
            c = input("> ")
            if c == '1': 
                if self.player.gold >= 50: self.player.gold-=50; self.player.potions+=1; print("Bought HP Potion.")
            elif c == '2':
                if self.player.gold >= 60: self.player.gold-=60; self.player.mana_potions+=1; print("Bought MP Potion.")
            elif c == '3':
                for item_name, data in ITEMS.items(): print(f"- {item_name} ({data['cost']}g)")
                buy = input("Name > ")
                if buy in ITEMS and self.player.gold >= ITEMS[buy]['cost']:
                    self.player.gold -= ITEMS[buy]['cost']; self.player.inventory.append(buy); print("Bought!")
            elif c == 'x': break

    def loot_event(self):
        self.type_text("\nA chest!")
        if self.get_input(['open', 'leave']) == 'open':
            if random.random() > 0.4:
                g = random.randint(20, 80)
                self.player.gold += g
                print(f"💰 Found {g} gold!")
            else:
                self.player.take_damage(15)

if __name__ == "__main__":
    game = Game()
    game.main_menu()