import flet as ft
import random
import time
import json
import os
import hashlib
import threading

# ==========================================
#              CONFIGURATION
# ==========================================

MAP_SIZE = 5

BIOMES = [
    {"name": "Whispering Woods", "theme": "Fantasy", "desc": "Violet leaves fall gently. The wind howls."},
    {"name": "Neon Slums", "theme": "Sci-Fi", "desc": "Holographic ads flicker in the rain."},
    {"name": "Cursed Crypt", "theme": "Horror", "desc": "Fog rolls over tombstones. You hear whispers."},
    {"name": "Sunken Grotto", "theme": "Adventure", "desc": "Rushing water echoes in the dark."}
]

ENEMIES = {
    "Fantasy": ["Goblin", "Wolf", "Bandit"],
    "Sci-Fi": ["Drone", "Cyborg", "Sec-Bot"],
    "Horror": ["Ghost", "Zombie", "Vampire"],
    "Adventure": ["Crab", "Pirate", "Slime"]
}

ROAMING_BOSSES = {"Fantasy": "Elder Dragon", "Sci-Fi": "Mecha-Titan", "Horror": "Lich Lord", "Adventure": "Kraken"}

ITEMS = {
    "Iron Sword": {"type": "w", "value": 5, "cost": 50, "desc": "Standard blade."},
    "Plasma Rifle": {"type": "w", "value": 10,"cost": 150, "desc": "Energy bolts."},
    "Demon Blade": {"type": "w", "value": 20,"cost": 400, "desc": "Cursed aura."},
    "God Slayer": {"type": "w", "value": 50,"cost": 9999,"desc": "Infinite power."},
    "Leather Armor": {"type": "a", "value": 2, "cost": 40, "desc": "Basic protection."},
    "Nano-Suit": {"type": "a", "value": 6, "cost": 120, "desc": "Synthetic plating."},
    "Dragon Plate": {"type": "a", "value": 12,"cost": 450, "desc": "Dragon scales."},
    "Iron Ore": {"type": "m", "value": 0, "cost": 10, "desc": "Raw metal."},
    "Magic Dust": {"type": "m", "value": 0, "cost": 15, "desc": "Sparkling residue."},
    "Scrap Metal": {"type": "m", "value": 0, "cost": 10, "desc": "Rusted parts."},
    "Monster Fang": {"type": "m", "value": 0, "cost": 20, "desc": "Sharp trophy."},
    "Ice Bomb": {"type": "c", "value": 0, "cost": 80, "desc": "Freezes enemy."}
}

RECIPES = {
    "Health Potion": {"Magic Dust": 2, "Monster Fang": 1},
    "Mana Potion": {"Magic Dust": 3},
    "Ice Bomb": {"Magic Dust": 2, "Scrap Metal": 1},
    "Iron Sword": {"Iron Ore": 3, "Scrap Metal": 1},
    "Nano-Suit": {"Scrap Metal": 5, "Iron Ore": 2}
}

PETS = {
    "Wolf": {"cost": 300, "desc": "Atks 5 dmg/turn."},
    "Fairy": {"cost": 400, "desc": "Heals 5 HP/turn."},
    "Golem": {"cost": 500, "desc": "Blocks 20% dmg."}
}

CLASS_SKILLS = {
    "Warrior": {3: "Rage (+Atk)", 6: "Stone Skin (+HP)", 9: "Execute (Kill <30HP)"},
    "Rogue": {3: "Evasion (Dodge)", 6: "Greed (+Gold)", 9: "Assassinate (2x Dmg)"},
    "Mage": {3: "Focus (+MP)", 6: "Efficiency (-Cost)", 9: "Recharge (+Regen)"}
}

SPELLS = {
    "1": {"name": "Fireball", "cost": 12, "dmg_mult": 2.5, "desc": "Burn chance."},
    "2": {"name": "Lightning", "cost": 8, "dmg_mult": 1.5, "desc": "Quick zap."},
    "3": {"name": "Holy Light", "cost": 15, "heal": 60, "desc": "Heal HP."},
    "4": {"name": "Armageddon", "cost": 50, "dmg_mult": 5.0, "desc": "Ultimate."} 
}

