class_name Rules
extends RefCounted
## Static game data: terrain, units, commanders, operational means. Balance lives here.

enum Terrain { PLAIN, FOREST, HILLS, CITY, WATER, MOUNTAIN }

const TERRAIN := {
	Terrain.PLAIN: {"name": "Рівнина", "cost": 1, "def": 0},
	Terrain.FOREST: {"name": "Ліс", "cost": 2, "def": 20},
	Terrain.HILLS: {"name": "Пагорби", "cost": 2, "def": 30},
	Terrain.CITY: {"name": "Місто", "cost": 1, "def": 35},
	Terrain.WATER: {"name": "Вода", "cost": -1, "def": 0},  # impassable on the ground
	Terrain.MOUNTAIN: {"name": "Гори", "cost": -1, "def": 0},  # impassable on the ground
}

## Target classes (canon §5): what a unit is when it is shot at.
const CLASS_NAMES := {
	"inf": "піхота", "light": "легка техніка", "heavy": "важка броня",
	"heli": "вертоліт", "air": "літак",
}

## atk: damage against each target class (0 = cannot attack that class).
## counter: returns fire when attacked (canon §4.3). heavy: forest/hills cost +1.
## flying: ignores terrain and zones of control. capture: may take cities (infantry only).
## fire_after_move=false: must stand still to fire. move_after_attack: may still move
## after firing (attack helicopter). splash: share of damage dealt to the neighbours
## of the target, friends included (canon §22). repair: heals an adjacent friend.
## airfield: bought only at airfields. dig: entrenches when it stands still a turn.
## branch: which commanders boost the unit.
const UNITS := {
	"infantry": {
		"name": "Піхота", "short": "Піх", "class": "inf", "branch": "infantry",
		"hp": 100, "def": 25, "move": 3, "min_range": 1, "range": 1, "cost": 100,
		"atk": {"inf": 45, "light": 28, "heavy": 10, "heli": 0, "air": 0},
		"counter": true, "capture": true, "dig": true,
	},
	"recon": {
		"name": "Бронемашина", "short": "Розв", "class": "light", "branch": "armor",
		"hp": 70, "def": 18, "move": 6, "min_range": 1, "range": 1, "cost": 150,
		"atk": {"inf": 38, "light": 26, "heavy": 6, "heli": 0, "air": 0},
		"counter": true,
	},
	"ifv": {
		"name": "БМП", "short": "БМП", "class": "light", "branch": "armor",
		"hp": 100, "def": 30, "move": 5, "min_range": 1, "range": 1, "cost": 250,
		"atk": {"inf": 48, "light": 42, "heavy": 20, "heli": 18, "air": 0},
		"counter": true,
	},
	"tank": {
		"name": "Танк", "short": "Танк", "class": "heavy", "branch": "armor",
		"hp": 130, "def": 50, "move": 4, "min_range": 1, "range": 1, "cost": 400, "points": 2,
		"atk": {"inf": 52, "light": 66, "heavy": 60, "heli": 0, "air": 0},
		"counter": true, "heavy": true,
	},
	"artillery": {
		"name": "САУ", "short": "САУ", "class": "light", "branch": "artillery",
		"hp": 70, "def": 10, "move": 3, "min_range": 2, "range": 3, "cost": 350, "points": 2,
		"atk": {"inf": 62, "light": 56, "heavy": 42, "heli": 0, "air": 0},
		"fire_after_move": false,
	},
	"mlrs": {
		"name": "РСЗВ", "short": "РСЗВ", "class": "light", "branch": "artillery",
		"hp": 60, "def": 8, "move": 3, "min_range": 3, "range": 4, "cost": 450, "points": 2,
		"atk": {"inf": 70, "light": 52, "heavy": 26, "heli": 0, "air": 0},
		"fire_after_move": false, "splash": 0.3,
	},
	"sam": {
		"name": "ППО", "short": "ППО", "class": "light", "branch": "support",
		"hp": 70, "def": 15, "move": 4, "min_range": 1, "range": 3, "cost": 300,
		"atk": {"inf": 0, "light": 0, "heavy": 0, "heli": 80, "air": 75},
		"intercept": true,
	},
	"logistics": {
		"name": "Логістика", "short": "Лог", "class": "light", "branch": "support",
		"hp": 60, "def": 10, "move": 5, "min_range": 1, "range": 1, "cost": 150,
		"atk": {"inf": 0, "light": 0, "heavy": 0, "heli": 0, "air": 0},
		"repair": 35,
	},
	"heli": {
		"name": "Ударний вертоліт", "short": "Верт", "class": "heli", "branch": "air",
		"hp": 90, "def": 20, "move": 7, "min_range": 1, "range": 1, "cost": 500, "points": 2,
		"atk": {"inf": 46, "light": 62, "heavy": 70, "heli": 20, "air": 0},
		"flying": true, "move_after_attack": true, "airfield": true,
	},
	"jet": {
		"name": "Штурмовик", "short": "Літ", "class": "air", "branch": "air",
		"hp": 80, "def": 25, "move": 9, "min_range": 1, "range": 1, "cost": 650, "points": 3,
		"atk": {"inf": 50, "light": 62, "heavy": 62, "heli": 45, "air": 40},
		"flying": true, "airfield": true,
	},
}

