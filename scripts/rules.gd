class_name Rules
extends RefCounted
## Static game data: terrain and unit stats. Balance lives here.

enum Terrain { PLAIN, FOREST, HILLS, CITY, WATER }

const TERRAIN := {
	Terrain.PLAIN: {"name": "Рівнина", "cost": 1, "def": 0, "color": Color(0.50, 0.64, 0.35)},
	Terrain.FOREST: {"name": "Ліс", "cost": 2, "def": 20, "color": Color(0.30, 0.47, 0.25)},
	Terrain.HILLS: {"name": "Пагорби", "cost": 2, "def": 30, "color": Color(0.62, 0.56, 0.38)},
	Terrain.CITY: {"name": "Місто", "cost": 1, "def": 35, "color": Color(0.55, 0.57, 0.58)},
	Terrain.WATER: {"name": "Вода", "cost": -1, "def": 0, "color": Color(0.22, 0.42, 0.62)},
}

## hits_air: can attack flying units. fire_after_move: may move and attack in one turn.
## heavy: forest/hills cost +1 movement. flying: ignores terrain, cannot capture cities.
const UNITS := {
	"infantry": {
		"name": "Піхота", "hp": 100, "atk": 30, "def": 25, "move": 3,
		"min_range": 1, "range": 1, "cost": 100, "hits_air": true,
	},
	"tank": {
		"name": "Танк", "hp": 120, "atk": 55, "def": 40, "move": 5,
		"min_range": 1, "range": 1, "cost": 300, "heavy": true,
	},
	"artillery": {
		"name": "САУ", "hp": 70, "atk": 60, "def": 10, "move": 3,
		"min_range": 2, "range": 3, "cost": 250, "fire_after_move": false,
	},
	"air_defense": {
		"name": "ППО", "hp": 70, "atk": 20, "air_atk": 70, "def": 15, "move": 4,
		"min_range": 1, "range": 2, "cost": 200, "hits_air": true,
	},
	"drone": {
		"name": "Дрон", "hp": 50, "atk": 35, "def": 10, "move": 7,
		"min_range": 1, "range": 1, "cost": 180, "flying": true, "hits_air": true,
	},
}

const BUILD_ORDER: Array[String] = ["infantry", "tank", "artillery", "air_defense", "drone"]

const INCOME_CITY := 50
const INCOME_CAPITAL := 100
const HEAL_IN_CITY := 20
const START_MONEY := 300
const COUNTER_FACTOR := 0.6