BUILDINGS = {"Blacksmith": 300, "Temple": 250, "Magic Tower": 500}

# ==========================================
#           GUI / IO BRIDGE
# ==========================================

class IOManager:
    def __init__(self):
        self.page = None
        self.log_col = None
        self.input_field = None
        self.hud_text = None
        self.input_event = threading.Event()
        self.last_input = ""

    def setup(self, page, log_col, input_field, hud_text):
        self.page = page
        self.log_col = log_col
        self.input_field = input_field
        self.hud_text = hud_text

    def print(self, text, speed=0.0):
        """Thread-safe print to GUI."""
        if not self.page: return
        # Clean color codes just in case
        t = ft.Text(text, font_family="Consolas", size=14, color="white")
        self.log_col.controls.append(t)
        self.page.update()
        if speed > 0: time.sleep(speed)
        # Auto scroll logic could go here

    def input(self, prompt=""):
        """Thread-safe input wait."""
        if not self.page: return ""
        if prompt: self.print(prompt)
        
        self.input_field.disabled = False
        self.input_field.focus()
        self.page.update()
        
        self.input_event.clear()
        self.input_event.wait() # BLOCK HERE until submit
        
        self.input_field.disabled = True
        self.page.update()
        return self.last_input

    def clear(self):
        if self.page:
            self.log_col.controls.clear()
            self.page.update()

    def update_hud(self, player):
        if not self.page: return
        txt = (f"{player.name} ({player.p_class}) | Lvl {player.level} | Gold: {player.gold}\n"
               f"HP: {player.hp}/{player.max_hp} | MP: {player.mp}/{player.max_mp} | XP: {player.xp}/{player.xp_to_next_level}")
        self.hud_text.value = txt
        self.page.update()

io = IOManager()

def gui_print(text, speed=0.0): io.print(text, speed)
def gui_input(prompt="> "): return io.input(prompt)
def gui_clear(): io.clear()
def gui_hud(p): io.update_hud(p)

# ==========================================
#              GAME LOGIC (Adapted)
# ==========================================

class Player:
    def __init__(self):
        self.name = "Hero"; self.p_class = "Warrior"; self.state = "alive"
        self.hp = 100; self.max_hp = 100; self.mp = 40; self.max_mp = 40
        self.base_attack = 10; self.gold = 100; self.xp = 0; self.level = 1; self.xp_to_next_level = 100
        self.potions = 2; self.mana_potions = 2
        self.inventory = []; self.equipped_weapon = None; self.equipped_armor = None
        self.pet = None; self.active_quest = None; self.town_upgrades = []; self.skills = []
        self.x = 2; self.y = 2

    @property
    def total_attack(self):
        b = ITEMS[self.equipped_weapon]['value'] if self.equipped_weapon else 0
        if "Rage (+Atk)" in self.skills: b += 5
        return self.base_attack + b

    @property
    def defense(self): return ITEMS[self.equipped_armor]['value'] if self.equipped_armor else 0

    def drink_potion(self):
        if self.potions > 0:
            self.hp = min(self.max_hp, self.hp + 40); self.potions -= 1
            gui_print(f"🧪 Healed. HP: {self.hp}/{self.max_hp}")
        else: gui_print("❌ No Potions.")

    def drink_mana_potion(self):
        if self.mana_potions > 0:
            self.mp = min(self.max_mp, self.mp + 30); self.mana_potions -= 1
            gui_print(f"🧪 Mana restored. MP: {self.mp}/{self.max_mp}")
        else: gui_print("❌ No Potions.")

    def gain_xp(self, amt):
        self.xp += amt
        while self.xp >= self.xp_to_next_level: self.level_up()

    def level_up(self):
        self.xp -= self.xp_to_next_level; self.level += 1
        self.xp_to_next_level = int(self.xp_to_next_level * 1.5)
        self.max_hp += 20; self.max_mp += 10; self.base_attack += 3
        self.hp = self.max_hp; self.mp = self.max_mp
        
        gui_print(f"\n🌟 LEVEL UP! You are now Level {self.level}!")
        if self.level in CLASS_SKILLS[self.p_class]:
            s = CLASS_SKILLS[self.p_class][self.level]
            self.skills.append(s)
            gui_print(f"🔥 UNLOCKED: {s}")
        gui_hud(self)

    def to_dict(self): return self.__dict__
    def from_dict(self, data):
        for k, v in data.items(): setattr(self, k, v)
        if not hasattr(self, 'skills'): self.skills = []
        if not hasattr(self, 'pet'): self.pet = None