const BUILD_ORDER: Array[String] = [
	"infantry", "recon", "ifv", "tank", "artillery", "mlrs", "sam", "logistics", "heli", "jet",
]

## Pseudo-3D sprites rendered by tools/render_units.gd (assets/units/<name>.png/.json).
## Unit types without an entry are drawn as NATO symbols.
const SPRITES := {
	"tank": "t72_rambo",
}

const BASE_INCOME := 100  # guaranteed every turn, even with no cities (canon §16.1)
const INCOME_CITY := 50
const INCOME_HQ := 100  # key points
const INCOME_AIRFIELD := 75

## Army limit (canon §16.3): units cost army points (1 unless "points" says more);
## each point over the limit cuts income by OVER_LIMIT_PENALTY, never below BASE_INCOME.
const ARMY_LIMIT_BASE := 12
const ARMY_LIMIT_PER_CITY := 2
const OVER_LIMIT_PENALTY := 0.1
const HEAL_IN_CITY := 20
const COUNTER_FACTOR := 0.6
const ENTRENCH_DEF := 30  # flat defence bonus for an entrenched unit
const CITY_DAMAGE_TO_FLYING := 0  # cities give no cover to aircraft

## Veterancy (canon §38): experience = damage dealt; each star +8% attack and defence.
const XP_STARS: Array[int] = [60, 160, 320]
const STAR_BONUS := 0.08

## Command points for operational means (canon §38).
const CP_START := 1
const CP_PER_TURN := 1
const CP_MAX := 6

const CARDS := {
	"strike": {"name": "Ракетний удар", "cp": 2,
		"text": "40 шкоди в обраному гексі й 15 у сусідніх (свої теж)."},
	"repair": {"name": "Польовий ремонт", "cp": 1,
		"text": "Свій юніт відновлює 40 HP."},
	"reserve": {"name": "Резерв", "cp": 2,
		"text": "Безкоштовна піхота у вільному своєму місті."},
}
const CARD_ORDER: Array[String] = ["strike", "repair", "reserve"]

## Commanders (canon §38): fictional officers. A commander attached to a unit of the
## same branch gives +6% attack and +4% defence per rank; rank 3 unlocks the perk.
const COMMANDERS := {
	"steel": {"name": "Полк. Сталь", "branch": "armor", "unlock": 0,
		"perk": "+1 рух", "perk_id": "move"},
	"sentinel": {"name": "Майор Вартовий", "branch": "infantry", "unlock": 0,
		"perk": "окопування дає вдвічі більше захисту", "perk_id": "dig"},
	"thunder": {"name": "Полк. Грім", "branch": "artillery", "unlock": 30,
		"perk": "+1 дальність", "perk_id": "range"},
	"cobra": {"name": "Майор Кобра", "branch": "armor", "unlock": 40,
		"perk": "контратака на повну силу", "perk_id": "counter"},
	"forest": {"name": "Кпт. Лісовий", "branch": "infantry", "unlock": 40,
		"perk": "+1 рух", "perk_id": "move"},
	"berkut": {"name": "Підп. Беркут", "branch": "air", "unlock": 50,
		"perk": "+2 рух", "perk_id": "move2"},
	"shield": {"name": "Майор Щит", "branch": "support", "unlock": 50,
		"perk": "ППО +1 дальність, логістика +20 ремонту", "perk_id": "support"},
	"anvil": {"name": "Ген. Ковадло", "branch": "any", "unlock": 80,
		"perk": "юніт відновлює 10 HP щоходу", "perk_id": "regen"},
}
const COMMANDER_ORDER: Array[String] = ["steel", "sentinel", "thunder", "cobra", "forest", "berkut", "shield", "anvil"]
const COMMANDER_MAX_RANK := 5
const CMD_ATK_PER_RANK := 0.06
const CMD_DEF_PER_RANK := 0.04
const BRANCH_NAMES := {
	"armor": "бронетехніка", "infantry": "піхота", "artillery": "артилерія",
	"air": "авіація", "support": "підтримка", "any": "будь-які війська",
}

## Medals for the player's commanders, earned during the campaign.
const MEDALS_CITY := 5
const MEDALS_KEY_POINT := 20
const MEDALS_KILL := 2
const COMMANDER_SLOTS := 4


static func rank_up_cost(rank: int) -> int:
	return 20 * rank