class Game:
    def __init__(self):
        self.player = Player()
        self.running = True; self.turn_count = 0
        self.world_map = []; self.void_gate_open = False
        self.username = None; self.password_hash = None; self.save_filename = None

    def start_app(self):
        # Threaded entry point
        while True:
            gui_clear()
            gui_print("=== RPG v18: APP EDITION ===")
            gui_print("1. Login\n2. Register\n3. Exit")
            c = gui_input()
            if c == '1': 
                if self.login(): self.main_menu()
            elif c == '2': self.register()
            elif c == '3': os._exit(0)

    def get_save_path(self, u): return f"rpg_save_{u}.json"

    def register(self):
        gui_print("\n--- NEW ACCOUNT ---")
        u = gui_input("Username:")
        if os.path.exists(self.get_save_path(u)): gui_print("❌ Exists."); time.sleep(1); return
        p = gui_input("Password:")
        self.username = u; self.password_hash = hashlib.sha256(p.encode()).hexdigest()
        self.save_filename = self.get_save_path(u)
        self.create_character()
        self.save_game(False)
        gui_print("✅ Registered!"); time.sleep(1)
        self.running = True; self.main_loop()

    def login(self):
        u = gui_input("Username:")
        path = self.get_save_path(u)
        if not os.path.exists(path): gui_print("❌ Not found."); time.sleep(1); return False
        p = gui_input("Password:")
        try:
            with open(path, "r") as f:
                d = json.load(f)
                if d["meta"]["password_hash"] == hashlib.sha256(p.encode()).hexdigest():
                    self.username = u; self.password_hash = d["meta"]["password_hash"]
                    self.save_filename = path
                    return True
        except: pass
        gui_print("❌ Wrong Password."); time.sleep(1); return False

    def create_character(self):
        gui_clear()
        self.player = Player(); self.generate_map()
        self.player.name = gui_input("Character Name:")
        gui_print("1. Warrior (HP)\n2. Rogue (Atk)\n3. Mage (MP)")
        while True:
            c = gui_input("Class:")
            if c == '1': self.player.p_class = "Warrior"; self.player.max_hp = 140; self.player.hp = 140; break
            elif c == '2': self.player.p_class = "Rogue"; self.player.base_attack = 14; break
            elif c == '3': self.player.p_class = "Mage"; self.player.max_mp = 80; self.player.mp = 80; break

    def generate_map(self):
        self.world_map = [[random.choice(BIOMES) for _ in range(MAP_SIZE)] for _ in range(MAP_SIZE)]
        self.world_map[2][2] = {"name": "Town Square", "theme": "Town", "desc": "Safe haven."}
        self.world_map[0][0] = {"name": "The Deep Pit", "theme": "Dungeon", "desc": "Darkness."}

    def save_game(self, verbose=True):
        d = {"meta": {"username": self.username, "password_hash": self.password_hash},
             "game_data": {"player": self.player.to_dict(), "turn_count": self.turn_count, "map": self.world_map, "void": self.void_gate_open}}
        with open(self.save_filename, "w") as f: json.dump(d, f)
        if verbose: gui_print("💾 Saved."); time.sleep(0.5)

    def load_game(self):
        with open(self.save_filename, "r") as f:
            gd = json.load(f).get("game_data", {})
            if "player" in gd:
                self.player.from_dict(gd["player"]); self.turn_count = gd["turn_count"]
                self.world_map = gd["map"]; self.void_gate_open = gd.get("void", False)
                return True
        return False

    def main_menu(self):
        while True:
            gui_clear()
            gui_print(f"USER: {self.username}")
            gui_print("1. Continue\n2. New Run\n3. Logout")
            c = gui_input()
            if c == '1': 
                if self.load_game(): self.running = True; self.main_loop()
                else: gui_print("No run found."); time.sleep(1)
            elif c == '2': self.create_character(); self.running = True; self.save_game(False); self.main_loop()
            elif c == '3': break

    def inventory_menu(self):
        while True:
            gui_clear()
            gui_print(f"--- {self.player.name}'s INVENTORY ---")
            gui_hud(self.player)
            
            gear = [i for i in self.player.inventory if ITEMS[i]['type'] not in ['m', 'c']]
            mats = [i for i in self.player.inventory if ITEMS[i]['type'] == 'm']
            
            gui_print("\n[GEAR]")
            for i in gear:
                s = "(E)" if i == self.player.equipped_weapon or i == self.player.equipped_armor else ""
                gui_print(f"- {i} {s}")
            
            gui_print("\n[MATS]")
            for i in set(mats): gui_print(f"- {i} x{self.player.inventory.count(i)}")
            
            gui_print(f"\n[ITEMS] HP: {self.player.potions} | MP: {self.player.mana_potions}")
            if "Ice Bomb" in self.player.inventory: gui_print(f"- Ice Bomb x{self.player.inventory.count('Ice Bomb')}")

            gui_print("\n(1)HP (2)MP (e)quip [name] (x)exit")
            c = gui_input()
            if c == 'x': break
            elif c == '1': self.player.drink_potion(); time.sleep(1)
            elif c == '2': self.player.drink_mana_potion(); time.sleep(1)
            elif c.startswith('e '):
                n = c[2:]
                if n in self.player.inventory and ITEMS[n]['type'] in ['w', 'a']:
                    if ITEMS[n]['type'] == 'w': self.player.equipped_weapon = n
                    else: self.player.equipped_armor = n
                    gui_print("Equipped."); time.sleep(1)

    def main_loop(self):
        while self.running and self.player.state == "alive":
            gui_hud(self.player); self.turn_count += 1
            if self.player.level >= 8 and not self.void_gate_open:
                self.void_gate_open = True; self.world_map[4][4] = {"name":"VOID GATE","theme":"Boss","desc":"End."}
                gui_print("\n⚠️ VOID GATE OPENED AT (4,4)!"); time.sleep(2)

            tile = self.world_map[self.player.y][self.player.x]
            gui_clear()
            self.draw_map_ui()
            gui_print(f"LOC: {tile['name']}\n\"{tile['desc']}\"")
            
            gui_print("\n(N)orth (S)outh (E)ast (W)est (L)ook (I)nv (M)enu")
            c = gui_input().lower().strip()
            
            if c in ['n','s','e','w']: self.move(c)
            elif c == 'l': self.explore(tile)
            elif c == 'i': self.inventory_menu()
            elif c == 'm': 
                if gui_input("1.Save 2.Quit > ") == '1': self.save_game()
                else: self.running = False

    def draw_map_ui(self):
        gui_print("  0 1 2 3 4")
        for y in range(MAP_SIZE):
            r = f"{y} "
            for x in range(MAP_SIZE):
                sym = "."
                if x==self.player.x and y==self.player.y: sym="P"
                elif self.world_map[y][x]['theme']=="Town": sym="T"
                elif self.world_map[y][x]['theme']=="Dungeon": sym="D"
                elif self.world_map[y][x]['theme']=="Boss": sym="!"
                r += sym + " "
            gui_print(r)

    def move(self, d):
        dx, dy = {'n':(0,-1),'s':(0,1),'e':(1,0),'w':(-1,0)}[d]
        nx, ny = self.player.x+dx, self.player.y+dy
        if 0<=nx<MAP_SIZE and 0<=ny<MAP_SIZE:
            self.player.x, self.player.y = nx, ny
            if self.world_map[ny][nx]['theme']!="Town" and random.random()<0.2:
                gui_print("⚠️ AMBUSH!"); time.sleep(1); self.combat(self.world_map[ny][nx]['theme'])
        else: gui_print("Blocked."); time.sleep(1)

    def explore(self, tile):
        t = tile['theme']
        if t == "Town": self.town_menu()
        elif t == "Dungeon": self.dungeon_loop()
        elif t == "Boss": self.final_boss()
        else:
            gui_print("Searching..."); time.sleep(1); r = random.random()
            if r < 0.15: self.npc_quest(t)
            elif r < 0.20: self.combat(t, ROAMING_BOSSES[t])
            elif r < 0.70: self.combat(t)
            else: self.loot()

    def town_menu(self):
        if "Temple" in self.player.town_upgrades: self.player.hp=self.player.max_hp; self.player.mp=self.player.max_mp; gui_print("✨ Temple Healed.")
        while True:
            gui_clear()
            b = ", ".join(self.player.town_upgrades)
            gui_print(f"TOWN (Built: {b})")
            gui_print("1.Shop 2.Build 3.Craft 4.Casino 5.Pet 6.Rest 7.Exit")
            c = gui_input()
            if c=='1': self.shop()
            elif c=='2': self.build()
            elif c=='3': self.craft()
            elif c=='4': self.casino()
            elif c=='5': self.pets()
            elif c=='6': self.save_game(); self.player.hp=min(self.player.max_hp, self.player.hp+10); gui_print("Rested."); time.sleep(1)
            elif c=='7': break

    def shop(self):
        while True:
            gui_clear(); gui_print(f"Gold: {self.player.gold}")
            gui_print("1.HP(50) 2.MP(60) 3.Bomb(80)")
            avail = [k for k,v in ITEMS.items() if v['type'] in ['w','a'] and v['tier'] <= (2 if "Blacksmith" in self.player.town_upgrades else 0)]
            for i in avail: gui_print(f"- {i} ({ITEMS[i]['cost']}g)")
            c = gui_input("Buy (Name/x):")
            if c=='x': break
            elif c=='1' and self.player.gold>=50: self.player.gold-=50; self.player.potions+=1
            elif c=='2' and self.player.gold>=60: self.player.gold-=60; self.player.mana_potions+=1
            elif c=='3' and self.player.gold>=80: self.player.gold-=80; self.player.inventory.append("Ice Bomb")
            elif c in avail and self.player.gold>=ITEMS[c]['cost']:
                self.player.gold-=ITEMS[c]['cost']; self.player.inventory.append(c); gui_print("Bought."); time.sleep(1)

    def build(self):
        gui_clear(); gui_print(f"Gold: {self.player.gold}")
        for k,v in BUILDINGS.items(): gui_print(f"{k}: {v}g")
        c = gui_input("Build (Name/x):")
        if c in BUILDINGS and self.player.gold>=BUILDINGS[c]:
            self.player.gold-=BUILDINGS[c]; self.player.town_upgrades.append(c); gui_print("Built."); time.sleep(1)

    def craft(self):
        gui_clear(); gui_print("RECIPES:")
        for k,v in RECIPES.items(): gui_print(f"{k}: {v}")
        c = gui_input("Craft (Name/x):")
        if c in RECIPES:
            reqs = RECIPES[c]
            if all(self.player.inventory.count(m)>=q for m,q in reqs.items()):
                for m,q in reqs.items(): 
                    for _ in range(q): self.player.inventory.remove(m)
                if "Potion" in c: 
                    if "Health" in c: self.player.potions+=1
                    else: self.player.mana_potions+=1
                else: self.player.inventory.append(c)
                gui_print("Crafted."); time.sleep(1)
            else: gui_print("No mats."); time.sleep(1)

    def casino(self):
        gui_clear()
        c = gui_input("1.Dice(100g->200g) 2.Lotto(500g) 3.Exit")
        if c=='1' and self.player.gold>=100:
            self.player.gold-=100; r=random.randint(1,6); gui_print(f"Rolled {r}")
            if r>=4: gui_print("WIN!"); self.player.gold+=200
            else: gui_print("LOSE.")
            time.sleep(1)
        elif c=='2' and self.player.gold>=500:
            self.player.gold-=500
            if random.random()<0.05: gui_print("JACKPOT! GOD SLAYER!"); self.player.inventory.append("God Slayer")
            else: gui_print("Lost.")
            time.sleep(1)

    def pets(self):
        gui_clear(); gui_print(f"Current: {self.player.pet}")
        for k,v in PETS.items(): gui_print(f"{k} ({v['cost']}g): {v['desc']}")
        c = gui_input("Buy (Name/x):")
        if c in PETS and self.player.gold>=PETS[c]['cost']:
            self.player.gold-=PETS[c]['cost']; self.player.pet=c; gui_print("Adopted."); time.sleep(1)

    def dungeon_loop(self):
        floor = 1
        while self.player.state == "alive":
            gui_clear(); gui_print(f"DUNGEON FLOOR {floor}")
            if gui_input("1.Deeper 2.Leave")=='2': break
            e = random.choice(["Skeleton", "Slime", "Shade"])
            self.combat_logic(e, 40+(floor*10), 10+floor, loot=random.choice(["Iron Ore", "Magic Dust"]))
            if self.player.state=="alive":
                floor+=1
                if floor%5==0: gui_print("Treasure! +100g"); self.player.gold+=100; time.sleep(1)

    def combat(self, theme, boss_override=None):
        if boss_override: self.combat_logic(boss_override, 200, 25, is_boss=True)
        else:
            e = random.choice(ENEMIES[theme])
            self.combat_logic(e, 30+(self.player.level*10), 10+(self.player.level*2))

    def combat_logic(self, name, hp, atk, is_boss=False, loot=None):
        burn=0; frozen=False
        while hp > 0 and self.player.state == "alive":
            gui_clear(); gui_print(f"VS {name} (HP: {hp})")
            gui_print(f"YOU (HP: {self.player.hp} MP: {self.player.mp})")
            if burn>0: gui_print(f"🔥 Enemy Burning ({burn})")
            if frozen: gui_print("❄️ Enemy Frozen")
            
            if burn>0: hp-=5; burn-=1; gui_print("Burn dmg -5.")
            if "Recharge (+Regen)" in self.player.skills: self.player.mp=min(self.player.max_mp, self.player.mp+5)
            
            c = gui_input("1.Atk 2.Mag 3.Item 4.Run")
            dmg = 0
            if c=='1':
                dmg = random.randint(self.player.total_attack-2, self.player.total_attack+2)
                if "Execute (Kill <30HP)" in self.player.skills and hp<30: dmg=hp; gui_print("EXECUTE!")
                elif "Assassinate (2x Dmg)" in self.player.skills and random.random()<0.2: dmg*=2; gui_print("CRIT!")
                gui_print(f"Hit {dmg}"); hp-=dmg
            elif c=='2':
                red = 2 if "Efficiency (-Cost)" in self.player.skills else 0
                gui_print("1.Fire(12) 2.Bolt(8) 3.Heal(15)")
                sc = gui_input()
                if sc in SPELLS:
                    s=SPELLS[sc]; cost=max(1,s['cost']-red)
                    if self.player.mp>=cost:
                        self.player.mp-=cost
                        if sc=='1': dmg=int(self.player.total_attack*2.5); hp-=dmg; gui_print(f"Fireball {dmg}"); 
                        if random.random()<0.5: burn=3; gui_print("Burned!")
                        elif sc=='2': dmg=int(self.player.total_attack*1.5); hp-=dmg; gui_print(f"Bolt {dmg}")
                        elif sc=='3': self.player.hp+=60; gui_print("Healed.")
                    else: gui_print("No MP.")
            elif c=='3':
                if "Ice Bomb" in self.player.inventory:
                    self.player.inventory.remove("Ice Bomb"); frozen=True; gui_print("Used Bomb. Frozen.")
                else: gui_print("No items.")
            elif c=='4':
                if is_boss: gui_print("Can't run.")
                elif random.random()>0.5: return
                else: gui_print("Fail.")
            
            # Pet
            if self.player.pet=="Wolf": gui_print("Wolf bites 5."); hp-=5
            elif self.player.pet=="Fairy": self.player.hp+=5; gui_print("Fairy heals 5.")

            if hp>0:
                time.sleep(1)
                edmg = random.randint(atk-3, atk+3)
                if frozen: edmg //= 2; frozen=False; gui_print("Frozen reduces dmg.")
                if self.player.pet=="Golem": edmg = int(edmg*0.8)
                
                if "Evasion (Dodge)" in self.player.skills and random.random()<0.15: gui_print("Dodged!")
                else: 
                    t = max(1, edmg - self.player.defense)
                    self.player.hp -= t; gui_print(f"Enemy hits {t}")
                    if self.player.hp<=0: self.player.state="dead"
            time.sleep(1)

        if self.player.state=="alive":
            g=30*(4 if is_boss else 1); xp=40
            if "Greed (+Gold)" in self.player.skills: g=int(g*1.2)
            self.player.gold+=g; self.player.gain_xp(xp)
            if loot and random.random()<0.6: self.player.inventory.append(loot); gui_print(f"Loot: {loot}")
            gui_print("Victory!"); time.sleep(1); 
            if self.player.active_quest and self.player.active_quest['target']==name: self.player.active_quest['progress']+=1

    def final_boss(self):
        self.combat_logic("THE WORLD EATER", 500, 30, is_boss=True)
        if self.player.state=="alive": self.player.state="won"

    def npc_quest(self, t):
        if self.player.active_quest: gui_print("Busy."); time.sleep(1); return
        e=random.choice(ENEMIES[t]); c=random.randint(2,4)
        if gui_input(f"Kill {c} {e}s? y/n")=='y': self.player.active_quest={'target':e,'count':c,'progress':0,'reward':c*35,'xp':c*25}

    def loot(self):
        if gui_input("Chest! Open? y/n")=='y': self.player.gold+=random.randint(20,80); gui_print("Gold found."); time.sleep(1)

# ==========================================
#              MAIN APP SETUP
# ==========================================

def main(page: ft.Page):
    page.title = "RPG v18"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 400
    page.window_height = 800
    
    # UI Elements
    hud_text = ft.Text("Initialize...", size=12, color="green")
    log_col = ft.Column(scroll="auto", expand=True, auto_scroll=True)
    
    input_field = ft.TextField(
        hint_text="Type command...", 
        expand=True, 
        on_submit=lambda e: submit_input(),
        disabled=True
    )
    submit_btn = ft.IconButton(icon="send", on_click=lambda e: submit_input())

    def submit_input():
        if not input_field.value: return
        io.last_input = input_field.value
        input_field.value = ""
        io.input_event.set()

    # Layout
    page.add(
        ft.Container(content=hud_text, padding=5, bgcolor="bluegrey900"),
        ft.Container(content=log_col, expand=True, padding=10, border=ft.border.all(1, "white")),
        ft.Row([input_field, submit_btn], alignment="center")
    )

    # Init Bridge
    io.setup(page, log_col, input_field, hud_text)

    # Start Game Thread
    game = Game()
    t = threading.Thread(target=game.start_app, daemon=True)
    t.start()

ft.app(target=main)